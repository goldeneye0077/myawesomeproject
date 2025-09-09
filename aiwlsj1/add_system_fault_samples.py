#!/usr/bin/env python3
"""
添加系统故障记录样本数据
"""
import asyncio
import sys
from datetime import datetime, timedelta
from db.session import AsyncSessionLocal
from db.models import SystemFaultLog

async def add_sample_system_faults():
    """添加示例系统故障记录"""
    async with AsyncSessionLocal() as session:
        try:
            # 创建一些示例故障记录
            sample_faults = [
                SystemFaultLog(
                    fault_type="database",
                    severity="warning",
                    title="数据库连接超时",
                    description="连接数据库时发生超时，可能是网络延迟导致",
                    error_message="Connection timeout after 30 seconds",
                    affected_module="database_connection",
                    user_impact="low",
                    status="resolved",
                    resolved_at=datetime.utcnow() - timedelta(hours=2),
                    resolution_notes="重启数据库连接池解决问题",
                    occurred_at=datetime.utcnow() - timedelta(hours=4),
                    environment="production"
                ),
                SystemFaultLog(
                    fault_type="api",
                    severity="error",
                    title="PUE数据API响应异常",
                    description="获取PUE趋势数据时API返回空结果",
                    error_message="Empty result set returned from PUE data query",
                    affected_module="pue_api",
                    user_impact="medium",
                    status="resolved",
                    resolved_at=datetime.utcnow() - timedelta(hours=1),
                    resolution_notes="修复数据查询条件，扩大查询范围",
                    occurred_at=datetime.utcnow() - timedelta(hours=6),
                    environment="production"
                ),
                SystemFaultLog(
                    fault_type="system",
                    severity="info",
                    title="内存使用率超过70%",
                    description="系统内存使用率达到75%，建议关注",
                    affected_module="system_monitor",
                    user_impact="none",
                    status="resolved",
                    resolved_at=datetime.utcnow() - timedelta(minutes=30),
                    resolution_notes="清理临时文件，内存使用率恢复正常",
                    occurred_at=datetime.utcnow() - timedelta(hours=2),
                    environment="production"
                ),
                SystemFaultLog(
                    fault_type="application",
                    severity="warning",
                    title="图表渲染缓慢",
                    description="ECharts图表初始化时间超过5秒",
                    error_message="Chart initialization timeout",
                    affected_module="charts_renderer",
                    user_impact="low",
                    status="open",
                    occurred_at=datetime.utcnow() - timedelta(hours=1),
                    environment="production"
                ),
                SystemFaultLog(
                    fault_type="database",
                    severity="info",
                    title="数据库维护完成",
                    description="定期数据库维护任务成功完成",
                    affected_module="database_maintenance",
                    user_impact="none",
                    status="closed",
                    resolved_at=datetime.utcnow() - timedelta(minutes=15),
                    resolution_notes="数据库优化完成，性能提升约15%",
                    occurred_at=datetime.utcnow() - timedelta(hours=1),
                    environment="production"
                )
            ]
            
            # 添加记录到数据库
            for fault in sample_faults:
                session.add(fault)
            
            await session.commit()
            print(f"成功添加 {len(sample_faults)} 条系统故障记录")
            
        except Exception as e:
            await session.rollback()
            print(f"添加样本数据失败: {e}")
            return False
        
        return True

if __name__ == "__main__":
    asyncio.run(add_sample_system_faults())