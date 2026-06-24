"""手机号验证器 - 支持中国大陆和国际格式"""

import re


def validate_phone(phone: str, country_code: str = "CN") -> str:
    """验证手机号格式

    Args:
        phone: 待验证的手机号
        country_code: 国家代码（默认CN-中国）

    Returns:
        规范化后的手机号（只保留数字）

    Raises:
        ValueError: 手机号格式不合法
    """
    if not phone or not phone.strip():
        raise ValueError("手机号不能为空")

    # 只保留数字、+、-、空格
    phone = "".join(c for c in phone if c.isdigit() or c in "+- ")

    if country_code == "CN":
        # 中国大陆手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            raise ValueError(f"手机号格式不合法: {phone}")
    else:
        # 国际格式：+国家代码-手机号
        if not re.match(r'^\+\d{1,3}-\d{6,14}$', phone):
            raise ValueError(f"手机号格式不合法: {phone}")

    return phone
