"""
安全审计日志系统
记录所有安全相关的操作和事件
"""
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

# 创建安全审计日志记录器
security_logger = logging.getLogger("api_pilot.security_audit")


class SecurityEventType(Enum):
    """安全事件类型"""
    # 认证相关
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKE = "token_revoke"
    
    # 授权相关
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    
    # 数据操作
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    DATA_DELETE = "data_delete"
    DATA_MODIFY = "data_modify"
    
    # 系统操作
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    API_KEY_GENERATE = "api_key_generate"
    API_KEY_REVOKE = "api_key_revoke"
    
    # 异常事件
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_INPUT = "invalid_input"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"


class SecurityAudit:
    """
    安全审计日志类
    用于记录和查询安全事件
    """
    
    @staticmethod
    def log_event(
        event_type: SecurityEventType,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        severity: str = "INFO"
    ):
        """
        记录安全事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            username: 用户名
            ip_address: IP地址
            user_agent: 用户代理
            details: 详细信息
            success: 是否成功
            severity: 严重程度 (INFO, WARNING, ERROR, CRITICAL)
        """
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
            "success": success,
            "severity": severity
        }
        
        # 根据严重程度选择日志级别
        log_message = json.dumps(event_data, ensure_ascii=False)
        
        if severity == "CRITICAL":
            security_logger.critical(log_message)
        elif severity == "ERROR":
            security_logger.error(log_message)
        elif severity == "WARNING":
            security_logger.warning(log_message)
        else:
            security_logger.info(log_message)
    
    @staticmethod
    def log_login_success(user_id: int, username: str, ip_address: str, user_agent: str):
        """记录登录成功"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_login_failed(username: str, ip_address: str, user_agent: str, reason: str = "invalid_credentials"):
        """记录登录失败"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.LOGIN_FAILED,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": reason},
            success=False,
            severity="WARNING"
        )
    
    @staticmethod
    def log_access_denied(user_id: Optional[int], username: Optional[str], ip_address: str, resource: str, reason: str):
        """记录访问被拒绝"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.ACCESS_DENIED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details={"resource": resource, "reason": reason},
            success=False,
            severity="WARNING"
        )
    
    @staticmethod
    def log_suspicious_activity(ip_address: str, user_agent: str, details: Dict[str, Any]):
        """记录可疑活动"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=False,
            severity="ERROR"
        )
    
    @staticmethod
    def log_rate_limit_exceeded(ip_address: str, endpoint: str, user_agent: str):
        """记录限流触发"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"endpoint": endpoint},
            success=False,
            severity="WARNING"
        )
    
    @staticmethod
    def log_data_operation(
        event_type: SecurityEventType,
        user_id: int,
        username: str,
        ip_address: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        operation: str = "unknown"
    ):
        """记录数据操作"""
        SecurityAudit.log_event(
            event_type=event_type,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "operation": operation
            }
        )
    
    @staticmethod
    def log_password_change(user_id: int, username: str, ip_address: str):
        """记录密码修改"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.PASSWORD_CHANGE,
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_permission_change(
        admin_user_id: int,
        admin_username: str,
        target_user_id: int,
        target_username: str,
        old_role: str,
        new_role: str,
        ip_address: str
    ):
        """记录权限变更"""
        SecurityAudit.log_event(
            event_type=SecurityEventType.ROLE_CHANGE,
            user_id=admin_user_id,
            username=admin_username,
            ip_address=ip_address,
            details={
                "target_user_id": target_user_id,
                "target_username": target_username,
                "old_role": old_role,
                "new_role": new_role
            }
        )


# 创建全局实例
security_audit = SecurityAudit()