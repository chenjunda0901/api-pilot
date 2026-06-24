"""密码哈希与验证工具 — 基于 bcrypt。

优化点：
- 使用 bcrypt 直接调用，兼容 bcrypt 4.x 和 5.x
- 密码强度校验统一封装（至少 6 位任意字符）
- 密码自动截断至 72 字节（bcrypt 限制）
"""

import re
import bcrypt

# 密码强度：至少 6 位任意字符
_PASSWORD_PATTERN = re.compile(r"^.{6,}$")


def hash_password(password: str) -> str:
    """对密码进行哈希处理。bcrypt 要求密码 ≤ 72 字节。"""
    pw_bytes = password.encode('utf-8')
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配哈希值。"""
    pw_bytes = plain_password.encode('utf-8')
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode('utf-8'))
    except ValueError:
        return False


def needs_rehash(hashed_password: str) -> bool:
    """检查 bcrypt 哈希是否使用较旧的 rounds 值（<12），需要升级。"""
    try:
        # bcrypt 哈希格式: $2b$rounds$...
        parts = hashed_password.split('$')
        if len(parts) >= 3:
            current_rounds = int(parts[2])
            return current_rounds < 12
    except (ValueError, IndexError):
        pass
    return False


def validate_password_strength(password: str) -> bool:
    """校验密码强度：至少 6 位任意字符。"""
    return bool(_PASSWORD_PATTERN.match(password))
