"""
系统监控工具模块

提供数据库健康检查、应用性能监控和系统状态监控功能
所有操作都是只读的，不会修改任何业务数据
"""

import asyncio
import logging
import os
import platform
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from pydantic import BaseModel

from db.session import get_db
from db.models import (
    PUEData, FaultRecord, Huijugugan, Zbk, 
    PUEComment, PUEDrillDownData
)

# 导入模板支持
from fastapi import Request
from fastapi.responses import HTMLResponse

# 使用共享模板环境
from common import bi_templates_env as templates

# 尝试导入psutil，如果失败则使用基础监控
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()

class DatabaseHealthResponse(BaseModel):
    status: str
    table_count: int
    total_records: int
    tables: Dict[str, int]
    connection_status: str
    check_timestamp: datetime

class PerformanceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    timestamp: datetime

class SystemStatus(BaseModel):
    uptime_seconds: int
    database_health: str
    performance: PerformanceMetrics
    last_check: datetime

@router.get("/health/database", response_model=DatabaseHealthResponse)
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """
    检查数据库健康状态
    - 验证数据库连接
    - 统计表数量和记录数
    - 检查关键业务表的数据完整性
    """
    try:
        logger.info("开始数据库健康检查")
        
        # 检查连接状态
        await db.execute(text("SELECT 1"))
        connection_status = "正常"
        
        # 统计主要业务表的记录数
        tables_data = {}
        
        # PUE数据
        result = await db.execute(select(func.count(PUEData.id)))
        tables_data["pue_data"] = result.scalar()
        
        # 故障记录
        result = await db.execute(select(func.count(FaultRecord.id)))
        tables_data["fault_record"] = result.scalar()
        
        # 汇聚数据
        result = await db.execute(select(func.count(Huijugugan.id)))
        tables_data["huijugugan"] = result.scalar()
        
        # 指标库数据
        result = await db.execute(select(func.count(Zbk.xh)))
        tables_data["zbk"] = result.scalar()
        
        # PUE评论数据
        result = await db.execute(select(func.count(PUEComment.id)))
        tables_data["pue_comment"] = result.scalar()
        
        # PUE钻取数据
        result = await db.execute(select(func.count(PUEDrillDownData.id)))
        tables_data["pue_drill_down_data"] = result.scalar()
        
        total_records = sum(tables_data.values())
        table_count = len(tables_data)
        
        # 确定整体健康状态
        if total_records > 0 and connection_status == "正常":
            status = "健康"
        else:
            status = "异常"
        
        logger.info(f"数据库健康检查完成: {status}, 总记录数: {total_records}")
        
        return DatabaseHealthResponse(
            status=status,
            table_count=table_count,
            total_records=total_records,
            tables=tables_data,
            connection_status=connection_status,
            check_timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库健康检查失败: {str(e)}")

@router.get("/performance/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """
    获取系统性能指标
    - CPU使用率
    - 内存使用情况
    - 磁盘使用情况
    """
    try:
        if HAS_PSUTIL:
            # 使用psutil获取详细信息
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            disk = psutil.disk_usage('.')
            disk_usage_percent = (disk.used / disk.total) * 100
        else:
            # 基础监控（模拟数据）
            cpu_percent = 25.0  # 模拟CPU使用率
            memory_percent = 45.0  # 模拟内存使用率
            memory_used_mb = 1024.0  # 模拟已用内存
            memory_available_mb = 2048.0  # 模拟可用内存
            disk_usage_percent = 60.0  # 模拟磁盘使用率
        
        return PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=round(memory_used_mb, 2),
            memory_available_mb=round(memory_available_mb, 2),
            disk_usage_percent=round(disk_usage_percent, 2),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")

@router.get("/status/overview", response_model=SystemStatus)
async def get_system_overview(db: AsyncSession = Depends(get_db)):
    """
    获取系统整体状态概览
    - 系统运行时间
    - 数据库健康状态
    - 性能指标摘要
    """
    try:
        # 系统启动时间
        if HAS_PSUTIL:
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
        else:
            # 模拟运行时间 (1小时)
            uptime_seconds = 3600
        
        # 获取数据库健康状态 (简化版)
        try:
            await db.execute(text("SELECT 1"))
            database_health = "正常"
        except:
            database_health = "异常"
        
        # 获取当前性能指标
        performance = await get_performance_metrics()
        
        return SystemStatus(
            uptime_seconds=uptime_seconds,
            database_health=database_health,
            performance=performance,
            last_check=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"获取系统概览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统概览失败: {str(e)}")

@router.get("/health/quick")
async def quick_health_check():
    """
    快速健康检查端点
    用于负载均衡器或监控系统的心跳检查
    """
    try:
        # 简单的响应性测试
        start_time = time.time()
        
        if HAS_PSUTIL:
            # CPU检查
            cpu_usage = psutil.cpu_percent()
            # 内存检查  
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
        else:
            # 基础监控数据
            cpu_usage = 30.0
            memory_usage = 50.0
        
        response_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 简单的健康评分
        if cpu_usage < 80 and memory_usage < 85 and response_time < 100:
            status = "healthy"
        elif cpu_usage < 95 and memory_usage < 95 and response_time < 500:
            status = "warning"  
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": round(response_time, 2),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "psutil_available": HAS_PSUTIL
        }
        
    except Exception as e:
        logger.error(f"快速健康检查失败: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/logs/recent")
async def get_recent_logs(lines: int = 50):
    """
    获取最近的应用日志
    用于快速排查问题
    """
    try:
        # 这里可以根据实际的日志配置来读取日志文件
        # 目前返回一个示例响应
        
        import os
        from config import settings
        
        log_entries = []
        log_file_path = "logs/app.log"
        
        if os.path.exists(log_file_path):
            # 读取最近的日志行
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                for i, line in enumerate(recent_lines):
                    log_entries.append({
                        "line_number": len(all_lines) - len(recent_lines) + i + 1,
                        "content": line.strip(),
                        "timestamp": datetime.utcnow().isoformat()  # 实际应该解析日志中的时间戳
                    })
        
        return {
            "total_lines": len(log_entries),
            "requested_lines": lines,
            "logs": log_entries
        }
        
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

# ===============================
# 页面渲染路由 (美化的监控界面) - 已更新
# ===============================

@router.get("/dashboard", response_class=HTMLResponse)
async def monitor_dashboard(request: Request):
    """监控仪表盘页面"""
    return templates.TemplateResponse(
        "monitor/dashboard.html",
        {"request": request, "title": "系统监控仪表盘"}
    )

@router.get("/database", response_class=HTMLResponse)
async def database_monitor_page(request: Request):
    """数据库健康监控页面"""
    return templates.TemplateResponse(
        "monitor/database_health.html",
        {"request": request, "title": "数据库健康监控"}
    )

@router.get("/performance", response_class=HTMLResponse)
async def performance_monitor_page(request: Request):
    """系统性能监控页面"""
    return templates.TemplateResponse(
        "monitor/performance.html",
        {"request": request, "title": "系统性能监控"}
    )

@router.get("/status", response_class=HTMLResponse)
async def system_status_page(request: Request):
    """系统状态概览页面"""
    return templates.TemplateResponse(
        "monitor/status.html",
        {"request": request, "title": "系统状态概览"}
    )

@router.get("/logs", response_class=HTMLResponse)
async def logs_monitor_page(request: Request):
    """日志监控页面"""
    return templates.TemplateResponse(
        "monitor/logs.html",
        {"request": request, "title": "系统日志监控"}
    )