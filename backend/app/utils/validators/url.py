"""URL验证器 - 统一URL格式和安全验证"""

import socket
from urllib.parse import urlparse


def validate_url(url: str, require_scheme: bool = True) -> str:
    """验证URL格式，返回规范化后的URL

    Args:
        url: 待验证的URL
        require_scheme: 是否要求包含协议头（http:// 或 https://）

    Returns:
        规范化后的URL

    Raises:
        ValueError: URL格式不合法
    """
    if not url or not url.strip():
        raise ValueError("URL不能为空")

    url = url.strip()

    if require_scheme:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL必须以 http:// 或 https:// 开头: {url}")
    else:
        # 如果没有协议头，添加默认的 http://
        if not url.startswith(("http://", "https://", "/")):
            url = "http://" + url

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"URL格式不合法（缺少域名）: {url}")

        # 检查是否为本地地址（安全风险）
        hostname = parsed.hostname
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            # 允许localhost，但记录警告
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"URL指向本地地址: {url}")

        return url
    except Exception as e:
        raise ValueError(f"URL解析失败: {url} ({e})")


def _check_ip(ip_str: str) -> None:
    """检查单个 IP 地址是否允许访问（SSRF 防护）。"""
    import ipaddress

    ip = ipaddress.ip_address(ip_str)
    if ip.is_private:
        raise ValueError(f"禁止访问内网地址: {ip_str}")
    if ip.is_loopback:
        raise ValueError(f"禁止访问回环地址: {ip_str}")
    if ip.is_link_local:
        raise ValueError(f"禁止访问链路本地地址: {ip_str}")
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            _check_ip(str(ip.ipv4_mapped))  # 递归检查映射的 IPv4 地址
            return
        if ip.is_private or ip.is_loopback:
            raise ValueError(f"禁止访问内网/回环 IPv6 地址: {ip_str}")


def validate_request_url(url: str) -> str:
    """验证API请求URL（严格模式）

    用于执行引擎的URL验证，比validate_url更严格：
    - 必须包含协议头
    - 不允许本地地址（防止SSRF）
    - 不允许内网地址（防止SSRF）
    - 域名需 DNS 解析校验（防止 DNS rebinding）

    Args:
        url: 待验证的URL

    Returns:
        规范化后的URL

    Raises:
        ValueError: URL格式不合法或存在安全风险
    """
    if not url or not url.strip():
        raise ValueError("请求URL不能为空")

    url = url.strip()

    # 必须包含协议头
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"请求URL必须以 http:// 或 https:// 开头: {url}")

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"请求URL格式不合法: {url}")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError(f"请求URL缺少有效域名: {url}")

        # 禁止本地地址（防止SSRF攻击）
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            raise ValueError(f"禁止访问本地地址: {url}")

        # 检查是否为内网地址
        import ipaddress

        try:
            ip = ipaddress.ip_address(hostname)
            _check_ip(str(ip))
        except ValueError:
            # hostname 不是 IP 地址，进行 DNS 解析校验防止 DNS rebinding
            try:
                addrinfo = socket.getaddrinfo(hostname, 80, type=socket.SOCK_STREAM)
                resolved_ips = set()
                for _, _, _, _, sockaddr in addrinfo:
                    ip_str = sockaddr[0]
                    if "%" in ip_str:
                        ip_str = ip_str.split("%")[0]
                    resolved_ips.add(ip_str)
                if not resolved_ips:
                    raise ValueError(f"DNS 解析未返回任何地址: {hostname}")
                for ip_str in resolved_ips:
                    _check_ip(ip_str)
            except socket.gaierror:
                pass  # DNS 解析失败，让请求自然失败

        return url
    except ValueError:
        raise  # 重新抛出我们的验证错误
    except Exception as e:
        raise ValueError(f"请求URL解析失败: {url} ({e})")
