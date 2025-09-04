"""
工具模块测试
测试异常处理、响应处理等工具函数
"""

import pytest
from fastapi import HTTPException

from utils.exceptions import (
    BaseAppException, 
    DatabaseException, 
    ValidationException,
    FileUploadException,
    create_http_exception,
    handle_database_error,
    handle_validation_error
)
from utils.response import (
    success_response,
    error_response,
    paginated_response,
    handle_success,
    handle_error,
    handle_paginated_success
)


class TestExceptions:
    """异常处理测试"""
    
    def test_base_app_exception(self):
        """测试基础应用异常"""
        exc = BaseAppException("测试消息", "TEST_CODE", {"detail": "测试详情"})
        
        assert str(exc) == "测试消息"
        assert exc.message == "测试消息"
        assert exc.code == "TEST_CODE"
        assert exc.details == {"detail": "测试详情"}
    
    def test_database_exception(self):
        """测试数据库异常"""
        exc = DatabaseException("数据库错误")
        
        assert exc.code == "DATABASE_ERROR"
        assert exc.message == "数据库错误"
    
    def test_validation_exception(self):
        """测试验证异常"""
        exc = ValidationException("验证失败", details={"field": "name"})
        
        assert exc.code == "VALIDATION_ERROR"
        assert exc.message == "验证失败"
        assert exc.details["field"] == "name"
    
    def test_create_http_exception(self):
        """测试HTTP异常创建"""
        exc = create_http_exception(400, "错误消息", "TEST_CODE")
        
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 400
        assert exc.detail["message"] == "错误消息"
        assert exc.detail["code"] == "TEST_CODE"
    
    def test_handle_database_error(self):
        """测试数据库错误处理"""
        error = Exception("数据库连接失败")
        result = handle_database_error(error, "查询用户")
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 500
        assert "查询用户失败" in result.detail["message"]
    
    def test_handle_validation_error(self):
        """测试验证错误处理"""
        error = ValueError("无效的输入")
        result = handle_validation_error(error, "用户名")
        
        assert isinstance(result, HTTPException)
        assert result.status_code == 400
        assert "用户名格式不正确" in result.detail["message"]


class TestResponse:
    """响应处理测试"""
    
    def test_success_response(self):
        """测试成功响应"""
        data = {"id": 1, "name": "测试"}
        response = success_response(data, "操作成功", "SUCCESS")
        
        assert response.success is True
        assert response.message == "操作成功"
        assert response.data == data
        assert response.code == "SUCCESS"
    
    def test_error_response(self):
        """测试错误响应"""
        details = {"field": "name", "error": "required"}
        response = error_response("操作失败", "ERROR", details)
        
        assert response.success is False
        assert response.message == "操作失败"
        assert response.code == "ERROR"
        assert response.details == details
    
    def test_paginated_response(self):
        """测试分页响应"""
        data = [{"id": 1}, {"id": 2}]
        response = paginated_response(data, total=50, page=2, page_size=20)
        
        assert response.success is True
        assert response.data == data
        assert response.total == 50
        assert response.page == 2
        assert response.page_size == 20
        assert response.total_pages == 3  # math.ceil(50/20) = 3
    
    def test_handle_success(self):
        """测试成功处理器"""
        result = handle_success({"test": "data"}, "测试成功")
        
        assert result.status_code == 200
        # 检查响应内容
        import json
        content = json.loads(result.body.decode())
        assert content["success"] is True
        assert content["message"] == "测试成功"
        assert content["data"]["test"] == "data"
    
    def test_handle_error(self):
        """测试错误处理器"""
        result = handle_error("测试错误", "TEST_ERROR")
        
        assert result.status_code == 400
        # 检查响应内容
        import json
        content = json.loads(result.body.decode())
        assert content["success"] is False
        assert content["message"] == "测试错误"
        assert content["code"] == "TEST_ERROR"
    
    def test_handle_paginated_success(self):
        """测试分页成功处理器"""
        data = [{"id": 1}, {"id": 2}]
        result = handle_paginated_success(data, 100, 1, 10)
        
        assert result.status_code == 200
        # 检查响应内容
        import json
        content = json.loads(result.body.decode())
        assert content["success"] is True
        assert content["total"] == 100
        assert content["page"] == 1
        assert len(content["data"]) == 2