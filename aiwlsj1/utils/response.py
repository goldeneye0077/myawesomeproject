"""
统一响应处理模块
提供标准化的API响应格式
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi import status
import logging

logger = logging.getLogger(__name__)

class StandardResponse(BaseModel):
    """标准响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    """分页响应模型"""
    success: bool
    message: str
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    code: Optional[str] = None

def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: str = "SUCCESS"
) -> StandardResponse:
    """成功响应"""
    return StandardResponse(
        success=True,
        message=message,
        data=data,
        code=code
    )

def error_response(
    message: str = "操作失败",
    code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None,
    data: Any = None
) -> StandardResponse:
    """错误响应"""
    return StandardResponse(
        success=False,
        message=message,
        data=data,
        code=code,
        details=details
    )

def paginated_response(
    data: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "查询成功",
    code: str = "SUCCESS"
) -> PaginatedResponse:
    """分页响应"""
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        code=code
    )

def json_response(
    data: Union[StandardResponse, PaginatedResponse, Dict[str, Any]],
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """创建JSON响应"""
    if isinstance(data, (StandardResponse, PaginatedResponse)):
        content = data.dict()
    else:
        content = data
    
    return JSONResponse(
        content=content,
        status_code=status_code
    )

def handle_success(
    data: Any = None,
    message: str = "操作成功",
    code: str = "SUCCESS",
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """处理成功响应"""
    response = success_response(data=data, message=message, code=code)
    logger.info(f"成功响应: {message}")
    return json_response(response, status_code)

def handle_error(
    message: str = "操作失败",
    code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """处理错误响应"""
    response = error_response(message=message, code=code, details=details)
    logger.warning(f"错误响应: {message} (代码: {code})")
    return json_response(response, status_code)

def handle_paginated_success(
    data: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "查询成功",
    code: str = "SUCCESS"
) -> JSONResponse:
    """处理分页成功响应"""
    response = paginated_response(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        message=message,
        code=code
    )
    logger.info(f"分页查询成功: {message} (总计: {total}, 页码: {page})")
    return json_response(response)

def handle_validation_error(
    field: str,
    message: Optional[str] = None
) -> JSONResponse:
    """处理验证错误"""
    error_message = message or f"{field}格式不正确"
    return handle_error(
        message=error_message,
        code="VALIDATION_ERROR",
        details={"field": field},
        status_code=status.HTTP_400_BAD_REQUEST
    )

def handle_not_found(
    resource: str = "资源"
) -> JSONResponse:
    """处理资源未找到"""
    return handle_error(
        message=f"{resource}不存在",
        code="NOT_FOUND",
        details={"resource": resource},
        status_code=status.HTTP_404_NOT_FOUND
    )

def handle_unauthorized(
    message: str = "未授权访问"
) -> JSONResponse:
    """处理未授权"""
    return handle_error(
        message=message,
        code="UNAUTHORIZED",
        status_code=status.HTTP_401_UNAUTHORIZED
    )

def handle_forbidden(
    message: str = "权限不足"
) -> JSONResponse:
    """处理权限不足"""
    return handle_error(
        message=message,
        code="FORBIDDEN",
        status_code=status.HTTP_403_FORBIDDEN
    )

def handle_server_error(
    message: str = "服务器内部错误"
) -> JSONResponse:
    """处理服务器错误"""
    return handle_error(
        message=message,
        code="INTERNAL_SERVER_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )