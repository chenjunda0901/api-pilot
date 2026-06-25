"""脚本执行引擎（支持 QuickJS / Js2Py 双后端优雅降级）。

提供 Postman 兼容的 pm API：
  pm.variables.get/set    读写变量
  pm.request              修改请求参数（前置操作）
  pm.response             读取响应数据（后置操作）
  pm.environment          pm.variables 的别名

安全设计：使用全局锁序列化所有执行，任何时刻只运行一个脚本。

超时处理：用户脚本在子进程中执行（由主进程通过进程存活状态判断超时）。
"""

import asyncio
import json
import logging
import multiprocessing
import platform
import threading

logger = logging.getLogger("script_executor")

# 全局执行锁 — JS Context 非线程安全，同一时刻只允许一个脚本执行
_eval_lock = threading.Lock()

# JS 引擎后端：优先使用 quickjs，失败则回退到 js2py
_JS_ENGINE = None
_JS_ENGINE_NAME = None


def _get_js_engine():
    """获取可用的 JS 引擎（懒加载，自动降级）。"""
    global _JS_ENGINE, _JS_ENGINE_NAME
    if _JS_ENGINE is not None:
        return _JS_ENGINE, _JS_ENGINE_NAME

    # 尝试 QuickJS
    try:
        import quickjs

        _JS_ENGINE = quickjs
        _JS_ENGINE_NAME = "quickjs"
        logger.info("使用 QuickJS 作为脚本执行引擎")
        return _JS_ENGINE, _JS_ENGINE_NAME
    except ImportError:
        logger.warning("QuickJS 不可用，尝试使用 Js2Py 作为备选引擎...")

    # 回退到 Js2Py（纯 Python，跨平台）
    try:
        import js2py

        _JS_ENGINE = js2py
        _JS_ENGINE_NAME = "js2py"
        logger.info("使用 Js2Py 作为脚本执行引擎（纯 Python 实现，跨平台兼容）")
        return _JS_ENGINE, _JS_ENGINE_NAME
    except ImportError:
        pass

    # 都不可用
    raise RuntimeError(
        "没有可用的 JavaScript 执行引擎。请安装 quickjs（推荐）或 js2py：\n"
        "  pip install quickjs\n"
        "  # 或（Windows 下编译失败时）\n"
        "  pip install js2py"
    )


class UnifiedJSContext:
    """统一的 JS 上下文包装器，适配 QuickJS 和 Js2Py 的 API 差异。"""

    def __init__(self):
        engine, engine_name = _get_js_engine()
        self.engine_name = engine_name
        if engine_name == "quickjs":
            self.ctx = engine.Context()
            self._add_callable_quickjs()
        else:  # js2py
            self.ctx = engine.EvalJs()
            self._callables = {}

    def _add_callable_quickjs(self):
        """QuickJS 模式下的 add_callable 代理。"""
        self._add_callable_impl = self.ctx.add_callable

    def add_callable(self, name: str, func):
        """向 JS 上下文添加可调用函数。"""
        if self.engine_name == "quickjs":
            self.ctx.add_callable(name, func)
        else:  # js2py
            self._callables[name] = func
            setattr(self.ctx, name, func)

    def eval(self, code: str):
        """执行 JS 代码并返回结果。"""
        if self.engine_name == "quickjs":
            return self.ctx.eval(code)
        else:  # js2py
            return self.ctx.eval(code)


def _set_limits():
    """子进程资源限制：CPU 时间、内存、文件大小。"""
    if platform.system() == "Windows":
        logger.warning(
            "Windows: process resource limits unavailable, JS scripts run without CPU/memory restrictions"
        )
        return
    try:
        import resource

        # CPU 时间 10 秒
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        # 内存 128MB
        resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
        # 文件大小 1MB
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    except (ImportError, ValueError, OSError):
        logger.warning("Failed to set process resource limits: %s")


def _js_escape(s: str) -> str:
    """将 Python 字符串安全嵌入 JS 单引号字符串。

    使用 json.dumps 输出 JS 兼容字符串，天然转义所有特殊字符。
    然后再转义单引号，防止嵌入单引号 JS 字符串时注入。
    """
    return json.dumps(s, ensure_ascii=False)[1:-1].replace(
        "'", "\\'"
    )  # 去掉外层双引号 + 转义单引号


def _build_pm_js() -> str:
    """构建 pm API 的 JavaScript 代码。"""
    return """
(function() {
  const _request = {};
  let _requestDirty = false;
  const _response = {};

  this.pm = {
    variables: {
      get: function(key) { return js_get_var(key); },
      set: function(key, value) { js_set_var(key, value); },
      unset: function(key) { js_set_var(key, ''); },
    },
    environment: {
      get: function(key) { return js_get_var(key); },
      set: function(key, value) { js_set_var(key, value); },
      unset: function(key) { js_set_var(key, ''); },
    },
    request: _request,
    response: _response,
    console: {
      log: function() { js_console_log('log', Array.prototype.slice.call(arguments).join(' ')); },
      warn: function() { js_console_log('warn', Array.prototype.slice.call(arguments).join(' ')); },
      error: function() { js_console_log('error', Array.prototype.slice.call(arguments).join(' ')); },
    },
  };

  this._markRequestDirty = function() { _requestDirty = true; };
  this._isRequestDirty = function() { return _requestDirty; };
}).call(this);
"""


def _create_request_obj(
    method: str, path: str, headers: list, params: list, body: dict, auth: dict
) -> str:
    """创建 JavaScript 中的 pm.request 对象（带脏检测）。"""
    h_json = _js_escape(json.dumps(headers))
    p_json = _js_escape(json.dumps(params))
    b_json = _js_escape(json.dumps(body))
    a_json = _js_escape(json.dumps(auth))
    safe_method = _js_escape(method)
    safe_path = _js_escape(path)
    return f"""
(function() {{
  var self = this;
  var req = this.pm.request;
  var _body = JSON.parse('{b_json}');
  var _headers = JSON.parse('{h_json}');
  var _params = JSON.parse('{p_json}');
  var _auth = JSON.parse('{a_json}');

  Object.defineProperty(req, 'method', {{ get: function() {{ return req._method || '{safe_method}'; }}, set: function(v) {{ req._method = v; self._markRequestDirty(); }}, configurable: true, enumerable: true }});
  Object.defineProperty(req, 'url', {{ get: function() {{ return req._url || '{safe_path}'; }}, set: function(v) {{ req._url = v; self._markRequestDirty(); }}, configurable: true, enumerable: true }});
  Object.defineProperty(req, 'headers', {{ get: function() {{ return req._headers || _headers; }}, set: function(v) {{ req._headers = v; self._markRequestDirty(); }}, configurable: true, enumerable: true }});
  Object.defineProperty(req, 'params', {{ get: function() {{ return req._params || _params; }}, set: function(v) {{ req._params = v; self._markRequestDirty(); }}, configurable: true, enumerable: true }});
  Object.defineProperty(req, 'body', {{ get: function() {{ return req._body || _body; }}, set: function(v) {{ req._body = v; self._markRequestDirty(); }}, configurable: true, enumerable: true }});
  Object.defineProperty(req, 'auth', {{ get: function() {{ return req._auth || _auth; }}, set: function(v) {{ req._auth = v; self._markRequestDirty(); }}, configurable: true, enumerable: true }});

  this._originalSnapshot = null;
  this._saveOriginalSnapshot = function() {{ this._originalSnapshot = JSON.parse(JSON.stringify(req)); }};
  this._isDirtyDeep = function() {{
    return JSON.stringify(this._originalSnapshot) !== JSON.stringify(req);
  }};
}}).call(this);
"""


def _create_response_obj(response: dict) -> str:
    """创建 JavaScript 中的 pm.response 对象。"""
    status = response.get("response_status", 0)
    body_text = response.get("response_body", "")
    body_text_escaped = (
        body_text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    headers_json = json.dumps(response.get("response_headers", {}))
    return f"""
(function() {{
  var resp = this.pm.response;
  var _bodyText = '{body_text_escaped}';
  var _headers = JSON.parse('{headers_json}');
  var _jsonCache = null;

  Object.defineProperty(resp, 'status', {{ get: function() {{ return {status}; }}, enumerable: true }});
  Object.defineProperty(resp, 'text', {{ get: function() {{ return _bodyText; }}, enumerable: true }});
  Object.defineProperty(resp, 'headers', {{ get: function() {{ return _headers; }}, enumerable: true }});
  resp.json = function() {{
    if (_jsonCache === null) {{
      try {{ _jsonCache = JSON.parse(_bodyText); }} catch(e) {{ _jsonCache = {{}}; }}
    }}
    return _jsonCache;
  }};
}}).call(this);
"""


def _pre_script_in_subprocess(
    args: dict, result_queue: multiprocessing.Queue, timeout_ms: int
):
    """在子进程中执行前置脚本（无超时保护，超时由主进程 kill 判断）。"""
    try:
        variables = args["variables"]
        modified_vars = {}
        console_logs: list[str] = []
        console_errors: list[str] = []

        def js_get(key):
            return (
                modified_vars.get(key)
                if key in modified_vars
                else variables.get(key, "")
            )

        def js_set(key, value):
            modified_vars[key] = value

        def js_console_log(level: str, msg: str):
            if level == "error":
                console_errors.append(msg)
            else:
                console_logs.append(msg)

        ctx = UnifiedJSContext()
        ctx.add_callable("js_get_var", js_get)
        ctx.add_callable("js_set_var", js_set)
        ctx.add_callable("js_console_log", js_console_log)
        ctx.eval(_build_pm_js())
        ctx.eval(
            _create_request_obj(
                args["method"],
                args["path"],
                args["headers"],
                args["params"],
                args["body"],
                args["auth"],
            )
        )
        ctx.eval("this._saveOriginalSnapshot()")

        try:
            ctx.eval(args["script"])
        except Exception as e:  # noqa: BLE001 — 用户JS脚本可能抛出任意异常
            result_queue.put(
                {
                    "success": False,
                    "error": f"{type(e).__name__}: {e}",
                    "script_output": "\n".join(console_logs) if console_logs else None,
                    "script_error": "\n".join(
                        console_errors + [f"{type(e).__name__}: {e}"]
                    )
                    if console_errors or True
                    else None,
                }
            )
            return

        is_dirty = ctx.eval("this._isDirtyDeep()")
        modified_request = None
        if is_dirty:
            req_cache_raw = ctx.eval("JSON.stringify(this.pm.request)")
            req_cache = json.loads(req_cache_raw)
            # 脱敏敏感 header，防止 token/cookie 泄漏到报告
            safe_headers = [
                {**h, "value": "***"}
                if h.get("key", "").lower() in ("authorization", "cookie", "set-cookie")
                else h
                for h in (req_cache.get("_headers") or args["headers"])
            ]
            modified_request = {
                "method": req_cache.get("_method")
                or req_cache.get("method")
                or args["method"],
                "path": req_cache.get("_url") or args["path"],
                "headers": safe_headers,
                "params": req_cache.get("_params") or args["params"],
                "body": req_cache.get("_body") or args["body"],
                "auth": req_cache.get("_auth") or args["auth"],
            }

        result_queue.put(
            {
                "success": True,
                "is_dirty": is_dirty,
                "modified_vars": dict(modified_vars),
                "modified_request": modified_request,
                "script_output": "\n".join(console_logs) if console_logs else None,
                "script_error": "\n".join(console_errors) if console_errors else None,
            }
        )
    except Exception as e:  # noqa: BLE001 — JS上下文可能抛出任意异常
        result_queue.put(
            {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
            }
        )


def _post_script_in_subprocess(
    args: dict, result_queue: multiprocessing.Queue, timeout_ms: int
):
    """在子进程中执行后置脚本。"""
    try:
        variables = args["variables"]
        extracted = {}
        console_logs: list[str] = []
        console_errors: list[str] = []

        def js_get(key):
            return extracted.get(key) or variables.get(key, "")

        def js_set(key, value):
            extracted[key] = value

        def js_console_log(level: str, msg: str):
            if level == "error":
                console_errors.append(msg)
            else:
                console_logs.append(msg)

        ctx = UnifiedJSContext()
        ctx.add_callable("js_get_var", js_get)
        ctx.add_callable("js_set_var", js_set)
        ctx.add_callable("js_console_log", js_console_log)
        ctx.eval(_build_pm_js())
        ctx.eval(_create_response_obj(args["response"]))

        try:
            ctx.eval(args["script"])
        except Exception as e:  # noqa: BLE001 — 用户JS脚本可能抛出任意异常
            result_queue.put(
                {
                    "success": False,
                    "error": f"{type(e).__name__}: {e}",
                    "script_output": "\n".join(console_logs) if console_logs else None,
                    "script_error": "\n".join(
                        console_errors + [f"{type(e).__name__}: {e}"]
                    )
                    if console_errors or True
                    else None,
                }
            )
            return

        result_queue.put(
            {
                "success": True,
                "extracted": dict(extracted),
                "script_output": "\n".join(console_logs) if console_logs else None,
                "script_error": "\n".join(console_errors) if console_errors else None,
            }
        )
    except Exception as e:  # noqa: BLE001 — JS上下文可能抛出任意异常
        result_queue.put(
            {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
            }
        )


def _run_with_limits(func, args, result_queue, timeout_ms):
    """子进程入口：先设置资源限制，再执行目标函数。"""
    _set_limits()
    func(args, result_queue, timeout_ms)


def _run_with_timeout(func, args, timeout_sec: float):
    """在子进程中运行函数，超时则 kill 子进程并抛出 TimeoutError。"""
    result_queue = multiprocessing.Queue()

    try:
        p = multiprocessing.Process(
            target=_run_with_limits,
            args=(func, args, result_queue, 0),  # timeout_ms=0，不用 ctx.set_time_limit
            daemon=True,
        )
        p.start()

        import time

        deadline = time.monotonic() + timeout_sec + 1.0
        while True:
            if not result_queue.empty():
                result = result_queue.get_nowait()
                p.join(timeout=0.5)
                return result
            if time.monotonic() >= deadline:
                p.kill()
                p.join(timeout=2.0)
                raise TimeoutError(f"JS 脚本执行超时 ({timeout_sec}秒)")
            time.sleep(0.01)
    finally:
        # 清理队列资源，使用 cancel_join_thread 避免后台 feeder 线程阻塞导致 hang
        # 正常流程已完成时队列数据已无意义，cancel 比 join 更安全
        try:
            result_queue.close()
            result_queue.cancel_join_thread()
        except (OSError, ValueError):
            pass


async def execute_pre_script(
    script: str,
    method: str,
    path: str,
    headers: list,
    params: list,
    body: dict,
    auth: dict,
    variables: dict,
    timeout_sec: float = 10.0,
) -> dict | None:
    """执行前置操作脚本，返回修改后的请求参数（script 修改了才返回）。

    返回字典可能包含以下字段：
    - modified_request: 修改后的请求参数（仅脚本修改了请求时）
    - script_output: console.log/warn 输出
    - script_error: console.error 输出及脚本异常信息
    """
    if not script or not script.strip():
        return None

    args = {
        "script": script,
        "method": method,
        "path": path,
        "headers": headers,
        "params": params,
        "body": body,
        "auth": auth,
        "variables": variables,
    }

    try:
        result = await asyncio.to_thread(
            _run_with_timeout, _pre_script_in_subprocess, args, timeout_sec
        )
        if not result["success"]:
            err_str = result["error"]
            if "TimeoutError" in err_str or "timed out" in err_str.lower():
                raise TimeoutError(f"JS 脚本执行超时 ({timeout_sec}秒)")
            logger.warning("pre-script 执行失败: %s", err_str)
            return {
                "script_output": result.get("script_output"),
                "script_error": result.get("script_error") or err_str,
            }

        modified_vars = result.get("modified_vars", {})
        if modified_vars:
            variables.update(modified_vars)

        pre_result: dict = {}
        if result.get("is_dirty"):
            modified_request = result.get("modified_request")
            if modified_request:
                pre_result["modified_request"] = modified_request

        # 附加脚本输出
        if result.get("script_output"):
            pre_result["script_output"] = result["script_output"]
        if result.get("script_error"):
            pre_result["script_error"] = result["script_error"]

        return pre_result if pre_result else None

    except TimeoutError:
        raise
    except Exception as e:  # noqa: BLE001 — 脚本执行封装器需捕获所有异常
        if isinstance(e, TimeoutError):
            raise
        logger.warning("pre-script 执行失败: %s", e)
        return None


async def execute_post_script(
    script: str, response: dict, variables: dict, timeout_sec: float = 10.0
) -> dict:
    """执行后置操作脚本，返回脚本设置的变量及脚本输出。

    返回字典可能包含以下字段：
    - extracted: 脚本提取的变量
    - script_output: console.log/warn 输出
    - script_error: console.error 输出及脚本异常信息
    """
    if not script or not script.strip():
        return {}

    args = {
        "script": script,
        "response": response,
        "variables": variables,
    }

    try:
        result = await asyncio.to_thread(
            _run_with_timeout, _post_script_in_subprocess, args, timeout_sec
        )
        if not result["success"]:
            err_str = result["error"]
            if "TimeoutError" in err_str or "timed out" in err_str.lower():
                raise TimeoutError(f"JS 脚本执行超时 ({timeout_sec}秒)")
            logger.warning("post-script 执行失败: %s", err_str)
            # 即使失败也返回脚本输出
            post_result: dict = {}
            if result.get("script_output"):
                post_result["script_output"] = result["script_output"]
            post_result["script_error"] = result.get("script_error") or err_str
            return post_result

        extracted = result.get("extracted", {})
        if extracted:
            variables.update(extracted)

        post_result = dict(extracted)
        if result.get("script_output"):
            post_result["script_output"] = result["script_output"]
        if result.get("script_error"):
            post_result["script_error"] = result["script_error"]
        return post_result

    except TimeoutError:
        return {}
    except Exception as e:  # noqa: BLE001 — 脚本执行封装器需捕获所有异常
        logger.warning("post-script 执行失败: %s", e)
        return {}
