from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import traceback
import os

# 导入配置和工具
from config import settings
from utils.logging_config import setup_logging
from utils.response import handle_server_error, handle_error
from utils.exceptions import BaseAppException

# 导入数据库相关
from db.session import engine, get_db
from db.models import Base

# 导入路由
from bi import router as bi_router
from pue import router as pue_router
from huijugugan import router as huiju_router
from bi_data_manage import router as bi_data_manage_router
from bi_api import router as bi_api_router
from fault_analysis_fastapi import router as fault_router
from dashboard_api import router as dashboard_router

# 初始化日志系统
setup_logging()
logger = logging.getLogger(__name__)

# 安全导入绩效目标API
try:
    from performance_targets_api import router as targets_router
    TARGETS_API_AVAILABLE = True
    logger.info("绩效目标API模块加载成功")
except ImportError as e:
    TARGETS_API_AVAILABLE = False
    logger.warning(f"绩效目标API模块不可用: {e}")

# 导入新工具模块路由 (安全集成)
try:
    from tools.system_monitor import router as system_monitor_router
    TOOLS_AVAILABLE = True
    logger.info("工具模块加载成功")
except ImportError as e:
    TOOLS_AVAILABLE = False
    logger.warning(f"工具模块不可用: {e}")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    """处理应用自定义异常"""
    logger.error(f"应用异常: {exc.message} (代码: {exc.code})", exc_info=True)
    return handle_error(
        message=exc.message,
        code=exc.code,
        details=exc.details
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    logger.warning(f"HTTP异常: {exc.detail} (状态码: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", "请求失败"),
            "code": "HTTP_ERROR"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.error(f"未处理异常: {str(exc)}", exc_info=True)
    if settings.APP_DEBUG:
        return handle_error(
            message=f"服务器内部错误: {str(exc)}",
            code="INTERNAL_SERVER_ERROR",
            details={"traceback": traceback.format_exc()}
        )
    else:
        return handle_server_error()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册各业务路由
app.include_router(bi_data_manage_router, prefix="", tags=["数据管理"])
app.include_router(bi_router, prefix="", tags=["商业智能"])
app.include_router(pue_router, prefix="", tags=["PUE指标"])
app.include_router(huiju_router, tags=["汇聚骨干指标"])
app.include_router(bi_api_router, prefix="", tags=["API接口"])
app.include_router(fault_router, tags=["故障分析"])
app.include_router(dashboard_router, prefix="", tags=["仪表板"])

# 条件性注册绩效目标API
if TARGETS_API_AVAILABLE:
    app.include_router(targets_router, tags=["绩效目标"])
    logger.info("绩效目标API路由已注册")

# 安全注册工具模块路由 (可选功能)
if TOOLS_AVAILABLE:
    app.include_router(system_monitor_router, prefix="/tools/monitor", tags=["系统监控工具"])
    logger.info("系统监控工具已集成 - 重新加载完成")

@app.on_event("startup")
async def on_startup():
    """应用启动事件"""
    logger.info("应用启动中...")
    try:
        # 创建数据库表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
        raise
    
    logger.info(f"应用启动完成，运行在 http://{settings.APP_HOST}:{settings.APP_PORT}")

@app.on_event("shutdown")
async def on_shutdown():
    """应用关闭事件"""
    logger.info("应用关闭中...")

# 健康检查端点
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "message": "指标管理系统运行正常",
        "version": settings.APP_VERSION
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("启动开发服务器...")
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )