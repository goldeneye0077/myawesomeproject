"""
pytest配置文件
定义测试夹具和共享配置
"""

import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from db.models import Base
from db.session import get_db

# 测试数据库URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建测试数据库引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False  # 测试时不显示SQL日志
)

TestSessionLocal = sessionmaker(
    test_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """创建会话级别的事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """创建测试数据库"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """创建数据库会话"""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """创建测试客户端"""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # 清理依赖覆盖
    app.dependency_overrides.clear()

@pytest.fixture
def sample_data():
    """提供示例测试数据"""
    return {
        "indicator_data": {
            "name": "测试指标",
            "value": 85.5,
            "category": "性能指标",
            "description": "这是一个测试指标"
        },
        "pue_data": {
            "location": "测试机房",
            "month": "1",
            "year": "2025",
            "pue_value": 1.45
        },
        "fault_data": {
            "fault_type": "网络故障",
            "severity": "高",
            "description": "测试故障记录"
        }
    }

@pytest.fixture
async def create_test_data(db_session: AsyncSession, sample_data):
    """创建测试数据"""
    # 这里可以根据需要创建测试数据
    created_data = {}
    
    # 创建指标数据
    # indicator = YourModel(**sample_data["indicator_data"])
    # db_session.add(indicator)
    # await db_session.commit()
    # await db_session.refresh(indicator)
    # created_data["indicator"] = indicator
    
    yield created_data
    
    # 清理测试数据（可选，因为每次测试后会回滚）
    pass

# API测试夹具
@pytest.fixture
def api_headers():
    """API请求头"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

# 测试配置
@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    import os
    os.environ["APP_DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    yield
    # 清理测试环境
    pass