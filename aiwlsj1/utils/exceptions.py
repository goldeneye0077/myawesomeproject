"""
统一异常处理模块
提供标准化的异常类和错误处理机制
"""

from fastapi import HTTPException
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAppException(Exception):
    """应用基础异常类"""
    def __init__(
        self, 
        message: str, 
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class DatabaseException(BaseAppException):
    """数据库操作异常"""
    def __init__(self, message: str = "数据库操作失败", **kwargs):
        super().__init__(message, code="DATABASE_ERROR", **kwargs)

class ValidationException(BaseAppException):
    """数据验证异常"""
    def __init__(self, message: str = "数据验证失败", **kwargs):
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)

class FileUploadException(BaseAppException):
    """文件上传异常"""
    def __init__(self, message: str = "文件上传失败", **kwargs):
        super().__init__(message, code="FILE_UPLOAD_ERROR", **kwargs)

class ExternalAPIException(BaseAppException):
    """外部API调用异常"""
    def __init__(self, message: str = "外部服务调用失败", **kwargs):
        super().__init__(message, code="EXTERNAL_API_ERROR", **kwargs)

class AuthenticationException(BaseAppException):
    """认证异常"""
    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(message, code="AUTHENTICATION_ERROR", **kwargs)

class AuthorizationException(BaseAppException):
    """授权异常"""
    def __init__(self, message: str = "权限不足", **kwargs):
        super().__init__(message, code="AUTHORIZATION_ERROR", **kwargs)

def create_http_exception(
    status_code: int,
    message: str,
    code: str = "UNKNOWN_ERROR",
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """创建标准化的HTTP异常"""
    return HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "code": code,
            "details": details or {}
        }
    )

def handle_database_error(error: Exception, operation: str = "数据库操作") -> HTTPException:
    """处理数据库错误"""
    logger.error(f"{operation}失败: {str(error)}", exc_info=True)
    return create_http_exception(
        status_code=500,
        message=f"{operation}失败，请稍后重试",
        code="DATABASE_ERROR",
        details={"operation": operation}
    )

def handle_validation_error(error: Exception, field: str = "数据") -> HTTPException:
    """处理数据验证错误"""
    logger.warning(f"{field}验证失败: {str(error)}")
    return create_http_exception(
        status_code=400,
        message=f"{field}格式不正确",
        code="VALIDATION_ERROR",
        details={"field": field}
    )

def handle_file_upload_error(error: Exception, filename: str = "文件") -> HTTPException:
    """处理文件上传错误"""
    logger.error(f"文件上传失败 ({filename}): {str(error)}", exc_info=True)
    return create_http_exception(
        status_code=400,
        message=f"文件上传失败: {filename}",
        code="FILE_UPLOAD_ERROR",
        details={"filename": filename}
    )

def handle_external_api_error(error: Exception, service: str = "外部服务") -> HTTPException:
    """处理外部API调用错误"""
    logger.error(f"{service}调用失败: {str(error)}", exc_info=True)
    return create_http_exception(
        status_code=503,
        message=f"{service}暂时不可用，请稍后重试",
        code="EXTERNAL_API_ERROR",
        details={"service": service}
    )