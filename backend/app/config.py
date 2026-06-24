import logging
import os
import secrets
import socket
import stat
import sys
from pathlib import Path

logger = logging.getLogger("api_pilot.config")

BASE_DIR = Path(__file__).resolve().parent.parent


def _find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """查找可用端口，从 start_port 开始尝试，最多尝试 max_attempts 个端口。"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                result = s.connect_ex((host, port))
                if result != 0:
                    if port != start_port:
                        logger.warning(
                            f"端口 {start_port} 已被占用，已自动切换到端口 {port}"
                        )
                    return port
        except OSError:
            continue
    raise RuntimeError(
        f"无法找到可用端口，已尝试 {start_port}-{start_port + max_attempts - 1} 共 {max_attempts} 个端口。"
        f"请通过 API_PORT 环境变量指定其他端口。"
    )


def _get_data_dir() -> Path:
    """检测 WSL+NTFS 环境，自动将 DB 目录切换到 Linux 文件系统避免 SQLite WAL 问题。"""
    data_dir = os.getenv('API_PILOT_DATA_DIR')
    if data_dir:
        return Path(data_dir)
    # WSL mirrored 模式下，NTFS 文件系统上的 SQLite WAL 有跨系统 interop 问题
    # 自动将数据目录重定向到 Linux home
    is_wsl_ntfs = False
    try:
        is_wsl_ntfs = (
            'microsoft' in Path('/proc/version').read_text(errors='ignore').lower()
            and str(BASE_DIR).startswith('/mnt/')
        )
    except (FileNotFoundError, OSError):
        pass
    if is_wsl_ntfs:
        linux_data = Path.home() / '.api_pilot'
        linux_data.mkdir(exist_ok=True)
        return linux_data
    return BASE_DIR / 'data'


DATA_DIR = _get_data_dir()


def _load_secret_key() -> str:
    """从环境变量或文件缓存加载 SECRET_KEY，必要时生成新密钥并持久化。"""
    env_key = os.getenv('API_PILOT_SECRET_KEY')
    if env_key:
        return env_key
    key_file = BASE_DIR / '.secret_key'
    if key_file.exists():
        return key_file.read_text().strip()
    new_key = secrets.token_urlsafe(48)  # 生成更长的密钥
    key_file.write_text(new_key)
    # 设置文件权限为仅 owner 可读
    try:
        key_file.chmod(stat.S_IRUSR)
    except (OSError, AttributeError):
        # Windows 系统可能不支持 chmod，忽略错误
        pass
    return new_key


# ── 魔法数字常量 ──────────────────────────────────────────────────────────────
MAX_API_ID: int = 999_999_999
TOKEN_EXPIRY_THRESHOLD_MS: int = 30 * 60 * 1000  # 30 分钟


class Settings:
    API_HOST: str = os.getenv('API_HOST', '127.0.0.1')
    _API_PORT_ENV: int = int(os.getenv('API_PORT', '5000'))
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        f'sqlite+aiosqlite:///{(DATA_DIR / "api_pilot.db").as_posix()}'
    )
    SECRET_KEY: str = _load_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 分钟
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REPORT_RETENTION_DAYS: int = int(os.getenv('REPORT_RETENTION_DAYS', '30'))

    def __init__(self):
        # 开发环境自动查找可用端口，生产环境使用配置的端口
        env = os.getenv('ENVIRONMENT', 'development')
        if env == 'development':
            try:
                self.API_PORT = _find_available_port(self.API_HOST, self._API_PORT_ENV)
            except RuntimeError as e:
                logger.critical(str(e))
                sys.exit(1)
        else:
            self.API_PORT = self._API_PORT_ENV

    # Rate limiting
    RATE_LIMIT_LOGIN: str = os.getenv('RATE_LIMIT_LOGIN', '10/minute')
    RATE_LIMIT_REGISTER: str = os.getenv('RATE_LIMIT_REGISTER', '5/minute')
    RATE_LIMIT_REFRESH: str = os.getenv('RATE_LIMIT_REFRESH', '60/minute')

    # CORS
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', '*')

    # Cloudflare Turnstile
    TURNSTILE_SECRET_KEY: str = os.getenv('TURNSTILE_SECRET_KEY', '')
    TURNSTILE_MODE: str = os.getenv('TURNSTILE_MODE', 'test')  # 'production' | 'test' | 'disabled'

    # 独立安全开关（不依赖 SECRET_KEY，可单独启用）
    ENFORCE_CORS_WHITELIST: bool = os.getenv('ENFORCE_CORS_WHITELIST', 'false').lower() in ('true', '1', 'yes')
    ENFORCE_TURNSTILE_PRODUCTION: bool = os.getenv('ENFORCE_TURNSTILE_PRODUCTION', 'false').lower() in ('true', '1', 'yes')

    # 种子数据配置（生产环境必须通过环境变量设置，默认空字符串）
    SEED_ADMIN_PASSWORD: str = os.getenv('SEED_ADMIN_PASSWORD', '')
    SEED_DEMO_PASSWORD: str = os.getenv('SEED_DEMO_PASSWORD', '')
    SEED_TESTER_PASSWORD: str = os.getenv('SEED_TESTER_PASSWORD', '')

    # 高风险运维接口保护：默认仅开发环境允许执行种子重置/迁移
    ENABLE_DANGEROUS_SEED_ENDPOINTS: bool = os.getenv(
        'ENABLE_DANGEROUS_SEED_ENDPOINTS',
        'true' if os.getenv('ENVIRONMENT', 'development') == 'development' else 'false'
    ).lower() in ('true', '1', 'yes')

    # Mock 电商服务（默认开启，方便种子数据直接跑通）
    MOCK_ECOMMERCE_ENABLED: bool = os.getenv('MOCK_ECOMMERCE_ENABLED', 'true').lower() in ('true', '1', 'yes')

    # 运行环境标识：development / production
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')

    # ── SSRF 防护 ────────────────────────────────────────────────────────────
    # 允许发起 HTTP 请求的目标主机白名单（逗号分隔的 host/IP/CIDR）。
    # 开发环境默认允许 localhost + 私有网段；生产环境应仅配置受信的外部服务地址。
    # 示例：ALLOWED_API_HOSTS='api.example.com,10.0.1.0/24'
    ALLOWED_API_HOSTS: str = os.getenv(
        'ALLOWED_API_HOSTS',
        'localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16'
    )

    # ── Fernet 加密密钥 ──────────────────────────────────────────────────────
    # 变量加密使用 FERNET_ENCRYPTION_KEY 环境变量（32 字节 URL-safe base64 密钥）。
    # 若未设置，系统自动生成并打印警告（开发环境降级行为，生产环境必须设置）。
    # 生成方式: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY_ENV_VAR: str = 'FERNET_ENCRYPTION_KEY'

    # 变量加密密钥（Fernet 对称加密），基于 SECRET_KEY 派生
    @property
    def FERNET_KEY(self) -> str:
        """从 SECRET_KEY 派生 Fernet 兼容密钥（base64 编码的 32 字节）。"""
        import hashlib
        import base64
        key_bytes = hashlib.sha256(self.SECRET_KEY.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == 'production'

    @property
    def turnstile_is_enforced(self) -> bool:
        """Turnstile 人机验证是否强制启用。"""
        return self.TURNSTILE_MODE in ('production', 'test') or self.ENFORCE_TURNSTILE_PRODUCTION

    @property
    def cors_has_restrictions(self) -> bool:
        """CORS 是否有来源限制（非全开模式）。"""
        return self.CORS_ORIGINS != '*' or self.ENFORCE_CORS_WHITELIST


settings = Settings()

# ── 启动安全检查 ──────────────────────────────────────────────────────────────
if settings.is_production and not settings.SECRET_KEY:
    logger.critical(
        "生产环境必须设置 API_PILOT_SECRET_KEY 环境变量（至少 32 字符随机字符串）"
    )
    logger.critical(
        '生成方式: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
    sys.exit(1)

# 生产环境必须使用强密钥，不足32字符直接拒绝启动
if settings.is_production and len(settings.SECRET_KEY) < 32:
    logger.critical(
        f"生产环境 SECRET_KEY 长度仅 {len(settings.SECRET_KEY)} 字符，"
        "必须至少 32 字符以确保安全"
    )
    logger.critical(
        '生成方式: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
    sys.exit(1)

# 开发环境仅警告
if not settings.is_production and len(settings.SECRET_KEY) < 32:
    logger.warning(
        f"SECRET_KEY 长度仅 {len(settings.SECRET_KEY)} 字符，建议至少 32 字符以增强安全性"
    )

if settings.ENFORCE_TURNSTILE_PRODUCTION and settings.is_production:
    if not settings.TURNSTILE_SECRET_KEY:
        logger.critical(
            "ENFORCE_TURNSTILE_PRODUCTION=true 且处于生产环境，"
            "必须通过 TURNSTILE_SECRET_KEY 设置真实密钥"
        )
        sys.exit(1)
    if settings.TURNSTILE_SECRET_KEY == '1x0000000000000000000000000000000AA':
        logger.critical(
            "ENFORCE_TURNSTILE_PRODUCTION=true 但仍在使用 Turnstile 测试密钥，"
            "请通过 TURNSTILE_SECRET_KEY 环境变量设置真实密钥"
        )
        sys.exit(1)
