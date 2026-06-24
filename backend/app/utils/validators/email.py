"""邮箱验证器 - RFC 5322标准"""

import re


def validate_email(email: str) -> str:
    """验证邮箱格式

    Args:
        email: 待验证的邮箱

    Returns:
        规范化后的邮箱（小写，去除空格）

    Raises:
        ValueError: 邮箱格式不合法
    """
    if not email or not email.strip():
        raise ValueError("邮箱不能为空")

    email = email.strip().lower()

    # RFC 5322 简化版正则
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError(f"邮箱格式不合法: {email}")

    # 检查常见拼写错误
    typos = ["@gmial.com", "@gamil.com", "@yahooo.com", "@hotmial.com"]
    domain = email.split("@")[1] if "@" in email else ""
    if domain in [t.split("@")[1] for t in typos]:
        raise ValueError(f"邮箱域名疑似拼写错误: {domain}")

    return email
