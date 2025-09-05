import os
from typing import List
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    """应用配置类"""
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///db.sqlite3"
    
    # API配置
    DEEPSEEK_API_URL: str = "https://DeepSeek-R1-wzrba.eastus2.models.ai.azure.com/chat/completions"
    DEEPSEEK_API_KEY: str = ""
    
    # 应用配置
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    APP_RELOAD: bool = True
    APP_TITLE: str = "指标管理系统"
    APP_VERSION: str = "1.0.0"
    
    # 安全配置
    SECRET_KEY: str = "your_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # API 配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BI Analytics System"
    DEBUG: bool = True
    
    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000","http://localhost:8080","http://localhost:5173"]
    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10485760
    ALLOWED_FILE_TYPES: List[str] = [".xlsx",".xls",".csv"]
    
    # 缓存配置
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_EXPIRE_TIME: int = 3600
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_FILE_EXTENSIONS: List[str] = [".xlsx", ".xls", ".csv"]
    
    # 缓存配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5分钟
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 创建全局设置实例
settings = Settings()

# 保持向后兼容
DATABASE_URL = settings.DATABASE_URL
