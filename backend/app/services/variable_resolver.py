"""5 层作用域变量解析。

作用域顺序：global → project → env → case → runtime。
加密变量用 ``cryptography.fernet.Fernet`` 加解密。

典型用法::

    resolver = VariableResolver(key=b"...")
    stack = [("project", 1), ("env", 2), ("case", 5), ("runtime", {"trace_id": "abc"})]
    token = resolver.resolve("auth_token", stack)
    text = resolver.render_template("Bearer {{ auth_token }}", stack)
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger("service.variable_resolver")

# ── Fernet 加密密钥 ────────────────────────────────────────────────
# 优先从环境变量 FERNET_ENCRYPTION_KEY 读取 32 字节 URL-safe base64 密钥。
# 未设置时自动生成并打印警告（开发环境降级行为）。
_FERNET_KEY_ENV_VAR = "FERNET_ENCRYPTION_KEY"
_FERNET_KEY: bytes | None = None
_env_key = os.environ.get(_FERNET_KEY_ENV_VAR)
if _env_key:
    _FERNET_KEY = _env_key.encode("utf-8")
    logger.info("从环境变量 %s 加载 Fernet 加密密钥", _FERNET_KEY_ENV_VAR)
else:
    try:
        from cryptography.fernet import Fernet
        _FERNET_KEY = Fernet.generate_key()
        logger.warning(
            "环境变量 %s 未设置，已自动生成临时 Fernet 密钥（重启后失效，"
            "生产环境请务必设置）",
            _FERNET_KEY_ENV_VAR,
        )
    except ImportError:
        _FERNET_KEY = None
        logger.warning("cryptography 未安装，Fernet 加密功能不可用")



# ── 异常 ────────────────────────────────────────────────────────────────


class VariableResolverError(Exception):
    """变量解析错误。"""


class CryptoError(VariableResolverError):
    """变量加解密错误。"""


# ── 工具：Fernet 密钥 ───────────────────────────────────────────────────


def generate_key() -> bytes:
    """生成新的 Fernet 密钥（推荐 32 字节 URL-safe base64）。"""
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise CryptoError("未安装 cryptography") from exc
    return Fernet.generate_key()


def encrypt(plain: str, key: bytes) -> str:
    """加密明文 → base64 字符串。"""
    if not isinstance(plain, str):
        plain = str(plain)
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise CryptoError("未安装 cryptography") from exc
    try:
        f = Fernet(key)
        return f.encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise CryptoError(f"加密失败: {exc}") from exc


def decrypt(cipher: str, key: bytes) -> str:
    """解密 base64 字符串 → 明文。"""
    if not isinstance(cipher, str):
        raise CryptoError("cipher 必须是字符串")
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise CryptoError("未安装 cryptography") from exc
    try:
        f = Fernet(key)
        return f.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise CryptoError(f"解密失败: {exc}") from exc


# ── 解析器 ──────────────────────────────────────────────────────────────


# 模板替换的占位符：{{ name }} 形式
_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][\w.\-]*)\s*\}\}")


class VariableResolver:
    """5 层作用域变量解析器。"""

    # 优先级：runtime 最高
    SCOPE_ORDER: tuple[str, ...] = ("global", "project", "env", "case", "runtime")

    def __init__(self, key: bytes | None = None) -> None:
        self.key = key if key is not None else _FERNET_KEY

    # ── 内部合并 ────────────────────────────────────────────────

    def _merge(self, scope_stack: list[tuple[str, Any]]) -> dict[str, Any]:
        """按 ``SCOPE_ORDER`` 合并，后到的覆盖前面的。"""
        merged: dict[str, Any] = {}
        for scope_name, payload in scope_stack:
            if scope_name not in self.SCOPE_ORDER:
                logger.warning("未知 scope: %s", scope_name)
                continue
            data = self._normalize(scope_name, payload)
            merged.update(data)
        return merged

    def _normalize(self, scope_name: str, payload: Any) -> dict[str, Any]:
        """把不同形态的 payload 规范成 dict。

        形态约定：
          - ``"global"`` / ``"project"`` / ``"env"`` / ``"case"``：payload 可为：
              * int (scope_id)  →  调用方需提供 ``self.db`` 加载；这里只做兼容
              * dict            →  直接视作变量字典
          - ``"runtime"``：payload 必须为 dict
        """
        if payload is None:
            return {}
        if isinstance(payload, dict):
            return dict(payload)
        if scope_name == "runtime":
            raise VariableResolverError("runtime scope 必须是 dict")
        # int scope_id → 调用方需预解析为 dict，这里只做空 scope 标记
        if isinstance(payload, int):
            logger.debug(
                "scope=%s 传入 int payload=%s，变量需由调用方预解析",
                scope_name,
                payload,
            )
            return {}
        return {}

    # ── 公共方法 ────────────────────────────────────────────────

    def resolve(self, name: str, scope_stack: list[tuple[str, Any]]) -> Any:
        """从作用域栈中查找变量；找到时按 is_secret 决定是否需要解密。"""
        if not name:
            raise VariableResolverError("name 不能为空")
        merged = self._merge(scope_stack)
        if name not in merged:
            raise VariableResolverError(f"变量 {name!r} 不存在")
        value = merged[name]
        # 加密变量约定为 dict 形式: {"__secret__": true, "value": "<cipher>"}
        if isinstance(value, dict) and value.get("__secret__"):
            if self.key is None:
                raise CryptoError(f"变量 {name!r} 标记为加密但未提供 key")
            cipher = value.get("value", "")
            return decrypt(cipher, self.key)
        return value

    def try_resolve(
        self, name: str, scope_stack: list[tuple[str, Any]], default: Any = None
    ) -> Any:
        """不存在的变量返回 ``default``。"""
        try:
            return self.resolve(name, scope_stack)
        except VariableResolverError:
            return default

    def render_template(
        self, text: str, scope_stack: list[tuple[str, Any]], _depth: int = 0
    ) -> str:
        """把 ``{{ name }}`` 替换为变量值（递归替换，与 variable_renderer 行为一致）。"""
        if not isinstance(text, str) or _depth > 10:
            return text
        merged = self._merge(scope_stack)

        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key not in merged:
                return m.group(0)  # 找不到保留原样
            value = merged[key]
            if isinstance(value, dict) and value.get("__secret__"):
                return "<secret>"  # 模板里不直接展示明文
            return str(value)

        result = _VAR_PATTERN.sub(repl, text)
        # 递归替换直到无 {{}} 或达到最大深度，实现嵌套变量支持
        if _VAR_PATTERN.search(result):
            result = self.render_template(result, scope_stack, _depth + 1)
        return result

    def render_dict(
        self, data: dict[str, Any], scope_stack: list[tuple[str, Any]]
    ) -> dict[str, Any]:
        """递归把 dict 内的字符串值做模板替换。"""
        if not isinstance(data, dict):
            return data
        return {k: self._render_value(v, scope_stack) for k, v in data.items()}

    def _render_value(self, value: Any, scope_stack: list[tuple[str, Any]]) -> Any:
        if isinstance(value, str):
            return self.render_template(value, scope_stack)
        if isinstance(value, dict):
            return {k: self._render_value(v, scope_stack) for k, v in value.items()}
        if isinstance(value, list):
            return [self._render_value(v, scope_stack) for v in value]
        return value

    def list_all(self, scope_stack: list[tuple[str, Any]]) -> dict[str, Any]:
        """返回合并后的所有变量（脱敏 secret）。"""
        merged = self._merge(scope_stack)
        out: dict[str, Any] = {}
        for k, v in merged.items():
            if isinstance(v, dict) and v.get("__secret__"):
                out[k] = "<secret>"
            else:
                out[k] = v
        return out
