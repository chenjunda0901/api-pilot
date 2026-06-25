"""共享的 slowapi Limiter 实例，供 main.py 和 router 模块使用。

限流 Key 策略：当配置了 TRUSTED_PROXIES 时，仅对来自受信代理的请求
信任 X-Forwarded-For / X-Real-IP 头，防止未受信来源伪造 IP 绕过限流。
"""

from fastapi import Request
from slowapi import Limiter

from app.config import settings


def get_real_client_ip(request: Request) -> str:
    """Extract real client IP, respecting trusted proxy configuration."""
    # If no trusted proxies configured, always use direct connection IP
    if not settings.TRUSTED_PROXIES:
        if request.client:
            return request.client.host
        return '127.0.0.1'

    # Check if request comes from a trusted proxy
    client_ip = request.client.host if request.client else ''
    trusted = [p.strip() for p in settings.TRUSTED_PROXIES.split(',') if p.strip()]
    is_trusted = any(client_ip == p or _ip_in_cidr(client_ip, p) for p in trusted)

    if not is_trusted:
        # Not from trusted proxy, use direct IP
        return client_ip or '127.0.0.1'

    # From trusted proxy, use X-Forwarded-For (first hop = real client)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    return client_ip or '127.0.0.1'


def _ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP is within a CIDR range."""
    try:
        import ipaddress
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except (ValueError, TypeError):
        return False


limiter = Limiter(key_func=get_real_client_ip, default_limits=[])