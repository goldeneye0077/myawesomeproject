"""
仪表板数据API模块
提供主页所需的汇总数据和统计信息
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from db.session import get_db
from db.models import (
    PUEData, FaultRecord, Huijugugan, 
    CenterTopTop, LeftTop, RightTop, Bottom
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["仪表板"])


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """获取仪表板汇总数据"""
    try:
        # 获取当前时间
        now = datetime.now()
        current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        # 1. PUE指标统计
        pue_stats = await get_pue_stats(db, current_month, last_month)
        
        # 2. 故障统计
        fault_stats = await get_fault_stats(db, now)
        
        # 3. 网络运行状态
        network_stats = await get_network_stats(db)
        
        # 4. 系统健康度评分（基于各项指标计算）
        health_score = calculate_health_score(pue_stats, fault_stats, network_stats)
        
        return {
            "success": True,
            "data": {
                "pue_stats": pue_stats,
                "fault_stats": fault_stats,
                "network_stats": network_stats,
                "health_score": health_score,
                "last_updated": now.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取仪表板汇总数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


async def get_pue_stats(db: AsyncSession, current_month: datetime, last_month: datetime) -> Dict[str, Any]:
    """获取PUE统计数据"""
    try:
        # 当月PUE平均值
        current_pue_query = select(func.avg(PUEData.pue_value)).where(
            PUEData.year == current_month.year,
            PUEData.month == current_month.month
        )
        current_pue_result = await db.execute(current_pue_query)
        current_pue = current_pue_result.scalar() or 0
        
        # 上月PUE平均值
        last_pue_query = select(func.avg(PUEData.pue_value)).where(
            PUEData.year == last_month.year,
            PUEData.month == last_month.month
        )
        last_pue_result = await db.execute(last_pue_query)
        last_pue = last_pue_result.scalar() or 0
        
        # 计算环比变化
        change_rate = 0
        if last_pue > 0:
            change_rate = ((current_pue - last_pue) / last_pue) * 100
        
        # 最新PUE值
        latest_pue_query = select(PUEData.pue_value).order_by(
            desc(PUEData.year), desc(PUEData.month), desc(PUEData.id)
        ).limit(1)
        latest_pue_result = await db.execute(latest_pue_query)
        latest_pue = latest_pue_result.scalar() or 0
        
        return {
            "current_avg": round(current_pue, 2),
            "last_avg": round(last_pue, 2),
            "change_rate": round(change_rate, 2),
            "latest_value": round(latest_pue, 2),
            "status": "正常" if current_pue <= 1.5 else "关注" if current_pue <= 2.0 else "异常"
        }
    except Exception as e:
        logger.error(f"获取PUE统计失败: {str(e)}")
        return {"current_avg": 0, "last_avg": 0, "change_rate": 0, "latest_value": 0, "status": "未知"}


async def get_fault_stats(db: AsyncSession, now: datetime) -> Dict[str, Any]:
    """获取故障统计数据"""
    try:
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # 今日故障
        today_count_query = select(func.count(FaultRecord.id)).where(
            FaultRecord.start_time >= today
        )
        today_count_result = await db.execute(today_count_query)
        today_count = today_count_result.scalar() or 0
        
        # 本周故障
        week_count_query = select(func.count(FaultRecord.id)).where(
            FaultRecord.start_time >= week_start
        )
        week_count_result = await db.execute(week_count_query)
        week_count = week_count_result.scalar() or 0
        
        # 本月故障
        month_count_query = select(func.count(FaultRecord.id)).where(
            FaultRecord.start_time >= month_start
        )
        month_count_result = await db.execute(month_count_query)
        month_count = month_count_result.scalar() or 0
        
        # 故障类型分布（最近90天）
        ninety_days_ago = now - timedelta(days=90)
        fault_types_query = select(
            FaultRecord.province_fault_type,
            func.count(FaultRecord.id).label('count')
        ).where(
            FaultRecord.start_time >= ninety_days_ago
        ).group_by(FaultRecord.province_fault_type)
        
        fault_types_result = await db.execute(fault_types_query)
        fault_types = []
        for row in fault_types_result:
            fault_types.append({
                "type": row.province_fault_type or "未分类",
                "count": row.count
            })
        
        return {
            "today": today_count,
            "week": week_count,
            "month": month_count,
            "types_distribution": fault_types,
            "status": "正常" if today_count == 0 else "关注" if today_count <= 3 else "异常"
        }
    except Exception as e:
        logger.error(f"获取故障统计失败: {str(e)}")
        return {"today": 0, "week": 0, "month": 0, "types_distribution": [], "status": "未知"}


async def get_network_stats(db: AsyncSession) -> Dict[str, Any]:
    """获取网络运行状态"""
    try:
        # 获取汇聚骨干网络数据总数
        total_query = select(func.count(Huijugugan.id))
        total_result = await db.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # 最新数据时间
        latest_query = select(Huijugugan.created_at).order_by(desc(Huijugugan.created_at)).limit(1)
        latest_result = await db.execute(latest_query)
        latest_time = latest_result.scalar()
        
        # 模拟网络在线率（实际项目中应从真实监控系统获取）
        online_rate = 99.5  # 示例值
        
        return {
            "total_records": total_count,
            "online_rate": online_rate,
            "latest_update": latest_time.isoformat() if latest_time else None,
            "status": "正常" if online_rate >= 99.0 else "关注" if online_rate >= 95.0 else "异常"
        }
    except Exception as e:
        logger.error(f"获取网络统计失败: {str(e)}")
        return {"total_records": 0, "online_rate": 0, "latest_update": None, "status": "未知"}


def calculate_health_score(pue_stats: Dict, fault_stats: Dict, network_stats: Dict) -> Dict[str, Any]:
    """计算系统健康度评分"""
    try:
        score = 100
        
        # PUE评分（30%权重）
        pue_value = pue_stats.get("current_avg", 0)
        if pue_value > 2.0:
            score -= 30
        elif pue_value > 1.8:
            score -= 20
        elif pue_value > 1.5:
            score -= 10
        
        # 故障评分（40%权重）
        today_faults = fault_stats.get("today", 0)
        if today_faults > 5:
            score -= 40
        elif today_faults > 2:
            score -= 25
        elif today_faults > 0:
            score -= 10
        
        # 网络评分（30%权重）
        online_rate = network_stats.get("online_rate", 0)
        if online_rate < 95:
            score -= 30
        elif online_rate < 98:
            score -= 15
        elif online_rate < 99:
            score -= 5
        
        # 确保分数在0-100范围内
        score = max(0, min(100, score))
        
        # 确定健康等级
        if score >= 90:
            level = "优秀"
            color = "green"
        elif score >= 80:
            level = "良好"
            color = "blue"
        elif score >= 70:
            level = "一般"
            color = "yellow"
        elif score >= 60:
            level = "关注"
            color = "orange"
        else:
            level = "异常"
            color = "red"
        
        return {
            "score": score,
            "level": level,
            "color": color
        }
    except Exception as e:
        logger.error(f"计算健康度评分失败: {str(e)}")
        return {"score": 0, "level": "未知", "color": "gray"}


@router.get("/trend/pue")
async def get_pue_trend(months: int = 6, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """获取PUE趋势数据"""
    try:
        # 计算起始月份
        now = datetime.now()
        start_date = now - timedelta(days=30 * months)
        
        # 查询PUE月度数据
        query = select(
            PUEData.year,
            PUEData.month,
            func.avg(PUEData.pue_value).label('avg_pue')
        ).where(
            (PUEData.year * 100 + PUEData.month) >= (start_date.year * 100 + start_date.month)
        ).group_by(
            PUEData.year, PUEData.month
        ).order_by(
            PUEData.year, PUEData.month
        )
        
        result = await db.execute(query)
        data = []
        for row in result:
            data.append({
                "month": f"{row.year}-{str(row.month).zfill(2)}",
                "value": round(row.avg_pue, 2)
            })
        
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"获取PUE趋势数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取趋势数据失败: {str(e)}")


@router.get("/alerts")
async def get_recent_alerts(limit: int = 5, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """获取最近告警信息"""
    try:
        # 获取最近的故障记录作为告警
        query = select(FaultRecord).order_by(desc(FaultRecord.start_time)).limit(limit)
        result = await db.execute(query)
        faults = result.scalars().all()
        
        alerts = []
        for fault in faults:
            alerts.append({
                "id": fault.id,
                "type": "故障告警",
                "message": f"{fault.province_fault_type or '系统故障'}: {fault.fault_name or '无详细描述'}",
                "time": fault.start_time.isoformat() if fault.start_time else None,
                "level": "高" if "严重" in (fault.fault_name or "") else "中"
            })
        
        return {"success": True, "data": alerts}
    except Exception as e:
        logger.error(f"获取告警信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取告警失败: {str(e)}")