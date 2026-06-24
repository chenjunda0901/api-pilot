from fastapi.responses import JSONResponse


def success(data=None, message="操作成功", cookies: list[dict] | None = None, headers: dict | None = None, delete_cookies: list[str] | None = None):
    """统一成功响应。

    Args:
        data: 响应数据
        message: 提示消息
        cookies: 可选，要设置的 cookie 列表，每项为 set_cookie() 的 kwargs
        headers: 可选，额外的响应头
        delete_cookies: 可选，要删除的 cookie 名称列表
    """
    resp = JSONResponse(content={"code": 200, "message": message, "data": data})
    if cookies:
        for cookie in cookies:
            resp.set_cookie(**cookie)
    if delete_cookies:
        for name in delete_cookies:
            resp.delete_cookie(key=name, path="/")
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp


def fail(code: int = 400, message: str = "操作失败", data=None, cookies: list[dict] | None = None):
    resp = JSONResponse(status_code=code, content={"code": code, "message": message, "data": data})
    if cookies:
        for cookie in cookies:
            resp.set_cookie(**cookie)
    return resp
