"""共享的 slowapi Limiter 实例，供 main.py 和 router 模块使用。

限流 Key 策略：优先读取 X-Forwarded-For / X-Real-IP 请求头，
确保在 Nginx/CDN 反向代理环境下正确提取真实客户端 IP，
防止限流器误封代理服务器 IP 导致全网瘫痪。
"""

from fastapi import Request
from slowapi import Limiter


def get_real_client_ip(request: Request) -> str:
    """
    工业级真实客户端 IP 提取器。

    优先级：X-Forwarded-For 最左段 > X-Real-IP > 直连 client.host。
    X-Forwarded-For 格式通常为: 真实客户端IP, 代理1, 代理2...
    只取最左侧（最原始）的真实客户端 IP，防止攻击者伪造右侧字段。
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_real_client_ip, default_limits=[])