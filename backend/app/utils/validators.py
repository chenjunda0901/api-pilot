"""
输入验证工具 - 防止 SQL 注入、XSS、命令注入等安全威胁
"""

import re
import html
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# 危险字符模式
DANGEROUS_PATTERNS = {
    "sql_injection": [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bOR\b.*=.*\b)",
        r"(\bAND\b.*=.*\b)",
        r"('|\"|;|\\)",
        r"(0x[0-9a-f]+)",
    ],
    "xss": [
        r"(<script[^>]*>.*?</script>)",
        r"(<iframe[^>]*>.*?</iframe>)",
        r"(<img[^>]+onerror[^=]*=)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<svg[^>]*onload[^=]*=)",
    ],
    "command_injection": [
        r"[;&|`$]",
        r"(\|\||&&)",
        r"(\$\()",
        r"(`.*`)",
        r"(>.*>|\|)",
    ],
}


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str]
    sanitized_value: Any = None


class ValidationType(Enum):
    """验证类型"""
    STRING = "string"
    EMAIL = "email"
    URL = "url"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    UUID = "uuid"
    PATH = "path"
    JSON = "json"
    SQL_SAFE = "sql_safe"
    HTML_SAFE = "html_safe"


class InputValidator:
    """
    输入验证器
    
    特性：
    - 类型检查
    - SQL 注入防护
    - XSS 防护
    - 白名单验证
    - 自动清理
    """
    
    # 允许的 HTTP 方法
    ALLOWED_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    
    # 允许的 HTTP 状态码范围
    ALLOWED_STATUS_CODES = range(100, 600)
    
    @staticmethod
    def validate_string(
        value: Any,
        min_length: int = 0,
        max_length: int = 65535,
        pattern: Optional[str] = None,
        allow_empty: bool = False,
    ) -> ValidationResult:
        """验证字符串"""
        errors = []
        sanitized = None
        
        if value is None:
            if allow_empty:
                return ValidationResult(True, [], "")
            return ValidationResult(False, ["Value is required"], None)
        
        if not isinstance(value, str):
            return ValidationResult(False, ["Value must be a string"], None)
        
        value = value.strip()
        
        if len(value) < min_length:
            errors.append(f"Length must be at least {min_length} characters")
        
        if len(value) > max_length:
            errors.append(f"Length must not exceed {max_length} characters")
        
        if pattern and not re.match(pattern, value):
            errors.append(f"Value does not match pattern: {pattern}")
        
        sanitized = value
        
        return ValidationResult(len(errors) == 0, errors, sanitized)
    
    @staticmethod
    def validate_email(value: Any) -> ValidationResult:
        """验证邮箱"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        base_result = InputValidator.validate_string(value, max_length=254)
        if not base_result.valid:
            return base_result
        
        if not re.match(pattern, base_result.sanitized_value):
            return ValidationResult(False, ["Invalid email format"], None)
        
        return ValidationResult(True, [], base_result.sanitized_value)
    
    @staticmethod
    def validate_url(value: Any, allow_empty: bool = False) -> ValidationResult:
        """验证 URL"""
        base_result = InputValidator.validate_string(value, allow_empty=allow_empty)
        if not base_result.valid:
            return base_result
        
        # URL 白名单：仅允许 http/https
        pattern = r'^https?://[^\s]+$'
        if not re.match(pattern, base_result.sanitized_value):
            return ValidationResult(False, ["URL must start with http:// or https://"], None)
        
        return ValidationResult(True, [], base_result.sanitized_value)
    
    @staticmethod
    def validate_integer(
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> ValidationResult:
        """验证整数"""
        errors = []
        
        if value is None:
            return ValidationResult(False, ["Value is required"], None)
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return ValidationResult(False, ["Value must be an integer"], None)
        
        if min_value is not None and int_value < min_value:
            errors.append(f"Value must be at least {min_value}")
        
        if max_value is not None and int_value > max_value:
            errors.append(f"Value must not exceed {max_value}")
        
        return ValidationResult(len(errors) == 0, errors, int_value)
    
    @staticmethod
    def validate_sql_safe(value: Any, max_length: int = 10000) -> ValidationResult:
        """验证 SQL 安全字符串"""
        base_result = InputValidator.validate_string(value, max_length=max_length)
        if not base_result.valid:
            return base_result
        
        # 检查危险模式
        for pattern in DANGEROUS_PATTERNS["sql_injection"]:
            if re.search(pattern, base_result.sanitized_value, re.IGNORECASE):
                return ValidationResult(
                    False,
                    ["Potential SQL injection detected"],
                    None,
                )
        
        # 清理危险字符
        sanitized = base_result.sanitized_value
        for char in ["'", '"', ";", "\\", "--", "/*", "*/"]:
            sanitized = sanitized.replace(char, "")
        
        return ValidationResult(True, [], sanitized)
    
    @staticmethod
    def validate_html_safe(value: Any, max_length: int = 100000) -> ValidationResult:
        """验证 HTML 安全字符串"""
        base_result = InputValidator.validate_string(value, max_length=max_length)
        if not base_result.valid:
            return base_result
        
        # 检查 XSS 模式
        for pattern in DANGEROUS_PATTERNS["xss"]:
            if re.search(pattern, base_result.sanitized_value, re.IGNORECASE):
                return ValidationResult(
                    False,
                    ["Potential XSS attack detected"],
                    None,
                )
        
        # HTML 转义
        sanitized = html.escape(base_result.sanitized_value)
        
        return ValidationResult(True, [], sanitized)
    
    @staticmethod
    def validate_path(value: Any, allow_empty: bool = False) -> ValidationResult:
        """验证文件路径"""
        base_result = InputValidator.validate_string(value, allow_empty=allow_empty)
        if not base_result.valid:
            return base_result
        
        # 检查路径遍历
        if ".." in base_result.sanitized_value:
            return ValidationResult(False, ["Path traversal not allowed"], None)
        
        # 检查危险字符
        for char in ["$", "`", "|", "&", ";", "<", ">"]:
            if char in base_result.sanitized_value:
                return ValidationResult(False, [f"Character '{char}' not allowed in path"], None)
        
        return ValidationResult(True, [], base_result.sanitized_value)
    
    @staticmethod
    def validate_uuid(value: Any) -> ValidationResult:
        """验证 UUID 格式"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        base_result = InputValidator.validate_string(value, max_length=36)
        if not base_result.valid:
            return base_result
        
        if not re.match(pattern, base_result.sanitized_value.lower()):
            return ValidationResult(False, ["Invalid UUID format"], None)
        
        return ValidationResult(True, [], base_result.sanitized_value.lower())
    
    @staticmethod
    def validate_http_method(method: Any) -> ValidationResult:
        """验证 HTTP 方法"""
        if not isinstance(method, str):
            return ValidationResult(False, ["HTTP method must be a string"], None)
        
        method = method.upper()
        if method not in InputValidator.ALLOWED_HTTP_METHODS:
            return ValidationResult(
                False,
                [f"HTTP method must be one of: {', '.join(InputValidator.ALLOWED_HTTP_METHODS)}"],
                None,
            )
        
        return ValidationResult(True, [], method)
    
    @staticmethod
    def validate_json(value: Any) -> ValidationResult:
        """验证 JSON 格式"""
        import json
        
        if isinstance(value, dict):
            return ValidationResult(True, [], value)
        
        base_result = InputValidator.validate_string(value)
        if not base_result.valid:
            return base_result
        
        try:
            parsed = json.loads(base_result.sanitized_value)
            return ValidationResult(True, [], parsed)
        except json.JSONDecodeError as e:
            return ValidationResult(False, [f"Invalid JSON: {e}"], None)
    
    @staticmethod
    def validate_dict(data: Any, required_fields: List[str], optional_fields: Optional[List[str]] = None) -> ValidationResult:
        """验证字典数据"""
        errors = []
        validated_data = {}
        
        if not isinstance(data, dict):
            return ValidationResult(False, ["Data must be a dictionary"], None)
        
        # 检查必需字段
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
            else:
                validated_data[field] = data[field]
        
        # 复制可选字段
        if optional_fields:
            for field in optional_fields:
                if field in data:
                    validated_data[field] = data[field]
        
        return ValidationResult(len(errors) == 0, errors, validated_data if errors else validated_data)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名，移除危险字符"""
        # 移除路径分隔符
        filename = filename.replace("/", "").replace("\\", "")
        # 移除控制字符
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        # 只保留字母、数字、下划线、连字符、点和空格
        filename = re.sub(r'[^a-zA-Z0-9_.\-\s]', '', filename)
        # 限制长度
        filename = filename[:255]
        return filename.strip()
    
    @staticmethod
    def sanitize_html(value: str) -> str:
        """HTML 转义"""
        return html.escape(value)
    
    @staticmethod
    def validate_request_data(data: Dict[str, Any], schema: Dict[str, type]) -> ValidationResult:
        """验证请求数据"""
        errors = []
        validated = {}
        
        for field, expected_type in schema.items():
            if field not in data:
                if expected_type != Optional:
                    errors.append(f"Missing field: {field}")
                continue
            
            value = data[field]
            
            # 类型检查
            if expected_type is str:
                result = InputValidator.validate_string(value)
            elif expected_type is int:
                result = InputValidator.validate_integer(value)
            elif expected_type is bool:
                result = ValidationResult(isinstance(value, bool), ["Must be boolean"], value)
            elif expected_type is list:
                result = ValidationResult(isinstance(value, list), ["Must be list"], value)
            elif expected_type is dict:
                result = ValidationResult(isinstance(value, dict), ["Must be dict"], value)
            else:
                result = ValidationResult(True, [], value)
            
            if not result.valid:
                errors.extend([f"{field}: {e}" for e in result.errors])
            else:
                validated[field] = result.sanitized_value
        
        return ValidationResult(len(errors) == 0, errors, validated if errors else validated)


# 全局验证器实例
_validator = InputValidator()


def validate(value: Any, validation_type: ValidationType, **kwargs) -> ValidationResult:
    """便捷的验证函数"""
    if validation_type == ValidationType.STRING:
        return _validator.validate_string(value, **kwargs)
    elif validation_type == ValidationType.EMAIL:
        return _validator.validate_email(value)
    elif validation_type == ValidationType.URL:
        return _validator.validate_url(value, **kwargs)
    elif validation_type == ValidationType.INTEGER:
        return _validator.validate_integer(value, **kwargs)
    elif validation_type == ValidationType.SQL_SAFE:
        return _validator.validate_sql_safe(value, **kwargs)
    elif validation_type == ValidationType.HTML_SAFE:
        return _validator.validate_html_safe(value, **kwargs)
    elif validation_type == ValidationType.PATH:
        return _validator.validate_path(value, **kwargs)
    elif validation_type == ValidationType.UUID:
        return _validator.validate_uuid(value)
    elif validation_type == ValidationType.JSON:
        return _validator.validate_json(value)
    else:
        return ValidationResult(True, [], value)


def sanitize(value: str, type: str = "html") -> str:
    """便捷的清理函数"""
    if type == "html":
        return _validator.sanitize_html(value)
    elif type == "filename":
        return _validator.sanitize_filename(value)
    return value