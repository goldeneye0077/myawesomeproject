"""
绩效目标管理API - 独立模块
用于解决fault_analysis_fastapi.py模块加载问题
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from db.session import get_db
from db.models import PerformanceTarget

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/targets", tags=["绩效目标管理"])

@router.post('/save', response_model=Dict[str, Any])
async def save_targets(
    targets_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """保存绩效目标"""
    try:
        print(f"[TARGETS API] 接收到目标数据: {targets_data}")
        logger.info(f"保存绩效目标: {targets_data}")
        
        # 清理当前年份的旧目标
        current_year = datetime.now().year
        await db.execute(
            delete(PerformanceTarget).where(
                and_(
                    PerformanceTarget.year == current_year,
                    PerformanceTarget.status == 'active'
                )
            )
        )
        
        saved_count = 0
        saved_targets = []
        
        # 目标配置映射
        target_configs = {
            'resolution_time_target': '故障解决时间目标',
            'availability_target': '系统可用性目标', 
            'proactive_discovery_target': '主动发现率目标',
            'customer_satisfaction_target': '客户满意度目标'
        }
        
        # 保存每个目标
        for key, name in target_configs.items():
            if key in targets_data and targets_data[key] is not None:
                try:
                    value = float(targets_data[key])
                    if value > 0:
                        new_target = PerformanceTarget(
                            target_name=name,
                            target_category=key,
                            target_value=value,
                            unit='%' if 'rate' in key or 'availability' in key else ('分钟' if 'time' in key else '分'),
                            year=current_year,
                            status='active',
                            created_by='system',
                            effective_date=datetime.utcnow()
                        )
                        db.add(new_target)
                        saved_count += 1
                        saved_targets.append({
                            'category': key,
                            'name': name, 
                            'value': value
                        })
                        print(f"[TARGETS API] 添加目标: {name} = {value}")
                except (ValueError, TypeError) as e:
                    print(f"[TARGETS API] 跳过无效值 {key}: {targets_data[key]} - {e}")
                    continue
        
        # 提交到数据库
        await db.commit()
        print(f"[TARGETS API] 成功保存了 {saved_count} 个目标到数据库")
        
        return {
            'success': True,
            'targets_set': saved_count,
            'saved_targets': saved_targets,
            'message': f'成功保存了 {saved_count} 个绩效目标'
        }
        
    except Exception as e:
        await db.rollback()
        print(f"[TARGETS API] 保存失败: {str(e)}")
        logger.error(f"保存绩效目标失败: {str(e)}")
        return {
            'success': False,
            'targets_set': 0,
            'saved_targets': [],
            'message': f'保存失败: {str(e)}'
        }

@router.get('/list', response_model=Dict[str, Any])
async def get_targets(
    year: Optional[int] = Query(None, description="年份"),
    db: AsyncSession = Depends(get_db)
):
    """获取绩效目标列表"""
    try:
        print(f"[TARGETS API] 获取绩效目标数据")
        logger.info("获取绩效目标列表")
        
        # 构建查询
        query_year = year or datetime.now().year
        query = select(PerformanceTarget).where(
            and_(
                PerformanceTarget.year == query_year,
                PerformanceTarget.status == 'active'
            )
        )
        
        # 执行查询
        result = await db.execute(query.order_by(PerformanceTarget.created_at.desc()))
        targets = result.scalars().all()
        
        # 格式化数据
        targets_data = []
        for target in targets:
            targets_data.append({
                'id': target.id,
                'target_name': target.target_name,
                'target_category': target.target_category,
                'target_value': target.target_value,
                'unit': target.unit,
                'year': target.year,
                'created_at': target.created_at.isoformat() if target.created_at else None
            })
        
        print(f"[TARGETS API] 找到 {len(targets_data)} 个目标")
        
        return {
            'success': True,
            'data': {
                'total_count': len(targets_data),
                'targets': targets_data,
                'year': query_year
            },
            'message': f'成功获取 {len(targets_data)} 个绩效目标'
        }
        
    except Exception as e:
        print(f"[TARGETS API] 获取失败: {str(e)}")
        logger.error(f"获取绩效目标失败: {str(e)}")
        return {
            'success': False,
            'data': {'total_count': 0, 'targets': []},
            'message': f'获取失败: {str(e)}'
        }