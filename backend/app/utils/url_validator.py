"""URL 校验器——SSRF 防护：禁止内网/链路本地/CGNAT 地址，支持域名 DNS 解析校验"""

import socket
from urllib.parse import urlparse
import ipaddress

from app.config import settings


def _check_ip(ip_str: str) -> None:
    """检查单个 IP 地址是否允许访问。"""
    ip = ipaddress.ip_address(ip_str)
    if ip.is_private:
        raise ValueError("private IP addresses are not allowed")
    if ip.is_loopback:
        raise ValueError("loopback addresses are not allowed")
    if ip.is_link_local:
        raise ValueError(
            "link-local addresses (169.254.x.x) are not allowed (may expose metadata)"
        )
    if isinstance(ip, ipaddress.IPv4Address):
        cgnat_val = int(ip)
        if cgnat_val >= 0x64400000 and cgnat_val <= 0x647FFFFF:
            raise ValueError("CGNAT addresses (100.64.x.x) are not allowed")
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            _check_ip(str(ip.ipv4_mapped))  # 递归检查映射的 IPv4 地址
            return
        if ip.is_private or ip.is_loopback:
            raise ValueError("private/loopback IPv6 addresses are not allowed")


def validate_request_url(url: str) -> str:
    """Validate and normalize a request URL. Supports both IP and domain hostnames."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"unsupported scheme: {parsed.scheme}")
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("invalid URL: cannot parse hostname")

    # 仅开发环境允许本地地址
    if settings.ENVIRONMENT == "development" and hostname in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        return url

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # 域名场景：解析 DNS 并检查所有解析结果，防止 DNS rebinding
        try:
            addrinfo = socket.getaddrinfo(hostname, 80, type=socket.SOCK_STREAM)
            resolved_ips = set()
            for _, _, _, _, sockaddr in addrinfo:
                ip_str = sockaddr[0]
                if "%" in ip_str:
                    ip_str = ip_str.split("%")[0]
                resolved_ips.add(ip_str)
            if not resolved_ips:
                raise ValueError(
                    f"DNS resolution returned no addresses for: {hostname}"
                )
            for ip_str in resolved_ips:
                _check_ip(ip_str)
        except socket.gaierror:
            raise ValueError(f"DNS resolution failed for hostname: {hostname}")
        return url

    # 直接 IP 的场景
    _check_ip(str(ip))
    return url
