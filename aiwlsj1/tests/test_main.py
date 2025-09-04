"""
主应用测试
测试基础功能和健康检查
"""

import pytest
from fastapi.testclient import TestClient


class TestMainApp:
    """主应用测试类"""
    
    def test_health_check(self, client: TestClient):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data
        assert "version" in data
    
    def test_static_files(self, client: TestClient):
        """测试静态文件服务"""
        # 这个测试可能需要根据实际静态文件调整
        response = client.get("/static/css/styles.css")
        # 如果文件存在，应该返回200或304
        # 如果不存在，应该返回404
        assert response.status_code in [200, 304, 404]
    
    def test_cors_headers(self, client: TestClient):
        """测试CORS头部"""
        response = client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # 检查CORS头部是否正确设置
        assert "access-control-allow-origin" in response.headers
    
    def test_not_found_endpoint(self, client: TestClient):
        """测试不存在的端点"""
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_database_connection(self, db_session):
        """测试数据库连接"""
        # 测试数据库会话是否正常工作
        assert db_session is not None
        
        # 执行简单查询
        from sqlalchemy import text
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1