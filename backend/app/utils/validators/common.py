"""通用验证器 - 常用验证函数"""


def validate_not_empty(value: str, field_name: str = "字段") -> str:
    """验证字符串不为空

    Args:
        value: 待验证的值
        field_name: 字段名称（用于错误消息）

    Returns:
        去除首尾空格后的字符串

    Raises:
        ValueError: 值为空
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name}不能为空")
    return value.strip()


def validate_max_length(value: str, max_length: int, field_name: str = "字段") -> str:
    """验证字符串长度不超过最大值

    Args:
        value: 待验证的值
        max_length: 最大长度
        field_name: 字段名称

    Returns:
        原字符串

    Raises:
        ValueError: 超过最大长度
    """
    if len(value) > max_length:
        raise ValueError(f"{field_name}长度不能超过 {max_length} 个字符（当前 {len(value)}）")
    return value


def validate_min_length(value: str, min_length: int, field_name: str = "字段") -> str:
    """验证字符串长度不小于最小值

    Args:
        value: 待验证的值
        min_length: 最小长度
        field_name: 字段名称

    Returns:
        原字符串

    Raises:
        ValueError: 小于最小长度
    """
    if len(value) < min_length:
        raise ValueError(f"{field_name}长度不能少于 {min_length} 个字符（当前 {len(value)}）")
    return value


def validate_pattern(value: str, pattern: str, field_name: str = "字段", message: str = None) -> str:
    """验证字符串匹配正则表达式

    Args:
        value: 待验证的值
        pattern: 正则表达式
        field_name: 字段名称
        message: 自定义错误消息

    Returns:
        原字符串

    Raises:
        ValueError: 不匹配正则表达式
    """
    import re
    if not re.match(pattern, value):
        raise ValueError(message or f"{field_name}格式不合法")
    return value
