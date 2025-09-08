#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障指标分析模块 - FastAPI版本
提供故障数据的分析和可视化功能
"""

from fastapi import APIRouter, Request, Depends, Query, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy import func, extract, and_, or_, distinct, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.session import get_db
from db.models import FaultRecord
from datetime import datetime, timedelta
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# 创建路由器
router = APIRouter(prefix="/fault", tags=["故障分析"])

# 配置模板
templates = Jinja2Templates(directory="templates")

def convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

# 配置日志
logger = logging.getLogger(__name__)

@router.get('/dashboard_client')
async def fault_dashboard_client(request: Request):
    """故障分析仪表板主页面（客户端渲染版）"""
    return templates.TemplateResponse('fault_dashboard.html', {'request': request})

# 与侧边栏导航保持一致的别名路由，确保 /fault/dashboard 进入客户端仪表板
@router.get('/dashboard')
async def fault_dashboard_alias(request: Request):
    """故障分析仪表板主页面（别名: /dashboard）"""
    return templates.TemplateResponse('fault_dashboard.html', {'request': request})

@router.get('/prediction', response_class=HTMLResponse)
async def fault_prediction_page(request: Request):
    """故障预测分析页面"""
    return templates.TemplateResponse(
        'fault_prediction.html',
        {'request': request, 'title': '故障预测分析'}
    )

@router.get('/indicators', response_class=HTMLResponse)
async def indicators_management_page(request: Request):
    """指标管理与绩效评估页面"""
    return templates.TemplateResponse(
        'indicators_management.html',
        {'request': request, 'title': '指标管理与绩效评估'}
    )

@router.get('/api/overview')
async def fault_overview(db: AsyncSession = Depends(get_db)):
    """获取故障概览数据"""
    try:
        # 总故障数
        result = await db.execute(select(func.count()).select_from(FaultRecord))
        total_faults = result.scalar()
        
        # 本月故障数
        current_month = datetime.now().replace(day=1)
        result = await db.execute(select(func.count()).select_from(FaultRecord).where(
            FaultRecord.fault_date >= current_month
        ))
        monthly_faults = result.scalar()
        
        # 平均处理时长
        result = await db.execute(select(func.avg(FaultRecord.fault_duration_hours)))
        avg_duration = result.scalar()
        avg_duration = round(avg_duration, 2) if avg_duration else 0
        
        # 主动发现率
        result = await db.execute(select(func.count()).select_from(FaultRecord).where(
            FaultRecord.is_proactive_discovery.isnot(None)
        ))
        total_with_discovery = result.scalar()
        
        result = await db.execute(select(func.count()).select_from(FaultRecord).where(
            FaultRecord.is_proactive_discovery == '是'
        ))
        proactive_count = result.scalar()
        
        proactive_rate = round((proactive_count / total_with_discovery * 100), 2) if total_with_discovery > 0 else 0
        
        return JSONResponse({
            'success': True,
            'data': {
                'total_faults': total_faults,
                'monthly_faults': monthly_faults,
                'avg_duration': avg_duration,
                'proactive_rate': proactive_rate
            }
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/trend')
async def fault_trend(db: AsyncSession = Depends(get_db)):
    """获取故障趋势数据"""
    try:
        # 按月统计故障数量
        year_col = extract('year', FaultRecord.fault_date).label('year')
        month_col = extract('month', FaultRecord.fault_date).label('month')
        stmt = select(
            year_col,
            month_col,
            func.count(FaultRecord.id).label('count')
        ).where(
            FaultRecord.fault_date.isnot(None)
        ).group_by(
            year_col,
            month_col
        ).order_by(year_col, month_col)
        result = await db.execute(stmt)
        monthly_stats = result.all()
        
        # 格式化数据
        trend_data = []
        for year, month, count in monthly_stats:
            trend_data.append({
                'date': f"{int(year)}-{int(month):02d}",
                'count': count
            })
        
        return JSONResponse({
            'success': True,
            'data': trend_data
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/category_analysis')
async def fault_category_analysis(db: AsyncSession = Depends(get_db)):
    """故障分类分析"""
    try:
        # 按原因分类统计
        stmt_cause = select(
            FaultRecord.cause_category,
            func.count(FaultRecord.id).label('count')
        ).where(
            FaultRecord.cause_category.isnot(None),
            FaultRecord.cause_category != ''
        ).group_by(FaultRecord.cause_category)
        result = await db.execute(stmt_cause)
        cause_stats = result.all()
        
        # 按故障类型统计
        stmt_type = select(
            FaultRecord.province_fault_type,
            func.count(FaultRecord.id).label('count')
        ).where(
            FaultRecord.province_fault_type.isnot(None),
            FaultRecord.province_fault_type != ''
        ).group_by(FaultRecord.province_fault_type)
        result = await db.execute(stmt_type)
        type_stats = result.all()
        
        # 按通报级别统计
        stmt_level = select(
            FaultRecord.notification_level,
            func.count(FaultRecord.id).label('count')
        ).where(
            FaultRecord.notification_level.isnot(None),
            FaultRecord.notification_level != ''
        ).group_by(FaultRecord.notification_level)
        result = await db.execute(stmt_level)
        level_stats = result.all()
        
        return JSONResponse({
            'success': True,
            'data': {
                'cause_category': [{'name': name, 'value': count} for name, count in cause_stats],
                'fault_type': [{'name': name, 'value': count} for name, count in type_stats],
                'notification_level': [{'name': name, 'value': count} for name, count in level_stats]
            }
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/duration_analysis')
async def fault_duration_analysis(db: AsyncSession = Depends(get_db)):
    """故障处理时长分析"""
    try:
        # 按时长区间统计
        duration_ranges = [
            ('0-2小时', 0, 2),
            ('2-6小时', 2, 6),
            ('6-12小时', 6, 12),
            ('12-24小时', 12, 24),
            ('24小时以上', 24, float('inf'))
        ]
        
        duration_stats = []
        for range_name, min_hours, max_hours in duration_ranges:
            if max_hours == float('inf'):
                stmt = select(func.count()).select_from(FaultRecord).where(
                    FaultRecord.fault_duration_hours >= min_hours
                )
            else:
                stmt = select(func.count()).select_from(FaultRecord).where(
                    and_(
                        FaultRecord.fault_duration_hours >= min_hours,
                        FaultRecord.fault_duration_hours < max_hours
                    )
                )
            result = await db.execute(stmt)
            count = result.scalar() or 0
            duration_stats.append({
                'range': range_name,
                'count': count
            })
        
        # 平均处理时长趋势（按月）
        year_col = extract('year', FaultRecord.fault_date).label('year')
        month_col = extract('month', FaultRecord.fault_date).label('month')
        stmt_avg = select(
            year_col,
            month_col,
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_duration_hours.isnot(None)
            )
        ).group_by(
            year_col,
            month_col
        ).order_by(year_col, month_col)
        result = await db.execute(stmt_avg)
        monthly_avg_duration = result.all()
        
        duration_trend = []
        for year, month, avg_duration in monthly_avg_duration:
            duration_trend.append({
                'date': f"{int(year)}-{int(month):02d}",
                'avg_duration': round(avg_duration, 2) if avg_duration else 0
            })
        
        return JSONResponse({
            'success': True,
            'data': {
                'duration_distribution': duration_stats,
                'duration_trend': duration_trend
            }
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/proactive_analysis')
async def fault_proactive_analysis(db: AsyncSession = Depends(get_db)):
    """主动发现分析"""
    try:
        # 主动发现vs被动发现统计
        stmt_proactive = select(
            FaultRecord.is_proactive_discovery,
            func.count(FaultRecord.id).label('count')
        ).where(
            FaultRecord.is_proactive_discovery.isnot(None)
        ).group_by(FaultRecord.is_proactive_discovery)
        result = await db.execute(stmt_proactive)
        proactive_stats = result.all()
        
        # 主动发现率趋势（按月）
        year_col = extract('year', FaultRecord.fault_date).label('year')
        month_col = extract('month', FaultRecord.fault_date).label('month')
        case_expr = case((FaultRecord.is_proactive_discovery == '是', 1), else_=0)
        stmt_monthly = select(
            year_col,
            month_col,
            func.sum(case_expr).label('proactive_count'),
            func.count(FaultRecord.id).label('total_count')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.is_proactive_discovery.isnot(None)
            )
        ).group_by(
            year_col,
            month_col
        ).order_by(year_col, month_col)
        result = await db.execute(stmt_monthly)
        monthly_proactive = result.all()
        
        proactive_trend = []
        for year, month, proactive_count, total_count in monthly_proactive:
            rate = round((proactive_count / total_count * 100), 2) if total_count > 0 else 0
            proactive_trend.append({
                'date': f"{int(year)}-{int(month):02d}",
                'proactive_rate': rate,
                'proactive_count': proactive_count,
                'total_count': total_count
            })
        
        return JSONResponse({
            'success': True,
            'data': {
                'proactive_distribution': [{'name': name if name else '未知', 'value': count} for name, count in proactive_stats],
                'proactive_trend': proactive_trend
            }
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/detail_list')
async def fault_detail_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    fault_type: Optional[str] = Query(None),
    cause_category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取故障详细列表"""
    try:
        # 构建查询
        query = select(FaultRecord)
        
        # 添加筛选条件
        if fault_type:
            query = query.where(FaultRecord.province_fault_type == fault_type)
        
        if cause_category:
            query = query.where(FaultRecord.cause_category == cause_category)
        
        # 分页与总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar() or 0
        
        paged_query = query.order_by(FaultRecord.fault_date.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page)
        result = await db.execute(paged_query)
        faults = result.scalars().all()
        
        # 格式化数据
        fault_list = []
        for fault in faults:
            fault_list.append({
                'id': fault.id,
                'sequence_no': fault.sequence_no,
                'fault_date': fault.fault_date.strftime('%Y-%m-%d %H:%M:%S') if fault.fault_date else '',
                'fault_name': fault.fault_name,
                'province_fault_type': fault.province_fault_type,
                'cause_category': fault.cause_category,
                'notification_level': fault.notification_level,
                'fault_duration_hours': round(fault.fault_duration_hours, 2) if fault.fault_duration_hours else 0,
                'is_proactive_discovery': fault.is_proactive_discovery,
                'fault_cause': fault.fault_cause,
                'fault_handling': fault.fault_handling
            })
        
        return JSONResponse({
            'success': True,
            'data': {
                'faults': fault_list,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/search')
async def fault_search(
    keyword: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db)
):
    """故障搜索"""
    try:
        # 在多个字段中搜索
        stmt = select(FaultRecord).where(
            or_(
                FaultRecord.fault_name.like(f'%{keyword}%'),
                FaultRecord.fault_cause.like(f'%{keyword}%'),
                FaultRecord.fault_handling.like(f'%{keyword}%'),
                FaultRecord.remarks.like(f'%{keyword}%')
            )
        ).order_by(FaultRecord.fault_date.desc()).limit(50)
        result = await db.execute(stmt)
        faults = result.scalars().all()
        
        # 格式化数据
        fault_list = []
        for fault in faults:
            fault_list.append({
                'id': fault.id,
                'sequence_no': fault.sequence_no,
                'fault_date': fault.fault_date.strftime('%Y-%m-%d %H:%M:%S') if fault.fault_date else '',
                'fault_name': fault.fault_name,
                'province_fault_type': fault.province_fault_type,
                'cause_category': fault.cause_category,
                'notification_level': fault.notification_level,
                'fault_duration_hours': round(fault.fault_duration_hours, 2) if fault.fault_duration_hours else 0,
                'is_proactive_discovery': fault.is_proactive_discovery
            })
        
        return JSONResponse({
            'success': True,
            'data': fault_list
        })
        
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

# ==================== V1 Drill-Down Aggregation API ====================
@router.get('/drill/group')
async def fault_drill_group(
    group_by: str = Query(..., regex='^(notification_level|cause_category)$'),
    notification_level: Optional[str] = Query(None),
    cause_category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Grouped aggregation for drill-down (V1)
    • group_by 可选 'notification_level' 或 'cause_category'
    • 继承现有过滤条件
    返回 buckets 列表：key, count, duration_sum, mttr
    """
    try:
        # 选择分组字段
        column = (
            FaultRecord.notification_level if group_by == 'notification_level' else FaultRecord.cause_category
        )

        # 基础查询
        stmt = select(
            column.label('key'),
            func.count(FaultRecord.id).label('count'),
            func.sum(FaultRecord.fault_duration_hours).label('duration_sum'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration')
        )

        # 过滤条件
        conditions = []
        if notification_level:
            conditions.append(FaultRecord.notification_level == notification_level)
        if cause_category:
            conditions.append(FaultRecord.cause_category == cause_category)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # 分组 & 排序
        stmt = stmt.group_by(column).order_by(func.count(FaultRecord.id).desc())
        result = await db.execute(stmt)

        buckets = [
            {
                'key': key if key else '未知',
                'count': cnt,
                'duration_sum': float(dur_sum) if dur_sum else 0,
                'mttr': round(avg_dur, 2) if avg_dur else 0
            }
            for key, cnt, dur_sum, avg_dur in result.all()
        ]

        return JSONResponse({'success': True, 'data': {'buckets': buckets}})
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

@router.get('/api/drilldown')
async def fault_drilldown(
    month: str = Query(..., description="格式: YYYY-MM"),
    db: AsyncSession = Depends(get_db)
):
    """按月下钻，多维度返回：
    - pareto: 原因分类计数与累计占比
    - boxplot: 各原因分类处理时长箱线图统计 [min, q1, median, q3, max]
    - control: 时序处理时长、均值、UCL/LCL(均值±3σ)
    - heatmap: 周(0-6, 周一为0) x 小时(0-23) 的发生次数
    - group_compare: 通报级别与原因分类的对比聚合
    """
    try:
        # 解析月份边界
        try:
            month_dt = datetime.strptime(month, '%Y-%m')
        except ValueError:
            return JSONResponse({'success': False, 'error': 'month 参数格式应为 YYYY-MM'}, status_code=400)

        start = month_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 计算下个月的1号
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        # 查询本月记录
        stmt = select(FaultRecord).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_date >= start,
                FaultRecord.fault_date < end
            )
        ).order_by(FaultRecord.fault_date.asc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        # 组装基础数据
        durations = []  # (datetime, duration)
        cause_counter = Counter()
        category_durations = defaultdict(list)  # cause -> [durations]
        heatmap_counts = defaultdict(int)  # (weekday, hour) -> count
        level_agg = defaultdict(lambda: {'count': 0, 'sum': 0.0})

        for r in records:
            # 时长
            dur = float(r.fault_duration_hours) if r.fault_duration_hours is not None else None
            if r.fault_date:
                if dur is not None:
                    durations.append((r.fault_date, dur))
            # 原因分类统计
            cause = r.cause_category or '未知'
            cause_counter[cause] += 1
            if dur is not None:
                category_durations[cause].append(dur)
            # 热力图 (周-时)
            if r.fault_date:
                wd = (r.fault_date.weekday())  # 周一=0
                hr = r.fault_date.hour
                heatmap_counts[(wd, hr)] += 1
            # 通报级别聚合
            lvl = r.notification_level or '未知'
            level_agg[lvl]['count'] += 1
            if dur is not None:
                level_agg[lvl]['sum'] += dur

        # Pareto: 排序与累计占比
        total = sum(cause_counter.values()) or 1
        pareto_items = sorted(cause_counter.items(), key=lambda x: x[1], reverse=True)
        cum = 0
        pareto = []
        for name, cnt in pareto_items:
            cum += cnt
            pareto.append({
                'name': name,
                'count': cnt,
                'cum_percent': round(cum / total * 100, 2)
            })

        # Boxplot: 计算五数概括
        def percentile(arr, p):
            if not arr:
                return 0.0
            arr_sorted = sorted(arr)
            k = (len(arr_sorted) - 1) * p
            f = int(k)
            c = min(f + 1, len(arr_sorted) - 1)
            if f == c:
                return arr_sorted[int(k)]
            return arr_sorted[f] + (arr_sorted[c] - arr_sorted[f]) * (k - f)

        boxplot = []
        boxplot_categories = []
        for cat, vals in category_durations.items():
            if not vals:
                continue
            vmin = float(min(vals))
            q1 = float(percentile(vals, 0.25))
            med = float(percentile(vals, 0.5))
            q3 = float(percentile(vals, 0.75))
            vmax = float(max(vals))
            boxplot.append([round(vmin, 2), round(q1, 2), round(med, 2), round(q3, 2), round(vmax, 2)])
            boxplot_categories.append(cat)

        # Control chart: 均值、σ、UCL/LCL
        durations_sorted = [d for _, d in sorted(durations, key=lambda x: x[0])]
        control_series = [round(d, 2) for d in durations_sorted]
        mean = round(sum(durations_sorted) / len(durations_sorted), 2) if durations_sorted else 0.0
        if len(durations_sorted) > 1:
            mu = sum(durations_sorted) / len(durations_sorted)
            variance = sum((x - mu) ** 2 for x in durations_sorted) / (len(durations_sorted) - 1)
            sigma = variance ** 0.5
        else:
            sigma = 0.0
        ucl = round(mean + 3 * sigma, 2)
        lcl = round(max(mean - 3 * sigma, 0.0), 2)

        # Heatmap data
        heatmap = [[h, w, heatmap_counts.get((w, h), 0)] for w in range(7) for h in range(24)]

        # Group compare
        level_keys = sorted(level_agg.keys())
        level_counts = [level_agg[k]['count'] for k in level_keys]
        level_avg = [round((level_agg[k]['sum'] / level_agg[k]['count']), 2) if level_agg[k]['count'] > 0 else 0 for k in level_keys]

        return JSONResponse({
            'success': True,
            'data': {
                'pareto': pareto,
                'boxplot': {
                    'categories': boxplot_categories,
                    'data': boxplot
                },
                'control': {
                    'series': control_series,
                    'mean': mean,
                    'ucl': ucl,
                    'lcl': lcl
                },
                'heatmap': heatmap,
                'group_compare': {
                    'levels': level_keys,
                    'counts': level_counts,
                    'avg_duration': level_avg
                }
            }
        })
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})

# ==================== 故障数据管理路由 ====================

@router.get('/data', response_class=HTMLResponse)
async def fault_data_page(
    request: Request,
    page: int = Query(1, ge=1),
    fault_type: Optional[str] = Query(None),
    cause_category: Optional[str] = Query(None),
    notification_level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """故障数据管理页面"""
    PAGE_SIZE = 10
    
    try:
        # 获取筛选选项
        result = await db.execute(select(distinct(FaultRecord.province_fault_type)).where(
            FaultRecord.province_fault_type.isnot(None),
            FaultRecord.province_fault_type != ''
        ))
        all_fault_types = [item[0] for item in result.all()]
        
        result = await db.execute(select(distinct(FaultRecord.cause_category)).where(
            FaultRecord.cause_category.isnot(None),
            FaultRecord.cause_category != ''
        ))
        all_cause_categories = [item[0] for item in result.all()]
        
        result = await db.execute(select(distinct(FaultRecord.notification_level)).where(
            FaultRecord.notification_level.isnot(None),
            FaultRecord.notification_level != ''
        ))
        all_notification_levels = [item[0] for item in result.all()]
        
        # 构建查询
        query = select(FaultRecord)
        
        if fault_type:
            query = query.where(FaultRecord.province_fault_type == fault_type)
        if cause_category:
            query = query.where(FaultRecord.cause_category == cause_category)
        if notification_level:
            query = query.where(FaultRecord.notification_level == notification_level)
        
        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else 1
        
        # 防止页码越界
        if page < 1:
            page = 1
        if pages > 0 and page > pages:
            page = pages
        elif pages == 0:
            page = 1
        
        # 分页查询
        paged_query = query.order_by(FaultRecord.created_at.desc()).offset(
            (page - 1) * PAGE_SIZE
        ).limit(PAGE_SIZE)
        result = await db.execute(paged_query)
        fault_data_list = result.scalars().all()
        
        return templates.TemplateResponse(
            'fault_data.html',
            {
                'request': request,
                'fault_data_list': fault_data_list,
                'page': page,
                'pages': pages,
                'total': total,
                'all_fault_types': all_fault_types,
                'all_cause_categories': all_cause_categories,
                'all_notification_levels': all_notification_levels,
                'current_fault_type': fault_type,
                'current_cause_category': cause_category,
                'current_notification_level': notification_level
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/add_fault_data', response_class=HTMLResponse)
async def add_fault_data_form(request: Request):
    """添加故障数据表单页面"""
    return templates.TemplateResponse('add_fault_data.html', {'request': request})

@router.post('/add_fault_data')
async def add_fault_data(
    sequence_no: Optional[int] = Form(None),
    fault_date: Optional[str] = Form(None),
    fault_name: Optional[str] = Form(None),
    province_fault_type: Optional[str] = Form(None),
    cause_category: Optional[str] = Form(None),
    notification_level: Optional[str] = Form(None),
    fault_duration_hours: Optional[float] = Form(None),
    is_proactive_discovery: Optional[str] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    complaint_situation: Optional[str] = Form(None),
    fault_cause: Optional[str] = Form(None),
    fault_handling: Optional[str] = Form(None),
    province_cause_category: Optional[str] = Form(None),
    province_cause_analysis: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """添加故障数据"""
    try:
        # 解析日期时间
        parsed_fault_date = None
        if fault_date:
            try:
                parsed_fault_date = datetime.strptime(fault_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    parsed_fault_date = datetime.strptime(fault_date, '%Y-%m-%d')
                except ValueError:
                    pass
        
        parsed_start_time = None
        if start_time:
            try:
                parsed_start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        parsed_end_time = None
        if end_time:
            try:
                parsed_end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        fault_record = FaultRecord(
            sequence_no=sequence_no,
            fault_date=parsed_fault_date,
            fault_name=fault_name,
            province_fault_type=province_fault_type,
            cause_category=cause_category,
            notification_level=notification_level,
            fault_duration_hours=fault_duration_hours,
            is_proactive_discovery=is_proactive_discovery,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            complaint_situation=complaint_situation,
            fault_cause=fault_cause,
            fault_handling=fault_handling,
            province_cause_category=province_cause_category,
            province_cause_analysis=province_cause_analysis,
            remarks=remarks
        )
        
        db.add(fault_record)
        await db.commit()
        
        return RedirectResponse(url='/fault/data', status_code=303)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/edit_fault_data/{fault_id}', response_class=HTMLResponse)
async def edit_fault_data_form(request: Request, fault_id: int, db: AsyncSession = Depends(get_db)):
    """编辑故障数据表单页面"""
    result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
    fault_record = result.scalar_one_or_none()
    if not fault_record:
        raise HTTPException(status_code=404, detail="故障记录不存在")
    
    return templates.TemplateResponse(
        'edit_fault_data.html',
        {'request': request, 'fault_record': fault_record}
    )

@router.post('/edit_fault_data/{fault_id}')
async def edit_fault_data(
    fault_id: int,
    sequence_no: Optional[int] = Form(None),
    fault_date: Optional[str] = Form(None),
    fault_name: Optional[str] = Form(None),
    province_fault_type: Optional[str] = Form(None),
    cause_category: Optional[str] = Form(None),
    notification_level: Optional[str] = Form(None),
    fault_duration_hours: Optional[float] = Form(None),
    is_proactive_discovery: Optional[str] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    complaint_situation: Optional[str] = Form(None),
    fault_cause: Optional[str] = Form(None),
    fault_handling: Optional[str] = Form(None),
    province_cause_category: Optional[str] = Form(None),
    province_cause_analysis: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """更新故障数据"""
    try:
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        # 解析日期时间
        if fault_date:
            try:
                fault_record.fault_date = datetime.strptime(fault_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    fault_record.fault_date = datetime.strptime(fault_date, '%Y-%m-%d')
                except ValueError:
                    pass
        
        if start_time:
            try:
                fault_record.start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        if end_time:
            try:
                fault_record.end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        # 更新其他字段
        fault_record.sequence_no = sequence_no
        fault_record.fault_name = fault_name
        fault_record.province_fault_type = province_fault_type
        fault_record.cause_category = cause_category
        fault_record.notification_level = notification_level
        fault_record.fault_duration_hours = fault_duration_hours
        fault_record.is_proactive_discovery = is_proactive_discovery
        fault_record.complaint_situation = complaint_situation
        fault_record.fault_cause = fault_cause
        fault_record.fault_handling = fault_handling
        fault_record.province_cause_category = province_cause_category
        fault_record.province_cause_analysis = province_cause_analysis
        fault_record.remarks = remarks
        fault_record.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return RedirectResponse(url='/fault/data', status_code=303)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/delete_fault_data/{fault_id}')
async def delete_fault_data(fault_id: int, db: AsyncSession = Depends(get_db)):
    """删除故障数据"""
    try:
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        await db.delete(fault_record)
        await db.commit()
        
        return RedirectResponse(url='/fault/data', status_code=303)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/api/detail/{fault_id}')
async def get_fault_detail(fault_id: int, db: AsyncSession = Depends(get_db)):
    try:
        # 获取故障记录
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        if not fault_record:
            return JSONResponse({
                'success': False,
                'message': '故障记录不存在'
            }, status_code=404)
        
        # 格式化故障记录数据
        fault_data = {
            'id': fault_record.id,
            'fault_occurrence_time': fault_record.fault_occurrence_time.strftime('%Y-%m-%d %H:%M:%S') if fault_record.fault_occurrence_time else None,
            'fault_recovery_time': fault_record.fault_recovery_time.strftime('%Y-%m-%d %H:%M:%S') if fault_record.fault_recovery_time else None,
            'fault_duration_hours': round(fault_record.fault_duration_hours, 2) if fault_record.fault_duration_hours else 0,
            'fault_type': fault_record.fault_type,
            'province_fault_type': fault_record.province_fault_type,
            'cause_category': fault_record.cause_category,
            'notification_level': fault_record.notification_level,
            'is_proactive_discovery': fault_record.is_proactive_discovery,
            'fault_description': fault_record.fault_description,
            'handling_measures': fault_record.handling_measures,
            'remarks': fault_record.remarks
        }
        
        return JSONResponse({
            'success': True,
            'data': fault_data
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'message': str(e)
        }, status_code=500)

@router.get('/view_fault_data/{fault_id}', response_class=HTMLResponse)
async def view_fault_data(request: Request, fault_id: int, db: AsyncSession = Depends(get_db)):
    # 获取故障记录
    result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
    fault_record = result.scalar_one_or_none()
    if not fault_record:
        raise HTTPException(status_code=404, detail="故障记录不存在")
    
    return templates.TemplateResponse(
        'view_fault_data.html',
        {'request': request, 'fault_record': fault_record}
    )

# ==================== 故障预测分析模块 ====================

class FaultPredictionResponse(BaseModel):
    """故障预测响应模型"""
    prediction_date: str
    predicted_fault_count: int
    probability_score: float
    risk_level: str
    confidence: float
    contributing_factors: List[Dict[str, Any]]

class MTTRPredictionResponse(BaseModel):
    """MTTR预测响应模型"""
    fault_type: str
    predicted_mttr_hours: float
    confidence_interval: Dict[str, float]  # {"lower": xx, "upper": xx}
    historical_avg: float
    improvement_suggestions: List[str]

class AnomalyDetectionResponse(BaseModel):
    """异常检测响应模型"""
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    anomaly_type: str  # 'count', 'duration', 'pattern'
    analysis_period: str
    detected_patterns: List[Dict[str, Any]]

@router.get('/api/prediction/fault_forecast', response_model=Dict[str, Any])
async def fault_forecast_prediction(
    forecast_days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    故障预测API - 基于历史数据预测未来故障发生情况
    """
    try:
        # 获取历史故障数据（过去6个月）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        stmt = select(
            extract('year', FaultRecord.fault_date).label('year'),
            extract('month', FaultRecord.fault_date).label('month'),
            extract('day', FaultRecord.fault_date).label('day'),
            func.count(FaultRecord.id).label('fault_count'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date
            )
        ).group_by(
            extract('year', FaultRecord.fault_date),
            extract('month', FaultRecord.fault_date),
            extract('day', FaultRecord.fault_date)
        ).order_by('year', 'month', 'day')
        
        result = await db.execute(stmt)
        daily_stats = result.all()
        
        # 数据预处理
        if not daily_stats:
            return JSONResponse({
                'success': False,
                'message': '历史数据不足，无法进行预测'
            })
        
        # 转换为pandas DataFrame进行时序分析
        data = []
        for year, month, day, count, avg_dur in daily_stats:
            try:
                date_obj = datetime(int(year), int(month), int(day))
                data.append({
                    'date': date_obj,
                    'fault_count': int(count) if count else 0,
                    'avg_duration': float(avg_dur) if avg_dur else 0.0
                })
            except ValueError:
                continue
        
        df = pd.DataFrame(data)
        if df.empty:
            return JSONResponse({
                'success': False,
                'message': '数据处理失败'
            })
        
        df.set_index('date', inplace=True)
        
        # 简单的移动平均预测（可后续升级为更复杂的机器学习模型）
        window_size = min(7, len(df))
        if window_size < 3:
            return JSONResponse({
                'success': False,
                'message': '数据点不足，无法进行可靠预测'
            })
        
        # 计算移动平均和趋势
        ma_fault_count = df['fault_count'].rolling(window=window_size).mean()
        ma_duration = df['avg_duration'].rolling(window=window_size).mean()
        
        # 计算预测结果
        recent_avg_count = ma_fault_count.dropna().tail(3).mean()
        recent_avg_duration = ma_duration.dropna().tail(3).mean()
        
        # 季节性调整（简化版）
        current_month = datetime.now().month
        monthly_multiplier = _get_seasonal_multiplier(current_month)
        
        predicted_daily_count = recent_avg_count * monthly_multiplier
        predicted_total_count = int(predicted_daily_count * forecast_days)
        
        # 计算置信度和风险等级
        variance = df['fault_count'].var()
        confidence = max(0.6, min(0.95, 1 - (variance / (recent_avg_count + 1))))
        
        risk_level = _calculate_risk_level(predicted_daily_count, df['fault_count'].quantile(0.8))
        
        # 分析贡献因素
        contributing_factors = await _analyze_contributing_factors(db, start_date, end_date)
        
        return JSONResponse({
            'success': True,
            'data': {
                'prediction_period_days': forecast_days,
                'predicted_total_faults': predicted_total_count,
                'predicted_daily_average': round(predicted_daily_count, 2),
                'confidence': round(confidence, 3),
                'risk_level': risk_level,
                'historical_daily_average': round(df['fault_count'].mean(), 2),
                'trend_analysis': {
                    'recent_trend': 'increasing' if ma_fault_count.tail(3).diff().mean() > 0 else 'decreasing',
                    'volatility': 'high' if variance > recent_avg_count else 'normal'
                },
                'contributing_factors': contributing_factors,
                'recommendations': _generate_prediction_recommendations(predicted_daily_count, risk_level)
            }
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': f'预测分析失败: {str(e)}'
        })

@router.get('/api/prediction/mttr_forecast', response_model=Dict[str, Any])
async def mttr_prediction(
    fault_type: Optional[str] = Query(None),
    cause_category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    MTTR预测API - 预测特定类型故障的平均修复时间
    """
    try:
        # 构建查询条件
        conditions = [FaultRecord.fault_duration_hours.isnot(None)]
        
        if fault_type:
            conditions.append(FaultRecord.province_fault_type == fault_type)
        if cause_category:
            conditions.append(FaultRecord.cause_category == cause_category)
        
        # 获取历史MTTR数据
        stmt = select(
            FaultRecord.fault_duration_hours,
            FaultRecord.province_fault_type,
            FaultRecord.cause_category,
            FaultRecord.notification_level,
            FaultRecord.is_proactive_discovery
        ).where(and_(*conditions)).order_by(FaultRecord.fault_date.desc()).limit(1000)
        
        result = await db.execute(stmt)
        records = result.all()
        
        if not records:
            return JSONResponse({
                'success': False,
                'message': '未找到匹配的历史数据'
            })
        
        # 数据分析
        durations = [float(r[0]) for r in records if r[0] is not None]
        if len(durations) < 3:
            return JSONResponse({
                'success': False,
                'message': '数据量不足以进行可靠预测'
            })
        
        # 统计分析
        mean_duration = np.mean(durations)
        std_duration = np.std(durations)
        median_duration = np.median(durations)
        
        # 置信区间计算（95%）
        confidence_interval = {
            'lower': max(0, mean_duration - 1.96 * std_duration / np.sqrt(len(durations))),
            'upper': mean_duration + 1.96 * std_duration / np.sqrt(len(durations))
        }
        
        # 按不同因素分析
        proactive_vs_reactive = defaultdict(list)
        level_analysis = defaultdict(list)
        
        for record in records:
            duration, f_type, cause, level, proactive = record
            if duration:
                if proactive:
                    proactive_vs_reactive[proactive].append(duration)
                if level:
                    level_analysis[level].append(duration)
        
        # 生成改进建议
        suggestions = _generate_mttr_suggestions(
            mean_duration, median_duration, proactive_vs_reactive, level_analysis
        )
        
        return JSONResponse({
            'success': True,
            'data': {
                'fault_type': fault_type or '全部类型',
                'cause_category': cause_category or '全部原因',
                'predicted_mttr_hours': round(mean_duration, 2),
                'median_mttr_hours': round(median_duration, 2),
                'confidence_interval': {
                    'lower': round(confidence_interval['lower'], 2),
                    'upper': round(confidence_interval['upper'], 2)
                },
                'historical_samples': len(durations),
                'statistics': {
                    'min': round(min(durations), 2),
                    'max': round(max(durations), 2),
                    'std_dev': round(std_duration, 2),
                    'percentiles': {
                        'p25': round(np.percentile(durations, 25), 2),
                        'p75': round(np.percentile(durations, 75), 2),
                        'p90': round(np.percentile(durations, 90), 2)
                    }
                },
                'improvement_suggestions': suggestions,
                'benchmark_analysis': _benchmark_mttr_analysis(mean_duration, durations)
            }
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': f'MTTR预测失败: {str(e)}'
        })

@router.get('/api/prediction/anomaly_detection', response_model=Dict[str, Any])
async def anomaly_detection(
    analysis_days: int = Query(30, ge=7, le=90),
    anomaly_threshold: float = Query(2.0, ge=1.0, le=5.0),
    db: AsyncSession = Depends(get_db)
):
    """
    异常检测API - 检测故障模式中的异常情况
    """
    try:
        # 获取分析期间的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=analysis_days)
        
        # 按天统计故障数量和平均处理时长
        stmt = select(
            func.date(FaultRecord.fault_date).label('fault_date'),
            func.count(FaultRecord.id).label('daily_count'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration'),
            func.count(case((FaultRecord.is_proactive_discovery == '是', 1))).label('proactive_count')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date
            )
        ).group_by(func.date(FaultRecord.fault_date)).order_by('fault_date')
        
        result = await db.execute(stmt)
        daily_data = result.all()
        
        if len(daily_data) < 7:
            return JSONResponse({
                'success': False,
                'message': '数据不足，无法进行异常检测'
            })
        
        # 数据处理
        counts = [int(r[1]) for r in daily_data]
        durations = [float(r[2]) if r[2] else 0 for r in daily_data]
        proactive_counts = [int(r[3]) for r in daily_data]
        dates = [r[0].strftime('%Y-%m-%d') for r in daily_data]
        
        # 异常检测算法 (基于Z-score)
        def detect_anomalies(data, threshold=anomaly_threshold):
            data_array = np.array(data)
            mean_val = np.mean(data_array)
            std_val = np.std(data_array)
            
            if std_val == 0:
                return [], []
            
            z_scores = np.abs((data_array - mean_val) / std_val)
            anomaly_indices = np.where(z_scores > threshold)[0]
            anomaly_scores = z_scores[anomaly_indices]
            
            return anomaly_indices.tolist(), anomaly_scores.tolist()
        
        # 检测不同类型的异常
        count_anomalies, count_scores = detect_anomalies(counts)
        duration_anomalies, duration_scores = detect_anomalies(durations)
        
        # 构建异常报告
        detected_anomalies = []
        
        for i, score in zip(count_anomalies, count_scores):
            detected_anomalies.append({
                'date': dates[i],
                'type': 'fault_count',
                'value': counts[i],
                'anomaly_score': round(score, 2),
                'description': f'故障数量异常：{counts[i]}件（日均{np.mean(counts):.1f}件）'
            })
        
        for i, score in zip(duration_anomalies, duration_scores):
            if durations[i] > 0:  # 排除无效数据
                detected_anomalies.append({
                    'date': dates[i],
                    'type': 'duration',
                    'value': round(durations[i], 2),
                    'anomaly_score': round(score, 2),
                    'description': f'处理时长异常：{durations[i]:.1f}小时（平均{np.mean([d for d in durations if d > 0]):.1f}小时）'
                })
        
        # 模式分析
        pattern_analysis = _analyze_fault_patterns(daily_data, analysis_days)
        
        # 综合异常评分
        overall_anomaly_score = np.mean([
            np.mean(count_scores) if count_scores else 0,
            np.mean(duration_scores) if duration_scores else 0
        ])
        
        is_anomaly = len(detected_anomalies) > 0 or overall_anomaly_score > anomaly_threshold
        
        return JSONResponse({
            'success': True,
            'data': {
                'analysis_period': f'{start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")}',
                'is_anomaly_detected': is_anomaly,
                'overall_anomaly_score': round(overall_anomaly_score, 3),
                'detection_threshold': anomaly_threshold,
                'detected_anomalies': detected_anomalies,
                'pattern_analysis': pattern_analysis,
                'summary_statistics': {
                    'avg_daily_faults': round(np.mean(counts), 2),
                    'avg_duration_hours': round(np.mean([d for d in durations if d > 0]), 2) if any(d > 0 for d in durations) else 0,
                    'proactive_discovery_rate': round(sum(proactive_counts) / sum(counts) * 100, 1) if sum(counts) > 0 else 0,
                    'total_analysis_days': len(daily_data)
                },
                'recommendations': _generate_anomaly_recommendations(detected_anomalies, pattern_analysis)
            }
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': f'异常检测失败: {str(e)}'
        })

# ==================== 辅助函数 ====================

def _get_seasonal_multiplier(month: int) -> float:
    """获取季节性调整系数"""
    # 简化的季节性模式（可基于历史数据进行优化）
    seasonal_factors = {
        1: 1.1,   # 一月：节假日后设备老化
        2: 0.9,   # 二月：相对平稳
        3: 1.0,   # 三月：正常
        4: 0.95,  # 四月：春季维护后
        5: 1.0,   # 五月：正常
        6: 1.15,  # 六月：夏季高峰前
        7: 1.2,   # 七月：高温影响
        8: 1.2,   # 八月：高温持续
        9: 1.1,   # 九月：设备负荷高
        10: 0.95, # 十月：秋季维护
        11: 1.0,  # 十一月：正常
        12: 1.05  # 十二月：年终压力
    }
    return seasonal_factors.get(month, 1.0)

def _calculate_risk_level(predicted_count: float, historical_threshold: float) -> str:
    """计算风险等级"""
    if predicted_count > historical_threshold * 1.5:
        return 'high'
    elif predicted_count > historical_threshold * 1.2:
        return 'medium'
    else:
        return 'low'

async def _analyze_contributing_factors(db: AsyncSession, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """分析故障贡献因素"""
    try:
        # 按原因分类统计
        stmt = select(
            FaultRecord.cause_category,
            func.count(FaultRecord.id).label('count'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration')
        ).where(
            and_(
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date,
                FaultRecord.cause_category.isnot(None)
            )
        ).group_by(FaultRecord.cause_category).order_by(func.count(FaultRecord.id).desc())
        
        result = await db.execute(stmt)
        factors = []
        
        for category, count, avg_dur in result.all():
            factors.append({
                'factor': category,
                'impact_score': int(count),
                'avg_duration_hours': round(float(avg_dur), 2) if avg_dur else 0,
                'risk_contribution': 'high' if count > 10 else 'medium' if count > 5 else 'low'
            })
        
        return factors[:5]  # 返回前5个主要因素
    except:
        return []

def _generate_prediction_recommendations(predicted_count: float, risk_level: str) -> List[str]:
    """生成预测建议"""
    recommendations = []
    
    if risk_level == 'high':
        recommendations.extend([
            '建议增加预防性维护频次',
            '准备充足的应急响应资源',
            '加强关键设备监控',
            '考虑提前调配技术人员'
        ])
    elif risk_level == 'medium':
        recommendations.extend([
            '保持正常维护计划',
            '关注设备运行状态',
            '确保备件库存充足'
        ])
    else:
        recommendations.extend([
            '继续保持当前维护策略',
            '可考虑优化资源配置'
        ])
    
    return recommendations

def _generate_mttr_suggestions(mean_duration: float, median_duration: float, 
                              proactive_analysis: dict, level_analysis: dict) -> List[str]:
    """生成MTTR改进建议"""
    suggestions = []
    
    # 基于平均时长的建议
    if mean_duration > 24:
        suggestions.append('平均处理时间较长，建议优化故障响应流程')
    elif mean_duration > 12:
        suggestions.append('可考虑加强故障诊断培训，提高处理效率')
    
    # 基于主动发现分析的建议
    if '是' in proactive_analysis and '否' in proactive_analysis:
        proactive_avg = np.mean(proactive_analysis['是'])
        reactive_avg = np.mean(proactive_analysis['否'])
        if reactive_avg > proactive_avg * 1.5:
            suggestions.append('提高主动发现能力可显著减少故障处理时间')
    
    # 基于级别分析的建议
    if level_analysis:
        max_level = max(level_analysis.keys(), key=lambda x: np.mean(level_analysis[x]))
        suggestions.append(f'"{max_level}"级故障处理时间最长，需重点关注')
    
    return suggestions

def _benchmark_mttr_analysis(current_mttr: float, all_durations: List[float]) -> Dict[str, Any]:
    """MTTR基准分析"""
    percentile_90 = np.percentile(all_durations, 90)
    percentile_75 = np.percentile(all_durations, 75)
    percentile_50 = np.percentile(all_durations, 50)
    
    if current_mttr <= percentile_50:
        performance_level = 'excellent'
    elif current_mttr <= percentile_75:
        performance_level = 'good'
    elif current_mttr <= percentile_90:
        performance_level = 'average'
    else:
        performance_level = 'needs_improvement'
    
    return {
        'performance_level': performance_level,
        'percentile_position': round(sum(1 for d in all_durations if d <= current_mttr) / len(all_durations) * 100, 1),
        'improvement_potential': round(max(0, current_mttr - percentile_50), 2)
    }

def _analyze_fault_patterns(daily_data: List, analysis_days: int) -> Dict[str, Any]:
    """分析故障模式"""
    if len(daily_data) < 7:
        return {'pattern_detected': False, 'message': '数据不足'}
    
    counts = [int(r[1]) for r in daily_data]
    
    # 简单的趋势分析
    first_half = counts[:len(counts)//2]
    second_half = counts[len(counts)//2:]
    
    trend = 'increasing' if np.mean(second_half) > np.mean(first_half) else 'decreasing'
    
    # 周期性检测（简化版）
    weekly_pattern = len(counts) >= 14
    if weekly_pattern:
        week1_avg = np.mean(counts[:7])
        week2_avg = np.mean(counts[7:14]) if len(counts) >= 14 else np.mean(counts[7:])
        weekly_stability = abs(week1_avg - week2_avg) < np.std(counts)
    else:
        weekly_stability = False
    
    return {
        'pattern_detected': True,
        'trend': trend,
        'weekly_stability': weekly_stability,
        'volatility': 'high' if np.std(counts) > np.mean(counts) else 'normal',
        'peak_detection': {
            'max_day': daily_data[np.argmax(counts)][0].strftime('%Y-%m-%d'),
            'max_count': max(counts),
            'min_day': daily_data[np.argmin(counts)][0].strftime('%Y-%m-%d'),
            'min_count': min(counts)
        }
    }

def _generate_anomaly_recommendations(anomalies: List[Dict], pattern_analysis: Dict) -> List[str]:
    """生成异常处理建议"""
    recommendations = []
    
    if not anomalies:
        recommendations.append('当前无异常检测到，继续保持现有运维策略')
        return recommendations

# ==================== 增强时序分析模块 ====================

@router.get('/api/analysis/time_series', response_model=Dict[str, Any])
async def advanced_time_series_analysis(
    analysis_period: int = Query(180, ge=30, le=365),
    granularity: str = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    高级时序分析API - 支持多种粒度的时序分析
    """
    try:
        # 根据分析周期确定起始时间
        end_date = datetime.now()
        start_date = end_date - timedelta(days=analysis_period)
        
        # 根据粒度选择时间分组方式
        if granularity == "hourly":
            time_format = func.date_format(FaultRecord.fault_date, '%Y-%m-%d %H:00:00')
            group_by_clause = func.date_format(FaultRecord.fault_date, '%Y-%m-%d %H')
        elif granularity == "daily":
            time_format = func.date(FaultRecord.fault_date)
            group_by_clause = func.date(FaultRecord.fault_date)
        elif granularity == "weekly":
            time_format = func.date_format(FaultRecord.fault_date, '%Y-%u')
            group_by_clause = func.date_format(FaultRecord.fault_date, '%Y-%u')
        else:  # monthly
            time_format = func.date_format(FaultRecord.fault_date, '%Y-%m')
            group_by_clause = func.date_format(FaultRecord.fault_date, '%Y-%m')
        
        # 查询时序数据
        stmt = select(
            time_format.label('time_period'),
            func.count(FaultRecord.id).label('fault_count'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration'),
            func.count(case((FaultRecord.is_proactive_discovery == '是', 1))).label('proactive_count'),
            func.count(distinct(FaultRecord.cause_category)).label('unique_causes')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date
            )
        ).group_by(group_by_clause).order_by(time_format)
        
        result = await db.execute(stmt)
        time_series_data = result.all()
        
        if len(time_series_data) < 3:
            return JSONResponse({
                'success': False,
                'message': f'数据点不足，无法进行{granularity}级时序分析'
            })
        
        # 数据处理和分析
        periods = []
        counts = []
        durations = []
        proactive_rates = []
        
        for period, count, avg_dur, proactive_cnt, unique_causes in time_series_data:
            periods.append(str(period))
            counts.append(int(count))
            durations.append(float(avg_dur) if avg_dur else 0)
            proactive_rate = (proactive_cnt / count * 100) if count > 0 else 0
            proactive_rates.append(round(proactive_rate, 2))
        
        # 时序分析计算
        analysis_results = _perform_time_series_analysis(counts, durations, proactive_rates)
        
        # 季节性分析
        seasonality_analysis = _analyze_seasonality(periods, counts, granularity)
        
        # 趋势分析
        trend_analysis = _analyze_trends(periods, counts, durations)
        
        return JSONResponse({
            'success': True,
            'data': {
                'time_series': {
                    'periods': periods,
                    'fault_counts': counts,
                    'avg_durations': durations,
                    'proactive_rates': proactive_rates
                },
                'analysis_results': analysis_results,
                'seasonality_analysis': seasonality_analysis,
                'trend_analysis': trend_analysis,
                'summary': {
                    'total_periods': len(periods),
                    'analysis_period_days': analysis_period,
                    'granularity': granularity,
                    'avg_faults_per_period': round(np.mean(counts), 2),
                    'volatility_coefficient': round(np.std(counts) / np.mean(counts), 3) if np.mean(counts) > 0 else 0
                }
            }
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': f'时序分析失败: {str(e)}'
        })

@router.get('/api/analysis/pattern_recognition', response_model=Dict[str, Any])
async def pattern_recognition_analysis(
    pattern_type: str = Query("all", regex="^(all|cyclical|seasonal|anomaly|correlation)$"),
    min_pattern_length: int = Query(3, ge=2, le=10),
    db: AsyncSession = Depends(get_db)
):
    """
    模式识别分析API - 识别故障数据中的各种模式
    """
    try:
        # 获取过去一年的数据用于模式识别
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # 按日统计数据
        stmt = select(
            func.date(FaultRecord.fault_date).label('date'),
            func.count(FaultRecord.id).label('count'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration'),
            extract('dow', FaultRecord.fault_date).label('day_of_week'),
            extract('hour', FaultRecord.fault_date).label('hour'),
            extract('month', FaultRecord.fault_date).label('month')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date
            )
        ).group_by(func.date(FaultRecord.fault_date)).order_by('date')
        
        result = await db.execute(stmt)
        daily_data = result.all()
        
        if len(daily_data) < min_pattern_length * 7:  # 至少需要几周的数据
            return JSONResponse({
                'success': False,
                'message': '数据不足，无法进行模式识别分析'
            })
        
        patterns = {}
        
        # 根据请求的模式类型执行相应分析
        if pattern_type in ['all', 'cyclical']:
            patterns['cyclical_patterns'] = _detect_cyclical_patterns(daily_data, min_pattern_length)
        
        if pattern_type in ['all', 'seasonal']:
            patterns['seasonal_patterns'] = _detect_seasonal_patterns(daily_data)
        
        if pattern_type in ['all', 'anomaly']:
            patterns['anomaly_patterns'] = _detect_pattern_anomalies(daily_data)
        
        if pattern_type in ['all', 'correlation']:
            patterns['correlation_patterns'] = _detect_correlation_patterns(daily_data)
        
        return JSONResponse({
            'success': True,
            'data': {
                'pattern_type': pattern_type,
                'analysis_period': f'{start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")}',
                'data_points': len(daily_data),
                'detected_patterns': patterns,
                'pattern_summary': _summarize_patterns(patterns)
            }
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': f'模式识别分析失败: {str(e)}'
        })

@router.get('/api/analysis/forecasting', response_model=Dict[str, Any])
async def advanced_forecasting_analysis(
    forecast_periods: int = Query(30, ge=7, le=90),
    model_type: str = Query("auto", regex="^(auto|linear|exponential|arima)$"),
    confidence_level: float = Query(0.95, ge=0.8, le=0.99),
    db: AsyncSession = Depends(get_db)
):
    """
    高级预测分析API - 支持多种预测模型
    """
    try:
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 使用一年的历史数据
        
        stmt = select(
            func.date(FaultRecord.fault_date).label('date'),
            func.count(FaultRecord.id).label('count'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration')
        ).where(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date
            )
        ).group_by(func.date(FaultRecord.fault_date)).order_by('date')
        
        result = await db.execute(stmt)
        historical_data = result.all()
        
        if len(historical_data) < 30:
            return JSONResponse({
                'success': False,
                'message': '历史数据不足，无法进行高级预测分析'
            })
        
        # 数据预处理
        dates = [row[0] for row in historical_data]
        counts = [row[1] for row in historical_data]
        durations = [float(row[2]) if row[2] else 0 for row in historical_data]
        
        # 选择或自动确定最佳预测模型
        if model_type == "auto":
            model_type = _select_best_model(counts)
        
        # 执行预测
        forecast_results = _perform_forecasting(
            dates, counts, durations, forecast_periods, model_type, confidence_level
        )
        
        # 模型评估
        model_evaluation = _evaluate_model_performance(counts, model_type)
        
        return JSONResponse({
            'success': True,
            'data': {
                'forecast_periods': forecast_periods,
                'model_type': model_type,
                'confidence_level': confidence_level,
                'historical_data_points': len(historical_data),
                'forecast_results': forecast_results,
                'model_evaluation': model_evaluation,
                'forecast_summary': {
                    'avg_predicted_faults': round(np.mean(forecast_results['predicted_counts']), 2),
                    'trend_direction': forecast_results['trend_direction'],
                    'prediction_stability': forecast_results['prediction_stability']
                }
            }
        })
        
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': f'高级预测分析失败: {str(e)}'
        })

# ==================== 高级分析辅助函数 ====================

def _perform_time_series_analysis(counts, durations, proactive_rates):
    """执行时序数据分析"""
    results = {}
    
    # 基础统计
    results['statistics'] = {
        'mean_count': round(np.mean(counts), 2),
        'std_count': round(np.std(counts), 2),
        'mean_duration': round(np.mean(durations), 2),
        'std_duration': round(np.std(durations), 2),
        'mean_proactive_rate': round(np.mean(proactive_rates), 2)
    }
    
    # 变化率分析
    count_changes = np.diff(counts)
    results['volatility'] = {
        'count_volatility': round(np.std(count_changes), 2),
        'max_increase': int(np.max(count_changes)) if len(count_changes) > 0 else 0,
        'max_decrease': int(np.min(count_changes)) if len(count_changes) > 0 else 0,
        'stability_score': round(1 - (np.std(counts) / (np.mean(counts) + 1)), 3)
    }
    
    # 自相关分析（简化版）
    if len(counts) > 5:
        lag1_corr = np.corrcoef(counts[:-1], counts[1:])[0, 1]
        results['autocorrelation'] = {
            'lag1_correlation': round(lag1_corr, 3) if not np.isnan(lag1_corr) else 0,
            'has_momentum': abs(lag1_corr) > 0.3 if not np.isnan(lag1_corr) else False
        }
    
    return results

def _analyze_seasonality(periods, counts, granularity):
    """分析季节性模式"""
    if granularity not in ['daily', 'weekly', 'monthly']:
        return {'seasonal_detected': False, 'message': f'{granularity}粒度不支持季节性分析'}
    
    try:
        if granularity == 'daily' and len(counts) >= 14:
            # 周度季节性检测
            weekly_avg = []
            for i in range(7):
                week_data = [counts[j] for j in range(i, len(counts), 7)]
                weekly_avg.append(np.mean(week_data) if week_data else 0)
            
            week_variation = np.std(weekly_avg) / np.mean(weekly_avg) if np.mean(weekly_avg) > 0 else 0
            
            return {
                'seasonal_detected': week_variation > 0.2,
                'seasonal_type': 'weekly',
                'variation_coefficient': round(week_variation, 3),
                'weekly_pattern': [round(avg, 2) for avg in weekly_avg],
                'peak_days': [i for i, avg in enumerate(weekly_avg) if avg == max(weekly_avg)]
            }
        
        elif granularity == 'monthly' and len(counts) >= 12:
            # 月度季节性检测
            month_variation = np.std(counts) / np.mean(counts) if np.mean(counts) > 0 else 0
            
            return {
                'seasonal_detected': month_variation > 0.3,
                'seasonal_type': 'monthly',
                'variation_coefficient': round(month_variation, 3),
                'peak_months': [periods[i] for i, count in enumerate(counts) if count == max(counts)]
            }
    
    except Exception:
        pass
    
    return {'seasonal_detected': False, 'message': '无法检测到明显的季节性模式'}

def _analyze_trends(periods, counts, durations):
    """分析趋势"""
    try:
        # 线性趋势分析
        x = np.arange(len(counts))
        count_slope = np.polyfit(x, counts, 1)[0]
        duration_slope = np.polyfit(x, durations, 1)[0]
        
        # 趋势强度
        count_trend_strength = abs(count_slope) / (np.std(counts) + 0.01)
        duration_trend_strength = abs(duration_slope) / (np.std(durations) + 0.01)
        
        return {
            'count_trend': {
                'direction': 'increasing' if count_slope > 0.01 else 'decreasing' if count_slope < -0.01 else 'stable',
                'slope': round(count_slope, 3),
                'strength': round(count_trend_strength, 3)
            },
            'duration_trend': {
                'direction': 'increasing' if duration_slope > 0.01 else 'decreasing' if duration_slope < -0.01 else 'stable',
                'slope': round(duration_slope, 3),
                'strength': round(duration_trend_strength, 3)
            },
            'trend_consistency': _calculate_trend_consistency(counts)
        }
    except Exception:
        return {'trend_analysis_failed': True}

def _calculate_trend_consistency(data):
    """计算趋势一致性"""
    if len(data) < 5:
        return 0.5
    
    # 计算移动平均趋势
    window = min(5, len(data) // 3)
    moving_avg = np.convolve(data, np.ones(window)/window, mode='valid')
    
    # 计算趋势方向的一致性
    directions = np.diff(moving_avg) > 0
    consistency = np.sum(directions == directions[0]) / len(directions) if len(directions) > 0 else 0.5
    
    return round(consistency, 3)

def _detect_cyclical_patterns(daily_data, min_length):
    """检测周期性模式"""
    counts = [row[1] for row in daily_data]
    
    if len(counts) < min_length * 4:
        return {'detected': False, 'reason': '数据不足'}
    
    # 简单的周期检测：寻找重复模式
    potential_cycles = []
    
    for cycle_length in range(min_length, min(30, len(counts) // 4)):
        correlation_sum = 0
        comparisons = 0
        
        for start in range(len(counts) - cycle_length * 2):
            pattern1 = counts[start:start + cycle_length]
            pattern2 = counts[start + cycle_length:start + cycle_length * 2]
            
            if len(pattern1) == len(pattern2) == cycle_length:
                try:
                    corr = np.corrcoef(pattern1, pattern2)[0, 1]
                    if not np.isnan(corr):
                        correlation_sum += corr
                        comparisons += 1
                except:
                    continue
        
        if comparisons > 0:
            avg_correlation = correlation_sum / comparisons
            if avg_correlation > 0.6:  # 强相关性阈值
                potential_cycles.append({
                    'cycle_length': cycle_length,
                    'correlation': round(avg_correlation, 3),
                    'frequency': f'每{cycle_length}天重复'
                })
    
    return {
        'detected': len(potential_cycles) > 0,
        'cycles': sorted(potential_cycles, key=lambda x: x['correlation'], reverse=True)[:3]
    }

def _detect_seasonal_patterns(daily_data):
    """检测季节性模式"""
    if len(daily_data) < 90:
        return {'detected': False, 'reason': '数据不足以检测季节性'}
    
    # 按星期几分组
    weekday_patterns = defaultdict(list)
    month_patterns = defaultdict(list)
    
    for date, count, avg_duration, dow, hour, month in daily_data:
        weekday_patterns[int(dow)].append(count)
        month_patterns[int(month)].append(count)
    
    # 分析星期模式
    weekday_avgs = []
    for day in range(7):
        if day in weekday_patterns and weekday_patterns[day]:
            weekday_avgs.append(np.mean(weekday_patterns[day]))
        else:
            weekday_avgs.append(0)
    
    weekday_variation = np.std(weekday_avgs) / np.mean(weekday_avgs) if np.mean(weekday_avgs) > 0 else 0
    
    # 分析月份模式
    month_avgs = []
    for month in range(1, 13):
        if month in month_patterns and month_patterns[month]:
            month_avgs.append(np.mean(month_patterns[month]))
        else:
            month_avgs.append(0)
    
    month_variation = np.std(month_avgs) / np.mean(month_avgs) if np.mean(month_avgs) > 0 else 0
    
    return {
        'detected': weekday_variation > 0.2 or month_variation > 0.3,
        'weekday_pattern': {
            'variation_coefficient': round(weekday_variation, 3),
            'peak_weekday': int(np.argmax(weekday_avgs)),
            'pattern_strength': 'strong' if weekday_variation > 0.4 else 'moderate' if weekday_variation > 0.2 else 'weak'
        },
        'monthly_pattern': {
            'variation_coefficient': round(month_variation, 3),
            'peak_month': int(np.argmax(month_avgs)) + 1,
            'pattern_strength': 'strong' if month_variation > 0.5 else 'moderate' if month_variation > 0.3 else 'weak'
        }
    }

def _detect_pattern_anomalies(daily_data):
    """检测模式异常"""
    counts = [row[1] for row in daily_data]
    durations = [float(row[2]) if row[2] else 0 for row in daily_data]
    
    # Z-score异常检测
    count_mean = np.mean(counts)
    count_std = np.std(counts)
    
    anomalies = []
    for i, (date, count, avg_dur, dow, hour, month) in enumerate(daily_data):
        if count_std > 0:
            z_score = abs((count - count_mean) / count_std)
            if z_score > 2.5:  # 异常阈值
                anomalies.append({
                    'date': str(date),
                    'value': count,
                    'z_score': round(z_score, 2),
                    'type': 'count_anomaly'
                })
    
    return {
        'detected': len(anomalies) > 0,
        'total_anomalies': len(anomalies),
        'anomaly_rate': round(len(anomalies) / len(daily_data) * 100, 2),
        'anomalies': anomalies[:10]  # 返回前10个异常
    }

def _detect_correlation_patterns(daily_data):
    """检测相关性模式"""
    counts = [row[1] for row in daily_data]
    durations = [float(row[2]) if row[2] else 0 for row in daily_data]
    
    if len(counts) < 10:
        return {'detected': False, 'reason': '数据不足'}
    
    try:
        # 故障数量与处理时长的相关性
        count_duration_corr = np.corrcoef(counts, durations)[0, 1]
        
        # 滞后相关性（前一天对后一天的影响）
        if len(counts) > 1:
            lag_corr = np.corrcoef(counts[:-1], counts[1:])[0, 1]
        else:
            lag_corr = 0
        
        return {
            'detected': abs(count_duration_corr) > 0.3 or abs(lag_corr) > 0.3,
            'correlations': {
                'count_duration': {
                    'coefficient': round(count_duration_corr, 3) if not np.isnan(count_duration_corr) else 0,
                    'strength': 'strong' if abs(count_duration_corr) > 0.7 else 'moderate' if abs(count_duration_corr) > 0.4 else 'weak'
                },
                'temporal_lag': {
                    'coefficient': round(lag_corr, 3) if not np.isnan(lag_corr) else 0,
                    'interpretation': 'previous_day_influence' if abs(lag_corr) > 0.3 else 'no_significant_lag_effect'
                }
            }
        }
    except Exception:
        return {'detected': False, 'reason': '计算相关性失败'}

def _summarize_patterns(patterns):
    """汇总模式分析结果"""
    summary = {
        'total_patterns_detected': 0,
        'pattern_types': [],
        'confidence_level': 'low'
    }
    
    for pattern_type, pattern_data in patterns.items():
        if isinstance(pattern_data, dict) and pattern_data.get('detected', False):
            summary['total_patterns_detected'] += 1
            summary['pattern_types'].append(pattern_type)
    
    if summary['total_patterns_detected'] >= 3:
        summary['confidence_level'] = 'high'
    elif summary['total_patterns_detected'] >= 2:
        summary['confidence_level'] = 'medium'
    
    return summary

def _select_best_model(data):
    """自动选择最佳预测模型"""
    # 简化的模型选择逻辑
    data_length = len(data)
    trend_strength = abs(np.polyfit(range(data_length), data, 1)[0])
    volatility = np.std(data) / np.mean(data) if np.mean(data) > 0 else 0
    
    if data_length < 30:
        return "linear"
    elif volatility > 0.5:
        return "exponential"
    elif trend_strength > 0.1:
        return "arima"
    else:
        return "linear"

def _perform_forecasting(dates, counts, durations, forecast_periods, model_type, confidence_level):
    """执行预测计算"""
    try:
        x = np.arange(len(counts))
        
        if model_type == "linear":
            # 线性回归预测
            slope, intercept = np.polyfit(x, counts, 1)
            
            forecast_x = np.arange(len(counts), len(counts) + forecast_periods)
            predicted_counts = slope * forecast_x + intercept
            predicted_counts = np.maximum(predicted_counts, 0)  # 确保非负
            
        elif model_type == "exponential":
            # 指数平滑预测
            alpha = 0.3
            smoothed = [counts[0]]
            for i in range(1, len(counts)):
                smoothed.append(alpha * counts[i] + (1 - alpha) * smoothed[-1])
            
            # 简单的指数外推
            last_value = smoothed[-1]
            growth_rate = (smoothed[-1] / smoothed[-min(10, len(smoothed))]) ** (1/min(10, len(smoothed))) - 1
            
            predicted_counts = []
            for i in range(forecast_periods):
                predicted_counts.append(max(0, last_value * ((1 + growth_rate) ** (i + 1))))
        
        else:  # ARIMA or fallback to linear
            # 简化的ARIMA模拟（实际应用中需要更复杂的实现）
            slope, intercept = np.polyfit(x, counts, 1)
            forecast_x = np.arange(len(counts), len(counts) + forecast_periods)
            
            # 添加一些随机波动来模拟ARIMA
            predicted_counts = slope * forecast_x + intercept
            noise = np.random.normal(0, np.std(counts) * 0.1, forecast_periods)
            predicted_counts = np.maximum(predicted_counts + noise, 0)
        
        # 生成置信区间
        prediction_std = np.std(counts)
        z_score = 1.96 if confidence_level >= 0.95 else 1.645  # 95% or 90% confidence
        
        confidence_upper = predicted_counts + z_score * prediction_std
        confidence_lower = np.maximum(predicted_counts - z_score * prediction_std, 0)
        
        # 趋势分析
        if len(predicted_counts) > 1:
            trend_slope = np.polyfit(range(len(predicted_counts)), predicted_counts, 1)[0]
            trend_direction = 'increasing' if trend_slope > 0.01 else 'decreasing' if trend_slope < -0.01 else 'stable'
        else:
            trend_direction = 'stable'
        
        # 预测稳定性
        prediction_volatility = np.std(predicted_counts) / np.mean(predicted_counts) if np.mean(predicted_counts) > 0 else 0
        stability = 'high' if prediction_volatility < 0.2 else 'medium' if prediction_volatility < 0.5 else 'low'
        
        return {
            'predicted_counts': [round(count, 2) for count in predicted_counts],
            'confidence_upper': [round(val, 2) for val in confidence_upper],
            'confidence_lower': [round(val, 2) for val in confidence_lower],
            'trend_direction': trend_direction,
            'prediction_stability': stability
        }
        
    except Exception as e:
        # 如果预测失败，使用简单的平均值预测
        avg_count = np.mean(counts)
        return {
            'predicted_counts': [round(avg_count, 2)] * forecast_periods,
            'confidence_upper': [round(avg_count * 1.2, 2)] * forecast_periods,
            'confidence_lower': [round(avg_count * 0.8, 2)] * forecast_periods,
            'trend_direction': 'stable',
            'prediction_stability': 'medium',
            'fallback_used': True,
            'error': str(e)
        }

def _evaluate_model_performance(data, model_type):
    """评估模型性能"""
    try:
        # 使用前80%的数据训练，后20%验证
        split_point = int(len(data) * 0.8)
        train_data = data[:split_point]
        test_data = data[split_point:]
        
        if len(test_data) < 3:
            return {'evaluation': 'insufficient_data'}
        
        # 简单的性能评估
        x_train = np.arange(len(train_data))
        if model_type == "linear":
            slope, intercept = np.polyfit(x_train, train_data, 1)
            x_test = np.arange(len(train_data), len(data))
            predictions = slope * x_test + intercept
        else:
            # 对于其他模型，使用移动平均作为预测
            predictions = [np.mean(train_data[-5:])] * len(test_data)
        
        # 计算错误指标
        mae = np.mean(np.abs(np.array(test_data) - np.array(predictions)))
        mse = np.mean((np.array(test_data) - np.array(predictions)) ** 2)
        
        return {
            'model_type': model_type,
            'mae': round(mae, 2),
            'mse': round(mse, 2),
            'accuracy_score': round(max(0, 1 - mae / (np.mean(test_data) + 0.01)), 3),
            'test_data_points': len(test_data)
        }
        
    except Exception:
        return {'evaluation': 'failed', 'model_type': model_type}
    
    
    if pattern_analysis.get('trend') == 'increasing':
        recommendations.append('故障呈上升趋势，建议制定应对策略')
    
    return recommendations

# ===============================
# 关联性分析模块 - 新增功能
# ===============================

@router.get('/api/analysis/correlation', response_model=Dict[str, Any])
async def correlation_analysis(
    correlation_type: str = Query("fault_metrics", regex="^(fault_metrics|external_factors|cross_domain)$"),
    time_range: int = Query(180, ge=30, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    故障指标关联性分析
    - fault_metrics: 故障指标内部关联性
    - external_factors: 与外部因素关联性  
    - cross_domain: 跨域关联分析
    """
    try:
        logger.info(f"开始关联性分析，类型: {correlation_type}, 时间范围: {time_range}天")
        
        # 获取时间范围内的故障数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=time_range)
        
        stmt = select(FaultRecord).where(
            FaultRecord.start_time >= start_date,
            FaultRecord.start_time <= end_date
        ).order_by(FaultRecord.start_time.desc())
        
        result = await db.execute(stmt)
        fault_records = result.scalars().all()
        
        if len(fault_records) < 10:
            return {
                'success': False,
                'message': f'数据量不足进行关联性分析，需要至少10条记录，当前只有{len(fault_records)}条'
            }
        
        correlation_results = {}
        
        if correlation_type == "fault_metrics":
            correlation_results = await _analyze_fault_metrics_correlation(fault_records)
        elif correlation_type == "external_factors":
            correlation_results = await _analyze_external_factors_correlation(fault_records, db)
        elif correlation_type == "cross_domain":
            correlation_results = await _analyze_cross_domain_correlation(fault_records, db)
        
        return {
            'success': True,
            'analysis_type': correlation_type,
            'time_range_days': time_range,
            'data_points': len(fault_records),
            'correlation_results': correlation_results,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'insights': _generate_correlation_insights(correlation_results, correlation_type)
        }
        
    except Exception as e:
        logger.error(f"关联性分析失败: {str(e)}")
        return {
            'success': False,
            'message': f'关联性分析执行失败: {str(e)}'
        }

async def _analyze_fault_metrics_correlation(fault_records):
    """故障指标内部关联性分析"""
    try:
        # 准备故障指标数据
        fault_data = []
        for record in fault_records:
            duration_hours = record.fault_duration_hours or 0
            duration_minutes = duration_hours * 60  # 转换为分钟
            fault_data.append({
                'duration': duration_minutes,
                'severity': _severity_to_numeric(record.notification_level),
                'hour_of_day': record.start_time.hour if record.start_time else 12,
                'day_of_week': record.start_time.weekday() if record.start_time else 1,
                'fault_type_code': _fault_type_to_numeric(record.province_fault_type)
            })
        
        if len(fault_data) < 10:
            return {'error': '数据不足进行关联性分析'}
        
        # 转换为numpy数组进行分析
        data_array = np.array([[
            d['duration'], d['severity'], d['hour_of_day'], 
            d['day_of_week'], d['fault_type_code']
        ] for d in fault_data])
        
        # 计算相关系数矩阵
        correlation_matrix = np.corrcoef(data_array.T)
        
        metrics = ['duration', 'severity', 'hour_of_day', 'day_of_week', 'fault_type']
        
        correlations = {}
        significant_correlations = []
        
        for i, metric1 in enumerate(metrics):
            correlations[metric1] = {}
            for j, metric2 in enumerate(metrics):
                if i != j:
                    corr_value = correlation_matrix[i][j]
                    correlations[metric1][metric2] = round(float(corr_value), 3)
                    
                    # 识别显著相关性（|r| > 0.3）
                    if abs(corr_value) > 0.3:
                        significant_correlations.append({
                            'metric1': metric1,
                            'metric2': metric2,
                            'correlation': round(float(corr_value), 3),
                            'strength': _get_correlation_strength(abs(corr_value)),
                            'direction': 'positive' if corr_value > 0 else 'negative'
                        })
        
        return {
            'correlation_matrix': correlations,
            'significant_correlations': significant_correlations,
            'analysis_method': 'pearson_correlation'
        }
        
    except Exception as e:
        return {'error': f'故障指标关联性分析失败: {str(e)}'}

async def _analyze_external_factors_correlation(fault_records, db):
    """与外部因素的关联性分析"""
    try:
        # 这里可以结合PUE数据、汇聚网络数据等外部因素
        # 获取同时间段的PUE数据
        fault_times = [r.start_time for r in fault_records if r.start_time]
        if not fault_times:
            return {'error': '故障记录缺少时间信息'}
        
        min_time = min(fault_times)
        max_time = max(fault_times)
        
        # 获取PUE数据
        pue_stmt = select(PUEData).where(
            PUEData.riqi >= min_time.date(),
            PUEData.riqi <= max_time.date()
        )
        pue_result = await db.execute(pue_stmt)
        pue_records = pue_result.scalars().all()
        
        # 获取汇聚网络数据
        huiju_stmt = select(Huijugugan).where(
            Huijugugan.riqi >= min_time.date(),
            Huijugugan.riqi <= max_time.date()
        )
        huiju_result = await db.execute(huiju_stmt)
        huiju_records = huiju_result.scalars().all()
        
        external_correlations = {}
        
        # PUE与故障的关联性
        if pue_records:
            pue_correlation = _calculate_time_series_correlation(
                fault_records, pue_records, 'pue_value'
            )
            external_correlations['pue_correlation'] = pue_correlation
        
        # 汇聚网络指标与故障的关联性
        if huiju_records:
            huiju_correlation = _calculate_time_series_correlation(
                fault_records, huiju_records, 'network_metric'
            )
            external_correlations['network_correlation'] = huiju_correlation
        
        return {
            'external_factors': external_correlations,
            'pue_data_points': len(pue_records),
            'network_data_points': len(huiju_records),
            'analysis_method': 'time_series_correlation'
        }
        
    except Exception as e:
        return {'error': f'外部因素关联性分析失败: {str(e)}'}

async def _analyze_cross_domain_correlation(fault_records, db):
    """跨域关联分析"""
    try:
        # 按故障类型分组分析
        fault_by_type = {}
        for record in fault_records:
            fault_type = record.province_fault_type or 'unknown'
            if fault_type not in fault_by_type:
                fault_by_type[fault_type] = []
            fault_by_type[fault_type].append(record)
        
        cross_domain_results = {}
        
        # 不同故障类型的时间分布相关性
        time_correlations = {}
        for fault_type1, records1 in fault_by_type.items():
            if len(records1) < 3:
                continue
            time_correlations[fault_type1] = {}
            
            for fault_type2, records2 in fault_by_type.items():
                if fault_type1 != fault_type2 and len(records2) >= 3:
                    # 计算时间序列相关性
                    correlation = _calculate_fault_type_time_correlation(records1, records2)
                    time_correlations[fault_type1][fault_type2] = correlation
        
        cross_domain_results['time_correlations'] = time_correlations
        
        # 严重程度的跨域影响
        severity_impact = _analyze_severity_cross_impact(fault_by_type)
        cross_domain_results['severity_impact'] = severity_impact
        
        return cross_domain_results
        
    except Exception as e:
        return {'error': f'跨域关联分析失败: {str(e)}'}

def _severity_to_numeric(severity):
    """将故障严重程度转换为数值"""
    # 基于通报级别进行映射
    severity_map = {
        '低': 1, 'low': 1, '一般': 1,
        '中': 2, 'medium': 2, '中等': 2,
        '高': 3, 'high': 3, '严重': 3, '重要': 3,
        '紧急': 4, 'critical': 4, '非常严重': 4, '特急': 4
    }
    if not severity:
        return 2
    return severity_map.get(str(severity).lower(), 2)

def _fault_type_to_numeric(fault_type):
    """将故障类型转换为数值编码"""
    if not fault_type:
        return 0
    # 简单的哈希编码
    return hash(fault_type) % 100

def _get_correlation_strength(abs_corr):
    """根据相关系数判断相关性强度"""
    if abs_corr >= 0.7:
        return 'strong'
    elif abs_corr >= 0.5:
        return 'moderate'
    elif abs_corr >= 0.3:
        return 'weak'
    else:
        return 'negligible'

def _calculate_time_series_correlation(fault_records, external_records, external_field):
    """计算故障与外部数据的时间序列相关性"""
    try:
        # 按日期聚合故障数量
        fault_by_date = {}
        for record in fault_records:
            if record.start_time:
                date_key = record.start_time.date()
                fault_by_date[date_key] = fault_by_date.get(date_key, 0) + 1
        
        # 按日期聚合外部数据
        external_by_date = {}
        for record in external_records:
            if hasattr(record, 'riqi') and record.riqi:
                date_key = record.riqi
                if external_field == 'pue_value':
                    value = record.zhibiao_zhi if hasattr(record, 'zhibiao_zhi') else 0
                else:
                    value = 1  # 简化处理
                external_by_date[date_key] = external_by_date.get(date_key, 0) + value
        
        # 找到共同日期
        common_dates = set(fault_by_date.keys()) & set(external_by_date.keys())
        if len(common_dates) < 5:
            return {'correlation': 0, 'significance': 'insufficient_data'}
        
        # 提取对应数据点
        fault_values = [fault_by_date[date] for date in sorted(common_dates)]
        external_values = [external_by_date[date] for date in sorted(common_dates)]
        
        # 计算相关系数
        if len(fault_values) >= 3:
            correlation = np.corrcoef(fault_values, external_values)[0, 1]
            return {
                'correlation': round(float(correlation), 3) if not np.isnan(correlation) else 0,
                'data_points': len(common_dates),
                'significance': 'significant' if abs(correlation) > 0.3 else 'not_significant'
            }
        
        return {'correlation': 0, 'significance': 'insufficient_data'}
        
    except Exception as e:
        return {'correlation': 0, 'error': str(e)}

def _calculate_fault_type_time_correlation(records1, records2):
    """计算不同故障类型的时间相关性"""
    try:
        # 提取小时级别的故障分布
        hours1 = [r.start_time.hour for r in records1 if r.start_time]
        hours2 = [r.start_time.hour for r in records2 if r.start_time]
        
        if len(hours1) < 3 or len(hours2) < 3:
            return 0
        
        # 创建24小时分布直方图
        hist1 = np.histogram(hours1, bins=24, range=(0, 24))[0]
        hist2 = np.histogram(hours2, bins=24, range=(0, 24))[0]
        
        # 计算相关系数
        correlation = np.corrcoef(hist1, hist2)[0, 1]
        return round(float(correlation), 3) if not np.isnan(correlation) else 0
        
    except Exception:
        return 0

def _analyze_severity_cross_impact(fault_by_type):
    """分析严重程度的跨域影响"""
    try:
        severity_analysis = {}
        
        for fault_type, records in fault_by_type.items():
            if len(records) < 2:
                continue
                
            severities = [_severity_to_numeric(r.notification_level) for r in records]
            avg_severity = np.mean(severities)
            
            severity_analysis[fault_type] = {
                'average_severity': round(float(avg_severity), 2),
                'severity_variance': round(float(np.var(severities)), 2),
                'total_faults': len(records)
            }
        
        return severity_analysis
        
    except Exception:
        return {}

def _generate_correlation_insights(correlation_results, correlation_type):
    """生成关联性分析洞察"""
    insights = []
    
    try:
        if correlation_type == "fault_metrics":
            if 'significant_correlations' in correlation_results:
                sig_corrs = correlation_results['significant_correlations']
                if sig_corrs:
                    insights.append(f"发现{len(sig_corrs)}个显著关联性指标对")
                    
                    strong_corrs = [c for c in sig_corrs if c.get('strength') == 'strong']
                    if strong_corrs:
                        insights.append(f"其中{len(strong_corrs)}个为强相关性，需要重点关注")
                else:
                    insights.append("各故障指标间相关性较弱，表明故障相对独立")
        
        elif correlation_type == "external_factors":
            if 'external_factors' in correlation_results:
                ext_factors = correlation_results['external_factors']
                
                if 'pue_correlation' in ext_factors:
                    pue_corr = ext_factors['pue_correlation'].get('correlation', 0)
                    if abs(pue_corr) > 0.3:
                        insights.append(f"PUE指标与故障存在{'正' if pue_corr > 0 else '负'}相关性")
                
                if 'network_correlation' in ext_factors:
                    net_corr = ext_factors['network_correlation'].get('correlation', 0)
                    if abs(net_corr) > 0.3:
                        insights.append("网络指标与故障存在相关性，建议加强网络监控")
        
        elif correlation_type == "cross_domain":
            if 'time_correlations' in correlation_results:
                time_corrs = correlation_results['time_correlations']
                if time_corrs:
                    insights.append("不同故障类型存在时间分布关联性")
                    insights.append("建议制定协同处理策略")
        
        if not insights:
            insights.append("未发现显著关联性，各指标相对独立")
            insights.append("可以采用单独优化策略")
        
    except Exception:
        insights.append("洞察生成失败，请检查分析结果")
    
    return insights

@router.get('/api/analysis/impact_assessment', response_model=Dict[str, Any])
async def fault_impact_assessment(
    assessment_dimension: str = Query("business", regex="^(business|technical|operational)$"),
    severity_weight: float = Query(1.0, ge=0.1, le=3.0),
    duration_weight: float = Query(1.0, ge=0.1, le=3.0),
    db: AsyncSession = Depends(get_db)
):
    """
    故障影响评估分析
    - business: 业务影响评估
    - technical: 技术影响评估  
    - operational: 运营影响评估
    """
    try:
        logger.info(f"开始故障影响评估，维度: {assessment_dimension}")
        
        # 获取最近6个月的故障数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=180)
        
        stmt = select(FaultRecord).where(
            FaultRecord.start_time >= start_date,
            FaultRecord.start_time <= end_date
        )
        
        result = await db.execute(stmt)
        fault_records = result.scalars().all()
        
        if len(fault_records) < 5:
            return {
                'success': False,
                'message': f'数据不足进行影响评估，需要至少5条记录'
            }
        
        impact_assessment = {}
        
        if assessment_dimension == "business":
            impact_assessment = _assess_business_impact(fault_records, severity_weight, duration_weight)
        elif assessment_dimension == "technical":
            impact_assessment = _assess_technical_impact(fault_records, severity_weight, duration_weight)
        elif assessment_dimension == "operational":
            impact_assessment = _assess_operational_impact(fault_records, severity_weight, duration_weight)
        
        return {
            'success': True,
            'assessment_dimension': assessment_dimension,
            'total_faults_analyzed': len(fault_records),
            'assessment_period_days': 180,
            'weights': {'severity': severity_weight, 'duration': duration_weight},
            'impact_assessment': impact_assessment,
            'assessment_timestamp': datetime.utcnow().isoformat(),
            'recommendations': _generate_impact_recommendations(impact_assessment, assessment_dimension)
        }
        
    except Exception as e:
        logger.error(f"故障影响评估失败: {str(e)}")
        return {
            'success': False,
            'message': f'影响评估执行失败: {str(e)}'
        }

def _assess_business_impact(fault_records, severity_weight, duration_weight):
    """业务影响评估"""
    try:
        business_impact = {
            'total_impact_score': 0,
            'high_impact_faults': 0,
            'service_disruption_hours': 0,
            'fault_type_impact': {},
            'impact_distribution': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        }
        
        for record in fault_records:
            # 计算单个故障的业务影响分数
            severity_score = _severity_to_numeric(record.notification_level) * severity_weight
            duration_hours = record.fault_duration_hours or 0
            duration_score = duration_hours * duration_weight
            
            impact_score = severity_score + duration_score
            business_impact['total_impact_score'] += impact_score
            
            # 高影响故障统计
            if impact_score > 5:
                business_impact['high_impact_faults'] += 1
            
            # 服务中断时长
            business_impact['service_disruption_hours'] += duration_hours
            
            # 按故障类型分类影响
            fault_type = record.province_fault_type or 'unknown'
            if fault_type not in business_impact['fault_type_impact']:
                business_impact['fault_type_impact'][fault_type] = {
                    'total_impact': 0,
                    'fault_count': 0,
                    'avg_impact': 0
                }
            
            business_impact['fault_type_impact'][fault_type]['total_impact'] += impact_score
            business_impact['fault_type_impact'][fault_type]['fault_count'] += 1
            
            # 影响分布统计
            if impact_score < 2:
                business_impact['impact_distribution']['low'] += 1
            elif impact_score < 4:
                business_impact['impact_distribution']['medium'] += 1
            elif impact_score < 7:
                business_impact['impact_distribution']['high'] += 1
            else:
                business_impact['impact_distribution']['critical'] += 1
        
        # 计算平均影响
        for fault_type in business_impact['fault_type_impact']:
            impact_data = business_impact['fault_type_impact'][fault_type]
            if impact_data['fault_count'] > 0:
                impact_data['avg_impact'] = round(
                    impact_data['total_impact'] / impact_data['fault_count'], 2
                )
        
        business_impact['total_impact_score'] = round(business_impact['total_impact_score'], 2)
        business_impact['service_disruption_hours'] = round(business_impact['service_disruption_hours'], 2)
        
        return business_impact
        
    except Exception as e:
        return {'error': f'业务影响评估失败: {str(e)}'}

def _assess_technical_impact(fault_records, severity_weight, duration_weight):
    """技术影响评估"""
    try:
        technical_impact = {
            'system_reliability_score': 0,
            'recovery_efficiency': 0,
            'fault_clustering': {},
            'technical_debt_indicators': [],
            'automation_opportunities': []
        }
        
        total_faults = len(fault_records)
        total_duration = sum((r.fault_duration_hours or 0) * 60 for r in fault_records)  # 转换为分钟
        
        # 系统可靠性评分 (基于故障频率和严重程度)
        severity_penalty = sum(_severity_to_numeric(r.notification_level) for r in fault_records)
        frequency_penalty = total_faults / 180  # 每日故障率
        
        reliability_score = max(0, 100 - severity_penalty - frequency_penalty * 10)
        technical_impact['system_reliability_score'] = round(reliability_score, 2)
        
        # 恢复效率 (平均恢复时间)
        avg_recovery_time = total_duration / total_faults if total_faults > 0 else 0
        recovery_efficiency = max(0, 100 - avg_recovery_time / 60)  # 按小时计算
        technical_impact['recovery_efficiency'] = round(recovery_efficiency, 2)
        
        # 故障聚类分析 (按时间聚类)
        fault_clustering = _analyze_fault_clustering(fault_records)
        technical_impact['fault_clustering'] = fault_clustering
        
        # 技术债务指标
        if avg_recovery_time > 120:  # 平均恢复时间超过2小时
            technical_impact['technical_debt_indicators'].append('恢复时间过长，需要优化故障处理流程')
        
        if total_faults > 50:  # 故障数量过多
            technical_impact['technical_debt_indicators'].append('故障频率过高，系统稳定性需要改善')
        
        # 自动化机会识别
        recurring_faults = _identify_recurring_faults(fault_records)
        if recurring_faults:
            technical_impact['automation_opportunities'].append('发现重复性故障，适合自动化处理')
        
        return technical_impact
        
    except Exception as e:
        return {'error': f'技术影响评估失败: {str(e)}'}

def _assess_operational_impact(fault_records, severity_weight, duration_weight):
    """运营影响评估"""
    try:
        operational_impact = {
            'operational_efficiency': 0,
            'resource_utilization': {},
            'cost_impact': 0,
            'team_productivity_impact': 0,
            'process_optimization_opportunities': []
        }
        
        total_faults = len(fault_records)
        total_handling_time = sum((r.fault_duration_hours or 0) * 60 for r in fault_records)  # 转换为分钟
        
        # 运营效率 (基于故障处理时间和数量)
        if total_faults > 0:
            efficiency_score = max(0, 100 - (total_handling_time / 60) / total_faults * 5)
        else:
            efficiency_score = 100
        operational_impact['operational_efficiency'] = round(efficiency_score, 2)
        
        # 资源利用率分析
        peak_hours = _analyze_fault_time_distribution(fault_records)
        operational_impact['resource_utilization'] = {
            'peak_hours': peak_hours,
            'off_peak_ratio': _calculate_off_peak_ratio(fault_records)
        }
        
        # 成本影响估算 (基于处理时长和严重程度)
        estimated_cost = 0
        for record in fault_records:
            severity_cost = _severity_to_numeric(record.notification_level) * 500  # 每级500元
            duration_cost = (record.fault_duration_hours or 0) * 60 * 10  # 每分钟10元人力成本
            estimated_cost += severity_cost + duration_cost
        
        operational_impact['cost_impact'] = round(estimated_cost, 2)
        
        # 团队生产力影响
        productivity_impact = min(100, total_handling_time / 60 / 8)  # 按工作日计算
        operational_impact['team_productivity_impact'] = round(productivity_impact, 2)
        
        # 流程优化机会
        if total_handling_time > 1000:  # 总处理时间超过1000分钟
            operational_impact['process_optimization_opportunities'].append('故障处理耗时过多，需要优化处理流程')
        
        long_duration_faults = [r for r in fault_records if (r.fault_duration_hours or 0) > 4]  # 超过4小时
        if len(long_duration_faults) > total_faults * 0.2:
            operational_impact['process_optimization_opportunities'].append('长时间故障比例过高，需要改进快速响应机制')
        
        return operational_impact
        
    except Exception as e:
        return {'error': f'运营影响评估失败: {str(e)}'}

def _analyze_fault_clustering(fault_records):
    """分析故障聚类情况"""
    try:
        # 按日期分组
        fault_by_date = {}
        for record in fault_records:
            if record.start_time:
                date_key = record.start_time.date()
                if date_key not in fault_by_date:
                    fault_by_date[date_key] = 0
                fault_by_date[date_key] += 1
        
        # 识别故障高峰期
        if not fault_by_date:
            return {'error': 'no_time_data'}
        
        daily_counts = list(fault_by_date.values())
        avg_daily_faults = np.mean(daily_counts)
        std_daily_faults = np.std(daily_counts)
        
        # 识别异常高峰日
        threshold = avg_daily_faults + 2 * std_daily_faults
        peak_days = [date for date, count in fault_by_date.items() if count > threshold]
        
        return {
            'avg_daily_faults': round(avg_daily_faults, 2),
            'peak_day_threshold': round(threshold, 2),
            'peak_days_count': len(peak_days),
            'clustering_indicator': 'high' if len(peak_days) > len(fault_by_date) * 0.1 else 'normal'
        }
        
    except Exception as e:
        return {'error': str(e)}

def _identify_recurring_faults(fault_records):
    """识别重复性故障"""
    try:
        fault_type_counts = {}
        for record in fault_records:
            fault_type = record.province_fault_type or 'unknown'
            fault_type_counts[fault_type] = fault_type_counts.get(fault_type, 0) + 1
        
        # 识别出现频率高的故障类型
        total_faults = len(fault_records)
        recurring_threshold = max(3, total_faults * 0.1)  # 至少3次或10%
        
        recurring_faults = [
            {'type': fault_type, 'count': count, 'percentage': round(count/total_faults*100, 1)}
            for fault_type, count in fault_type_counts.items()
            if count >= recurring_threshold
        ]
        
        return recurring_faults
        
    except Exception:
        return []

def _analyze_fault_time_distribution(fault_records):
    """分析故障时间分布"""
    try:
        hour_counts = {}
        for record in fault_records:
            if record.start_time:
                hour = record.start_time.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if not hour_counts:
            return []
        
        # 找出故障高峰小时
        max_count = max(hour_counts.values())
        peak_hours = [hour for hour, count in hour_counts.items() if count >= max_count * 0.8]
        
        return sorted(peak_hours)
        
    except Exception:
        return []

def _calculate_off_peak_ratio(fault_records):
    """计算非高峰时段故障比例"""
    try:
        # 定义工作时间和非工作时间
        work_hours = set(range(9, 18))  # 9:00-17:59
        
        work_time_faults = 0
        off_peak_faults = 0
        
        for record in fault_records:
            if record.start_time:
                hour = record.start_time.hour
                if hour in work_hours:
                    work_time_faults += 1
                else:
                    off_peak_faults += 1
        
        total_faults = work_time_faults + off_peak_faults
        if total_faults == 0:
            return 0
        
        return round(off_peak_faults / total_faults * 100, 2)
        
    except Exception:
        return 0

def _generate_impact_recommendations(impact_assessment, assessment_dimension):
    """生成影响评估建议"""
    recommendations = []
    
    try:
        if assessment_dimension == "business":
            if 'high_impact_faults' in impact_assessment:
                high_impact_count = impact_assessment['high_impact_faults']
                if high_impact_count > 10:
                    recommendations.append('高影响故障数量过多，建议制定专门的高优先级处理流程')
                
            if 'service_disruption_hours' in impact_assessment:
                disruption_hours = impact_assessment['service_disruption_hours']
                if disruption_hours > 100:
                    recommendations.append('服务中断时长过长，需要加强预防性维护和快速恢复能力')
        
        elif assessment_dimension == "technical":
            if 'system_reliability_score' in impact_assessment:
                reliability_score = impact_assessment['system_reliability_score']
                if reliability_score < 80:
                    recommendations.append('系统可靠性评分较低，需要进行架构优化和技术改进')
                
            if 'recovery_efficiency' in impact_assessment:
                recovery_efficiency = impact_assessment['recovery_efficiency']
                if recovery_efficiency < 70:
                    recommendations.append('故障恢复效率偏低，建议优化故障处理工具和流程')
        
        elif assessment_dimension == "operational":
            if 'operational_efficiency' in impact_assessment:
                efficiency = impact_assessment['operational_efficiency']
                if efficiency < 75:
                    recommendations.append('运营效率有待提升，考虑引入自动化工具和改进人员培训')
                
            if 'cost_impact' in impact_assessment:
                cost = impact_assessment['cost_impact']
                if cost > 50000:  # 成本超过5万元
                    recommendations.append('故障成本影响较大，需要投入资源进行根本性改善')
        
        if not recommendations:
            recommendations.append('当前指标表现良好，建议继续保持现有管理水平')
            recommendations.append('可以考虑进一步优化流程以达到更高标准')
        
    except Exception:
        recommendations.append('建议生成失败，请查看详细评估数据制定改进策略')
    
    return recommendations

# ===============================
# 二级下钻功能增强模块
# ===============================

@router.get('/api/drill_down/fault_details', response_model=Dict[str, Any])
async def fault_details_drill_down(
    drill_type: str = Query("by_type", regex="^(by_type|by_time|by_severity|by_location|by_cause)$"),
    drill_value: str = Query(..., description="下钻的具体值"),
    time_range: int = Query(90, ge=7, le=365),
    detail_level: str = Query("detailed", regex="^(summary|detailed|comprehensive)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    故障详情二级下钻分析
    - by_type: 按故障类型下钻
    - by_time: 按时间维度下钻
    - by_severity: 按严重程度下钻
    - by_location: 按地理位置下钻
    - by_cause: 按故障原因下钻
    """
    try:
        logger.info(f"开始故障详情下钻，类型: {drill_type}, 值: {drill_value}")
        
        # 获取时间范围内的故障数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=time_range)
        
        base_stmt = select(FaultRecord).where(
            FaultRecord.start_time >= start_date,
            FaultRecord.start_time <= end_date
        )
        
        # 根据下钻类型添加过滤条件
        if drill_type == "by_type":
            stmt = base_stmt.where(FaultRecord.province_fault_type == drill_value)
        elif drill_type == "by_time":
            # 按时间下钻，drill_value格式为 "YYYY-MM-DD" 或 "YYYY-MM" 或 "YYYY"
            if len(drill_value) == 4:  # 年份
                year = int(drill_value)
                stmt = base_stmt.where(extract('year', FaultRecord.start_time) == year)
            elif len(drill_value) == 7:  # 年-月
                year, month = drill_value.split('-')
                stmt = base_stmt.where(
                    extract('year', FaultRecord.start_time) == int(year),
                    extract('month', FaultRecord.start_time) == int(month)
                )
            else:  # 完整日期
                target_date = datetime.strptime(drill_value, '%Y-%m-%d').date()
                next_date = target_date + timedelta(days=1)
                stmt = base_stmt.where(
                    func.date(FaultRecord.start_time) >= target_date,
                    func.date(FaultRecord.start_time) < next_date
                )
        elif drill_type == "by_severity":
            stmt = base_stmt.where(FaultRecord.notification_level == drill_value)
        elif drill_type == "by_cause":
            stmt = base_stmt.where(FaultRecord.cause_category == drill_value)
        else:
            stmt = base_stmt
        
        result = await db.execute(stmt.order_by(FaultRecord.start_time.desc()))
        fault_records = result.scalars().all()
        
        if not fault_records:
            return {
                'success': False,
                'message': f'未找到符合下钻条件的故障记录'
            }
        
        # 根据详细级别生成分析结果
        drill_analysis = await _generate_drill_down_analysis(
            fault_records, drill_type, drill_value, detail_level, db
        )
        
        return {
            'success': True,
            'drill_type': drill_type,
            'drill_value': drill_value,
            'total_records': len(fault_records),
            'time_range_days': time_range,
            'detail_level': detail_level,
            'drill_analysis': drill_analysis,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"故障详情下钻失败: {str(e)}")
        return {
            'success': False,
            'message': f'下钻分析执行失败: {str(e)}'
        }

async def _generate_drill_down_analysis(fault_records, drill_type, drill_value, detail_level, db):
    """生成下钻分析结果"""
    try:
        analysis = {
            'basic_stats': _calculate_basic_stats(fault_records),
            'time_distribution': _analyze_time_distribution(fault_records),
            'severity_distribution': _analyze_severity_distribution(fault_records)
        }
        
        if detail_level in ['detailed', 'comprehensive']:
            analysis.update({
                'duration_analysis': _analyze_duration_patterns(fault_records),
                'related_patterns': await _find_related_patterns(fault_records, drill_type, db),
                'trend_analysis': _analyze_trends_in_subset(fault_records)
            })
        
        if detail_level == 'comprehensive':
            analysis.update({
                'comparative_analysis': await _compare_with_overall(fault_records, db),
                'root_cause_analysis': _deep_root_cause_analysis(fault_records),
                'predictive_insights': _generate_predictive_insights(fault_records),
                'actionable_recommendations': _generate_drill_down_recommendations(fault_records, drill_type, drill_value)
            })
        
        return analysis
        
    except Exception as e:
        return {'error': f'下钻分析生成失败: {str(e)}'}

def _calculate_basic_stats(fault_records):
    """计算基础统计信息"""
    try:
        if not fault_records:
            return {'error': 'no_data'}
        
        total_count = len(fault_records)
        total_duration = sum((r.fault_duration_hours or 0) for r in fault_records)
        avg_duration = total_duration / total_count if total_count > 0 else 0
        
        # 按类型分布
        type_distribution = {}
        for record in fault_records:
            fault_type = record.province_fault_type or 'unknown'
            type_distribution[fault_type] = type_distribution.get(fault_type, 0) + 1
        
        # 严重程度分布
        severity_stats = {}
        for record in fault_records:
            severity = record.notification_level or 'unknown'
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
        
        return {
            'total_faults': total_count,
            'total_duration_hours': round(total_duration, 2),
            'average_duration_hours': round(avg_duration, 2),
            'fault_type_distribution': type_distribution,
            'severity_distribution': severity_stats,
            'date_range': {
                'start': min(r.start_time for r in fault_records if r.start_time).isoformat() if fault_records else None,
                'end': max(r.start_time for r in fault_records if r.start_time).isoformat() if fault_records else None
            }
        }
        
    except Exception as e:
        return {'error': f'基础统计计算失败: {str(e)}'}

def _analyze_time_distribution(fault_records):
    """分析时间分布模式"""
    try:
        if not fault_records:
            return {'error': 'no_data'}
        
        # 按小时分布
        hourly_distribution = {}
        # 按星期分布
        weekly_distribution = {}
        # 按月分布  
        monthly_distribution = {}
        
        for record in fault_records:
            if record.start_time:
                hour = record.start_time.hour
                weekday = record.start_time.strftime('%A')
                month = record.start_time.strftime('%Y-%m')
                
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                weekly_distribution[weekday] = weekly_distribution.get(weekday, 0) + 1
                monthly_distribution[month] = monthly_distribution.get(month, 0) + 1
        
        # 识别高峰时段
        if hourly_distribution:
            peak_hour = max(hourly_distribution, key=hourly_distribution.get)
            peak_count = hourly_distribution[peak_hour]
        else:
            peak_hour = None
            peak_count = 0
        
        return {
            'hourly_distribution': hourly_distribution,
            'weekly_distribution': weekly_distribution,
            'monthly_distribution': monthly_distribution,
            'peak_time_analysis': {
                'peak_hour': peak_hour,
                'peak_hour_count': peak_count,
                'total_in_peak_hours': sum(count for hour, count in hourly_distribution.items() if hour in range(9, 18))
            }
        }
        
    except Exception as e:
        return {'error': f'时间分布分析失败: {str(e)}'}

def _analyze_severity_distribution(fault_records):
    """分析严重程度分布"""
    try:
        if not fault_records:
            return {'error': 'no_data'}
        
        severity_stats = {}
        severity_duration = {}
        
        for record in fault_records:
            severity = record.notification_level or 'unknown'
            duration = record.fault_duration_hours or 0
            
            if severity not in severity_stats:
                severity_stats[severity] = 0
                severity_duration[severity] = []
            
            severity_stats[severity] += 1
            severity_duration[severity].append(duration)
        
        # 计算各严重程度的平均处理时间
        severity_avg_duration = {}
        for severity, durations in severity_duration.items():
            if durations:
                severity_avg_duration[severity] = round(sum(durations) / len(durations), 2)
        
        # 严重程度权重计算
        severity_weights = {
            '低': 1, '一般': 1,
            '中': 2, '中等': 2,
            '高': 3, '严重': 3, '重要': 3,
            '紧急': 4, '特急': 4, '非常严重': 4
        }
        
        total_weight = sum(
            severity_weights.get(severity, 2) * count 
            for severity, count in severity_stats.items()
        )
        
        return {
            'severity_counts': severity_stats,
            'severity_avg_duration': severity_avg_duration,
            'severity_weight_score': total_weight,
            'high_severity_ratio': sum(
                count for severity, count in severity_stats.items()
                if severity_weights.get(severity, 2) >= 3
            ) / len(fault_records) if fault_records else 0
        }
        
    except Exception as e:
        return {'error': f'严重程度分布分析失败: {str(e)}'}

def _analyze_duration_patterns(fault_records):
    """分析处理时长模式"""
    try:
        if not fault_records:
            return {'error': 'no_data'}
        
        durations = [r.fault_duration_hours or 0 for r in fault_records]
        if not durations:
            return {'error': 'no_duration_data'}
        
        durations = np.array(durations)
        
        # 基础统计
        mean_duration = np.mean(durations)
        median_duration = np.median(durations)
        std_duration = np.std(durations)
        
        # 分布分析
        quick_fixes = sum(1 for d in durations if d <= 1)  # 1小时内
        standard_fixes = sum(1 for d in durations if 1 < d <= 4)  # 1-4小时
        long_fixes = sum(1 for d in durations if d > 4)  # 超过4小时
        
        # 异常值检测
        q75, q25 = np.percentile(durations, [75, 25])
        iqr = q75 - q25
        outlier_threshold = q75 + 1.5 * iqr
        outliers = sum(1 for d in durations if d > outlier_threshold)
        
        return {
            'duration_statistics': {
                'mean_hours': round(float(mean_duration), 2),
                'median_hours': round(float(median_duration), 2),
                'std_deviation': round(float(std_duration), 2),
                'min_hours': round(float(np.min(durations)), 2),
                'max_hours': round(float(np.max(durations)), 2)
            },
            'duration_categories': {
                'quick_fixes': quick_fixes,
                'standard_fixes': standard_fixes, 
                'long_fixes': long_fixes
            },
            'outlier_analysis': {
                'outlier_count': int(outliers),
                'outlier_threshold_hours': round(float(outlier_threshold), 2),
                'outlier_ratio': round(outliers / len(durations), 3) if durations.size > 0 else 0
            }
        }
        
    except Exception as e:
        return {'error': f'处理时长分析失败: {str(e)}'}

async def _find_related_patterns(fault_records, drill_type, db):
    """寻找相关模式"""
    try:
        patterns = {}
        
        if drill_type == "by_type":
            # 寻找相同类型故障的时间聚集模式
            time_clusters = _find_time_clusters(fault_records)
            patterns['time_clustering'] = time_clusters
            
        elif drill_type == "by_time":
            # 寻找同时间段的其他故障类型
            related_types = await _find_concurrent_fault_types(fault_records, db)
            patterns['concurrent_types'] = related_types
            
        elif drill_type == "by_severity":
            # 寻找相同严重程度故障的共同特征
            common_features = _find_common_features(fault_records)
            patterns['common_features'] = common_features
        
        return patterns
        
    except Exception as e:
        return {'error': f'关联模式分析失败: {str(e)}'}

def _find_time_clusters(fault_records):
    """寻找时间聚集模式"""
    try:
        if len(fault_records) < 3:
            return {'clusters': [], 'cluster_count': 0}
        
        # 将故障按时间排序
        sorted_faults = sorted(
            [r for r in fault_records if r.start_time], 
            key=lambda x: x.start_time
        )
        
        clusters = []
        current_cluster = []
        cluster_threshold_hours = 24  # 24小时内算作一个集群
        
        for fault in sorted_faults:
            if not current_cluster:
                current_cluster.append(fault)
            else:
                time_diff = (fault.start_time - current_cluster[-1].start_time).total_seconds() / 3600
                if time_diff <= cluster_threshold_hours:
                    current_cluster.append(fault)
                else:
                    if len(current_cluster) >= 2:  # 至少2个故障才算集群
                        clusters.append({
                            'start_time': current_cluster[0].start_time.isoformat(),
                            'end_time': current_cluster[-1].start_time.isoformat(),
                            'fault_count': len(current_cluster),
                            'duration_hours': time_diff
                        })
                    current_cluster = [fault]
        
        # 处理最后一个集群
        if len(current_cluster) >= 2:
            time_span = (current_cluster[-1].start_time - current_cluster[0].start_time).total_seconds() / 3600
            clusters.append({
                'start_time': current_cluster[0].start_time.isoformat(),
                'end_time': current_cluster[-1].start_time.isoformat(),
                'fault_count': len(current_cluster),
                'duration_hours': round(time_span, 2)
            })
        
        return {
            'clusters': clusters,
            'cluster_count': len(clusters),
            'clustered_faults': sum(c['fault_count'] for c in clusters),
            'clustering_ratio': sum(c['fault_count'] for c in clusters) / len(fault_records) if fault_records else 0
        }
        
    except Exception as e:
        return {'error': f'时间聚集分析失败: {str(e)}'}

async def _find_concurrent_fault_types(fault_records, db):
    """寻找并发故障类型"""
    try:
        if not fault_records:
            return {'concurrent_types': [], 'analysis': 'no_data'}
        
        # 获取故障时间范围
        fault_times = [r.start_time for r in fault_records if r.start_time]
        if not fault_times:
            return {'concurrent_types': [], 'analysis': 'no_time_data'}
        
        min_time = min(fault_times)
        max_time = max(fault_times)
        
        # 查询同时间段的其他类型故障
        concurrent_stmt = select(FaultRecord).where(
            FaultRecord.start_time >= min_time,
            FaultRecord.start_time <= max_time
        )
        
        result = await db.execute(concurrent_stmt)
        all_concurrent_faults = result.scalars().all()
        
        # 统计并发故障类型
        current_types = set(r.province_fault_type for r in fault_records if r.province_fault_type)
        concurrent_types = {}
        
        for fault in all_concurrent_faults:
            if fault.province_fault_type and fault.province_fault_type not in current_types:
                fault_type = fault.province_fault_type
                if fault_type not in concurrent_types:
                    concurrent_types[fault_type] = 0
                concurrent_types[fault_type] += 1
        
        # 排序并取前5
        top_concurrent = sorted(
            concurrent_types.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            'concurrent_types': [{'type': t, 'count': c} for t, c in top_concurrent],
            'total_concurrent_faults': len(all_concurrent_faults) - len(fault_records),
            'analysis': 'concurrent_analysis_complete'
        }
        
    except Exception as e:
        return {'error': f'并发故障类型分析失败: {str(e)}'}

def _find_common_features(fault_records):
    """寻找共同特征"""
    try:
        if not fault_records:
            return {'features': {}, 'analysis': 'no_data'}
        
        features = {}
        
        # 分析故障原因分类
        cause_categories = {}
        for record in fault_records:
            cause = record.cause_category or 'unknown'
            cause_categories[cause] = cause_categories.get(cause, 0) + 1
        
        features['cause_distribution'] = cause_categories
        
        # 分析发现方式
        discovery_methods = {}
        for record in fault_records:
            method = record.is_proactive_discovery or 'unknown'
            discovery_methods[method] = discovery_methods.get(method, 0) + 1
        
        features['discovery_methods'] = discovery_methods
        
        # 分析时间模式
        hour_patterns = {}
        for record in fault_records:
            if record.start_time:
                hour_group = _categorize_hour(record.start_time.hour)
                hour_patterns[hour_group] = hour_patterns.get(hour_group, 0) + 1
        
        features['time_patterns'] = hour_patterns
        
        return {
            'features': features,
            'total_records_analyzed': len(fault_records),
            'analysis': 'feature_analysis_complete'
        }
        
    except Exception as e:
        return {'error': f'共同特征分析失败: {str(e)}'}

def _categorize_hour(hour):
    """将小时分类"""
    if 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    elif 18 <= hour < 24:
        return 'evening'
    else:
        return 'night'

def _analyze_trends_in_subset(fault_records):
    """分析子集中的趋势"""
    try:
        if len(fault_records) < 3:
            return {'trend': 'insufficient_data'}
        
        # 按月份统计故障数量
        monthly_counts = {}
        for record in fault_records:
            if record.start_time:
                month_key = record.start_time.strftime('%Y-%m')
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        if len(monthly_counts) < 2:
            return {'trend': 'insufficient_time_span'}
        
        # 计算趋势
        months = sorted(monthly_counts.keys())
        counts = [monthly_counts[month] for month in months]
        
        # 简单线性趋势计算
        n = len(counts)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(counts)
        sum_xy = sum(x[i] * counts[i] for i in range(n))
        sum_x2 = sum(x_val ** 2 for x_val in x)
        
        # 线性回归系数
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        trend_direction = 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable'
        
        return {
            'trend_direction': trend_direction,
            'trend_slope': round(slope, 3),
            'monthly_data': monthly_counts,
            'analysis_period_months': len(months),
            'trend_confidence': 'high' if abs(slope) > 0.5 else 'medium' if abs(slope) > 0.1 else 'low'
        }
        
    except Exception as e:
        return {'error': f'趋势分析失败: {str(e)}'}

async def _compare_with_overall(fault_records, db):
    """与整体数据比较"""
    try:
        # 获取整体数据进行比较
        overall_stmt = select(FaultRecord).where(
            FaultRecord.start_time >= datetime.utcnow() - timedelta(days=365)
        )
        
        result = await db.execute(overall_stmt)
        overall_records = result.scalars().all()
        
        if not overall_records:
            return {'comparison': 'no_overall_data'}
        
        # 计算当前子集的统计指标
        subset_stats = _calculate_comparison_stats(fault_records)
        overall_stats = _calculate_comparison_stats(overall_records)
        
        comparison = {}
        for key in subset_stats:
            if key in overall_stats and overall_stats[key] != 0:
                ratio = subset_stats[key] / overall_stats[key]
                comparison[key] = {
                    'subset_value': subset_stats[key],
                    'overall_value': overall_stats[key],
                    'ratio': round(ratio, 2),
                    'comparison': 'higher' if ratio > 1.1 else 'lower' if ratio < 0.9 else 'similar'
                }
        
        return {
            'comparison_results': comparison,
            'subset_size': len(fault_records),
            'overall_size': len(overall_records),
            'analysis': 'comparison_complete'
        }
        
    except Exception as e:
        return {'error': f'整体比较分析失败: {str(e)}'}

def _calculate_comparison_stats(fault_records):
    """计算用于比较的统计指标"""
    if not fault_records:
        return {}
    
    durations = [r.fault_duration_hours or 0 for r in fault_records]
    severities = [_severity_to_numeric(r.notification_level) for r in fault_records]
    
    return {
        'avg_duration': np.mean(durations) if durations else 0,
        'avg_severity': np.mean(severities) if severities else 0,
        'fault_rate_per_day': len(fault_records) / 30,  # 假设30天
        'high_severity_ratio': sum(1 for s in severities if s >= 3) / len(severities) if severities else 0
    }

def _deep_root_cause_analysis(fault_records):
    """深度根因分析"""
    try:
        if not fault_records:
            return {'analysis': 'no_data'}
        
        # 分析故障原因模式
        cause_patterns = {}
        for record in fault_records:
            cause = record.cause_category or 'unknown'
            province_cause = record.province_cause_category or 'unknown'
            
            key = f"{cause}-{province_cause}"
            if key not in cause_patterns:
                cause_patterns[key] = {
                    'count': 0,
                    'avg_duration': 0,
                    'durations': []
                }
            
            cause_patterns[key]['count'] += 1
            duration = record.fault_duration_hours or 0
            cause_patterns[key]['durations'].append(duration)
        
        # 计算每种原因的平均处理时间
        for pattern in cause_patterns.values():
            if pattern['durations']:
                pattern['avg_duration'] = round(sum(pattern['durations']) / len(pattern['durations']), 2)
            del pattern['durations']  # 移除原始数据以减少响应大小
        
        # 识别主要根因
        top_causes = sorted(
            cause_patterns.items(), 
            key=lambda x: x[1]['count'], 
            reverse=True
        )[:5]
        
        # 分析故障处理效率
        handling_analysis = {}
        proactive_count = sum(1 for r in fault_records if r.is_proactive_discovery == '是')
        reactive_count = len(fault_records) - proactive_count
        
        handling_analysis = {
            'proactive_discovery': proactive_count,
            'reactive_discovery': reactive_count,
            'proactive_ratio': round(proactive_count / len(fault_records), 2) if fault_records else 0
        }
        
        return {
            'cause_patterns': dict(top_causes),
            'handling_analysis': handling_analysis,
            'total_analyzed': len(fault_records),
            'analysis_quality': 'high' if len(fault_records) > 10 else 'medium' if len(fault_records) > 5 else 'low'
        }
        
    except Exception as e:
        return {'error': f'根因分析失败: {str(e)}'}

def _generate_predictive_insights(fault_records):
    """生成预测性洞察"""
    try:
        if len(fault_records) < 5:
            return {'insights': [], 'confidence': 'low'}
        
        insights = []
        
        # 基于历史模式预测
        time_patterns = {}
        for record in fault_records:
            if record.start_time:
                hour = record.start_time.hour
                weekday = record.start_time.weekday()
                key = f"weekday_{weekday}_hour_{hour}"
                time_patterns[key] = time_patterns.get(key, 0) + 1
        
        # 识别高风险时段
        if time_patterns:
            peak_pattern = max(time_patterns, key=time_patterns.get)
            peak_count = time_patterns[peak_pattern]
            if peak_count >= len(fault_records) * 0.3:  # 30%以上的故障在同一时段
                insights.append(f"预测高风险时段: {peak_pattern}, 建议加强预防性监控")
        
        # 基于严重程度趋势
        recent_faults = sorted(
            [r for r in fault_records if r.start_time], 
            key=lambda x: x.start_time, 
            reverse=True
        )[:5]
        
        if len(recent_faults) >= 3:
            recent_severities = [_severity_to_numeric(r.notification_level) for r in recent_faults]
            avg_recent_severity = sum(recent_severities) / len(recent_severities)
            
            all_severities = [_severity_to_numeric(r.notification_level) for r in fault_records]
            avg_overall_severity = sum(all_severities) / len(all_severities)
            
            if avg_recent_severity > avg_overall_severity * 1.2:
                insights.append("预测严重程度呈上升趋势，建议加强预防措施")
        
        # 基于故障类型模式
        type_frequency = {}
        for record in fault_records:
            fault_type = record.province_fault_type or 'unknown'
            type_frequency[fault_type] = type_frequency.get(fault_type, 0) + 1
        
        if type_frequency:
            dominant_type = max(type_frequency, key=type_frequency.get)
            if type_frequency[dominant_type] > len(fault_records) * 0.4:
                insights.append(f"预测主要风险类型: {dominant_type}, 建议针对性改进")
        
        confidence = 'high' if len(fault_records) > 20 else 'medium' if len(fault_records) > 10 else 'low'
        
        return {
            'insights': insights,
            'confidence': confidence,
            'analysis_basis': len(fault_records)
        }
        
    except Exception as e:
        return {'error': f'预测性洞察生成失败: {str(e)}'}

def _generate_drill_down_recommendations(fault_records, drill_type, drill_value):
    """生成下钻分析建议"""
    try:
        recommendations = []
        
        if not fault_records:
            return ['未找到相关数据，无法生成具体建议']
        
        # 基于下钻类型的特定建议
        if drill_type == "by_type":
            type_count = len(fault_records)
            avg_duration = sum(r.fault_duration_hours or 0 for r in fault_records) / type_count
            
            recommendations.append(f"{drill_value}类型故障共{type_count}次，平均处理时长{avg_duration:.1f}小时")
            
            if avg_duration > 2:
                recommendations.append(f"建议优化{drill_value}类型故障的处理流程，缩短处理时间")
            
            if type_count > len(fault_records) * 0.3:
                recommendations.append(f"{drill_value}是主要故障类型，建议制定专项改进计划")
                
        elif drill_type == "by_time":
            time_count = len(fault_records)
            recommendations.append(f"时间段{drill_value}内发生{time_count}次故障")
            
            # 分析时间模式
            hours = [r.start_time.hour for r in fault_records if r.start_time]
            if hours:
                peak_hour = max(set(hours), key=hours.count)
                recommendations.append(f"高峰时段为{peak_hour}点，建议在此时段加强监控")
        
        elif drill_type == "by_severity":
            severity_count = len(fault_records)
            recommendations.append(f"{drill_value}级别故障共{severity_count}次")
            
            severity_num = _severity_to_numeric(drill_value)
            if severity_num >= 3:
                recommendations.append("高严重程度故障需要制定应急响应预案")
            
        # 通用建议
        durations = [r.fault_duration_hours or 0 for r in fault_records]
        long_duration_count = sum(1 for d in durations if d > 4)
        
        if long_duration_count > len(fault_records) * 0.2:
            recommendations.append("长时间故障比例较高，建议分析处理瓶颈")
        
        # 基于故障频率的建议
        if len(fault_records) > 10:
            recommendations.append("故障频率较高，建议进行根本原因分析")
        elif len(fault_records) < 3:
            recommendations.append("故障频率较低，继续保持良好状态")
        
        return recommendations
        
    except Exception as e:
        return [f'建议生成失败: {str(e)}']

# ===============================
# 智能推荐引擎模块
# ===============================

@router.get('/api/recommendations/intelligent', response_model=Dict[str, Any])
async def intelligent_recommendations(
    recommendation_type: str = Query("comprehensive", regex="^(comprehensive|preventive|reactive|strategic)$"),
    priority_level: str = Query("high", regex="^(low|medium|high|critical)$"),
    time_horizon: str = Query("short_term", regex="^(immediate|short_term|medium_term|long_term)$"),
    focus_area: str = Query("all", regex="^(all|reliability|efficiency|cost|quality)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    智能推荐引擎
    - comprehensive: 全面推荐（整合所有分析结果）
    - preventive: 预防性推荐（基于预测分析）
    - reactive: 响应性推荐（基于当前问题）
    - strategic: 战略性推荐（长期优化建议）
    """
    try:
        logger.info(f"开始智能推荐分析，类型: {recommendation_type}, 优先级: {priority_level}")
        
        # 获取最近6个月的数据进行综合分析
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=180)
        
        stmt = select(FaultRecord).where(
            FaultRecord.start_time >= start_date,
            FaultRecord.start_time <= end_date
        ).order_by(FaultRecord.start_time.desc())
        
        result = await db.execute(stmt)
        fault_records = result.scalars().all()
        
        if not fault_records:
            return {
                'success': False,
                'message': '无足够数据生成智能推荐'
            }
        
        # 运行综合分析以获得推荐依据
        analysis_context = await _run_comprehensive_analysis(fault_records, db)
        
        # 根据推荐类型生成智能建议
        recommendations = await _generate_intelligent_recommendations(
            analysis_context, recommendation_type, priority_level, 
            time_horizon, focus_area, fault_records
        )
        
        return {
            'success': True,
            'recommendation_type': recommendation_type,
            'priority_level': priority_level,
            'time_horizon': time_horizon,
            'focus_area': focus_area,
            'data_period_days': 180,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'recommendations': recommendations,
            'analysis_summary': _generate_analysis_summary(analysis_context, len(fault_records))
        }
        
    except Exception as e:
        logger.error(f"智能推荐引擎失败: {str(e)}")
        return {
            'success': False,
            'message': f'智能推荐生成失败: {str(e)}'
        }

async def _run_comprehensive_analysis(fault_records, db):
    """运行综合分析获得推荐依据"""
    try:
        context = {}
        
        # 1. 基础统计分析
        context['basic_stats'] = _calculate_basic_stats(fault_records)
        
        # 2. 时间模式分析
        context['time_patterns'] = _analyze_time_distribution(fault_records)
        
        # 3. 严重程度分析
        context['severity_analysis'] = _analyze_severity_distribution(fault_records)
        
        # 4. 持续时长分析
        context['duration_analysis'] = _analyze_duration_patterns(fault_records)
        
        # 5. 趋势分析
        context['trend_analysis'] = _analyze_trends_in_subset(fault_records)
        
        # 6. 根本原因分析
        context['root_cause_analysis'] = _deep_root_cause_analysis(fault_records)
        
        # 7. 相关性分析（简化版）
        if len(fault_records) >= 10:
            context['correlation_insights'] = await _analyze_fault_metrics_correlation(fault_records)
        
        # 8. 影响评估分析
        context['business_impact'] = _assess_business_impact(fault_records, 1.0, 1.0)
        context['technical_impact'] = _assess_technical_impact(fault_records, 1.0, 1.0)
        context['operational_impact'] = _assess_operational_impact(fault_records, 1.0, 1.0)
        
        # 9. 预测性洞察
        context['predictive_insights'] = _generate_predictive_insights(fault_records)
        
        return context
        
    except Exception as e:
        logger.error(f"综合分析运行失败: {str(e)}")
        return {'error': str(e)}

async def _generate_intelligent_recommendations(
    analysis_context, recommendation_type, priority_level, 
    time_horizon, focus_area, fault_records
):
    """生成智能推荐建议"""
    try:
        recommendations = {
            'immediate_actions': [],
            'short_term_improvements': [],
            'medium_term_strategies': [],
            'long_term_optimizations': [],
            'priority_ranking': []
        }
        
        # 基于分析结果生成不同类型的推荐
        if recommendation_type in ['comprehensive', 'preventive']:
            recommendations.update(await _generate_preventive_recommendations(analysis_context, fault_records))
        
        if recommendation_type in ['comprehensive', 'reactive']:
            recommendations.update(await _generate_reactive_recommendations(analysis_context, fault_records))
        
        if recommendation_type in ['comprehensive', 'strategic']:
            recommendations.update(await _generate_strategic_recommendations(analysis_context, fault_records))
        
        # 根据焦点领域过滤和调整推荐
        recommendations = _filter_by_focus_area(recommendations, focus_area, analysis_context)
        
        # 根据优先级和时间范围排序和筛选
        recommendations = _prioritize_recommendations(recommendations, priority_level, time_horizon)
        
        return recommendations
        
    except Exception as e:
        return {'error': f'智能推荐生成失败: {str(e)}'}

async def _generate_preventive_recommendations(analysis_context, fault_records):
    """生成预防性推荐"""
    try:
        preventive_recs = {
            'monitoring_enhancements': [],
            'proactive_measures': [],
            'risk_mitigation': []
        }
        
        # 基于时间模式的预防建议
        if 'time_patterns' in analysis_context:
            time_data = analysis_context['time_patterns']
            if 'peak_time_analysis' in time_data and time_data['peak_time_analysis']['peak_hour'] is not None:
                peak_hour = time_data['peak_time_analysis']['peak_hour']
                preventive_recs['monitoring_enhancements'].append({
                    'action': f'在{peak_hour}时加强系统监控',
                    'priority': 'high',
                    'estimated_effort': 'low',
                    'expected_impact': 'medium',
                    'implementation_time': '1-2周'
                })
        
        # 基于严重程度分析的预防建议
        if 'severity_analysis' in analysis_context:
            severity_data = analysis_context['severity_analysis']
            if severity_data.get('high_severity_ratio', 0) > 0.3:
                preventive_recs['risk_mitigation'].append({
                    'action': '建立高严重程度故障预警机制',
                    'priority': 'critical',
                    'estimated_effort': 'medium',
                    'expected_impact': 'high',
                    'implementation_time': '2-4周'
                })
        
        # 基于根因分析的预防建议
        if 'root_cause_analysis' in analysis_context:
            root_cause_data = analysis_context['root_cause_analysis']
            if 'cause_patterns' in root_cause_data:
                top_causes = sorted(
                    root_cause_data['cause_patterns'].items(),
                    key=lambda x: x[1]['count'],
                    reverse=True
                )[:3]
                
                for cause, data in top_causes:
                    if data['count'] > len(fault_records) * 0.15:  # 超过15%的故障
                        preventive_recs['proactive_measures'].append({
                            'action': f'针对"{cause}"原因制定预防性维护计划',
                            'priority': 'high',
                            'estimated_effort': 'medium',
                            'expected_impact': 'high',
                            'implementation_time': '3-6周',
                            'affected_faults': data['count']
                        })
        
        # 基于预测洞察的建议
        if 'predictive_insights' in analysis_context:
            insights = analysis_context['predictive_insights'].get('insights', [])
            for insight in insights:
                if '预测' in insight and '风险' in insight:
                    preventive_recs['risk_mitigation'].append({
                        'action': f'基于预测分析: {insight}',
                        'priority': 'medium',
                        'estimated_effort': 'low',
                        'expected_impact': 'medium',
                        'implementation_time': '1-3周'
                    })
        
        return {'preventive_recommendations': preventive_recs}
        
    except Exception as e:
        return {'preventive_recommendations': {'error': str(e)}}

async def _generate_reactive_recommendations(analysis_context, fault_records):
    """生成响应性推荐"""
    try:
        reactive_recs = {
            'immediate_fixes': [],
            'process_improvements': [],
            'resource_adjustments': []
        }
        
        # 基于持续时长分析的响应建议
        if 'duration_analysis' in analysis_context:
            duration_data = analysis_context['duration_analysis']
            if 'outlier_analysis' in duration_data:
                outlier_ratio = duration_data['outlier_analysis'].get('outlier_ratio', 0)
                if outlier_ratio > 0.1:  # 10%以上的异常值
                    reactive_recs['immediate_fixes'].append({
                        'action': '调查和修复处理时长异常的根本原因',
                        'priority': 'high',
                        'estimated_effort': 'high',
                        'expected_impact': 'high',
                        'implementation_time': '立即执行',
                        'affected_percentage': f'{outlier_ratio*100:.1f}%'
                    })
            
            if 'duration_categories' in duration_data:
                long_fixes = duration_data['duration_categories'].get('long_fixes', 0)
                total_fixes = sum(duration_data['duration_categories'].values())
                if long_fixes > total_fixes * 0.25:  # 长时修复超过25%
                    reactive_recs['process_improvements'].append({
                        'action': '优化长时故障处理流程',
                        'priority': 'high',
                        'estimated_effort': 'medium',
                        'expected_impact': 'high',
                        'implementation_time': '2-4周',
                        'current_ratio': f'{long_fixes/total_fixes*100:.1f}%'
                    })
        
        # 基于业务影响的响应建议
        if 'business_impact' in analysis_context and 'error' not in analysis_context['business_impact']:
            business_data = analysis_context['business_impact']
            if business_data.get('high_impact_faults', 0) > 5:
                reactive_recs['immediate_fixes'].append({
                    'action': '建立高影响故障快速响应团队',
                    'priority': 'critical',
                    'estimated_effort': 'medium',
                    'expected_impact': 'high',
                    'implementation_time': '1周内',
                    'high_impact_count': business_data['high_impact_faults']
                })
        
        # 基于技术影响的响应建议
        if 'technical_impact' in analysis_context and 'error' not in analysis_context['technical_impact']:
            tech_data = analysis_context['technical_impact']
            if tech_data.get('system_reliability_score', 100) < 70:
                reactive_recs['immediate_fixes'].append({
                    'action': '系统可靠性评分偏低，需要紧急技术改进',
                    'priority': 'critical',
                    'estimated_effort': 'high',
                    'expected_impact': 'high',
                    'implementation_time': '立即执行',
                    'current_score': tech_data['system_reliability_score']
                })
            
            if tech_data.get('recovery_efficiency', 100) < 60:
                reactive_recs['process_improvements'].append({
                    'action': '改进故障恢复效率，缩短恢复时间',
                    'priority': 'high',
                    'estimated_effort': 'medium',
                    'expected_impact': 'high',
                    'implementation_time': '2-3周',
                    'current_efficiency': tech_data['recovery_efficiency']
                })
        
        return {'reactive_recommendations': reactive_recs}
        
    except Exception as e:
        return {'reactive_recommendations': {'error': str(e)}}

async def _generate_strategic_recommendations(analysis_context, fault_records):
    """生成战略性推荐"""
    try:
        strategic_recs = {
            'infrastructure_improvements': [],
            'process_automation': [],
            'capability_building': [],
            'governance_enhancements': []
        }
        
        # 基于趋势分析的战略建议
        if 'trend_analysis' in analysis_context:
            trend_data = analysis_context['trend_analysis']
            if trend_data.get('trend_direction') == 'increasing':
                strategic_recs['infrastructure_improvements'].append({
                    'action': '故障呈上升趋势，需要系统性基础设施升级',
                    'priority': 'high',
                    'estimated_effort': 'high',
                    'expected_impact': 'high',
                    'implementation_time': '3-6个月',
                    'investment_level': 'high',
                    'trend_confidence': trend_data.get('trend_confidence', 'medium')
                })
        
        # 基于根因分析的战略建议
        if 'root_cause_analysis' in analysis_context:
            root_cause_data = analysis_context['root_cause_analysis']
            proactive_ratio = root_cause_data.get('handling_analysis', {}).get('proactive_ratio', 0)
            
            if proactive_ratio < 0.5:  # 主动发现率低于50%
                strategic_recs['capability_building'].append({
                    'action': '建设主动故障发现和预防能力',
                    'priority': 'medium',
                    'estimated_effort': 'high',
                    'expected_impact': 'high',
                    'implementation_time': '6-12个月',
                    'current_proactive_ratio': f'{proactive_ratio*100:.1f}%',
                    'target_ratio': '80%'
                })
        
        # 基于相关性分析的战略建议
        if 'correlation_insights' in analysis_context:
            corr_data = analysis_context['correlation_insights']
            if 'significant_correlations' in corr_data and corr_data['significant_correlations']:
                strong_correlations = [
                    c for c in corr_data['significant_correlations'] 
                    if c.get('strength') == 'strong'
                ]
                if strong_correlations:
                    strategic_recs['process_automation'].append({
                        'action': '基于强相关性指标建立自动化预警和处理系统',
                        'priority': 'medium',
                        'estimated_effort': 'high',
                        'expected_impact': 'high',
                        'implementation_time': '4-8个月',
                        'strong_correlations_count': len(strong_correlations)
                    })
        
        # 基于运营影响的战略建议
        if 'operational_impact' in analysis_context and 'error' not in analysis_context['operational_impact']:
            ops_data = analysis_context['operational_impact']
            if ops_data.get('operational_efficiency', 100) < 75:
                strategic_recs['governance_enhancements'].append({
                    'action': '建立运营效率治理框架和KPI体系',
                    'priority': 'medium',
                    'estimated_effort': 'medium',
                    'expected_impact': 'high',
                    'implementation_time': '2-4个月',
                    'current_efficiency': ops_data['operational_efficiency']
                })
            
            if ops_data.get('cost_impact', 0) > 100000:  # 成本影响超过10万
                strategic_recs['infrastructure_improvements'].append({
                    'action': '故障成本影响较大，考虑系统架构重构',
                    'priority': 'high',
                    'estimated_effort': 'very_high',
                    'expected_impact': 'very_high',
                    'implementation_time': '6-18个月',
                    'current_cost_impact': ops_data['cost_impact'],
                    'investment_justification': '长期成本节约'
                })
        
        return {'strategic_recommendations': strategic_recs}
        
    except Exception as e:
        return {'strategic_recommendations': {'error': str(e)}}

def _filter_by_focus_area(recommendations, focus_area, analysis_context):
    """根据焦点领域过滤推荐"""
    try:
        if focus_area == 'all':
            return recommendations
        
        filtered_recs = {}
        
        # 根据焦点领域筛选相关推荐
        focus_keywords = {
            'reliability': ['可靠性', '稳定性', '预警', '监控', '预防'],
            'efficiency': ['效率', '时长', '恢复', '处理', '响应'],
            'cost': ['成本', '投入', '节约', '资源', '投资'],
            'quality': ['质量', '准确性', '完整性', '标准', '流程']
        }
        
        keywords = focus_keywords.get(focus_area, [])
        
        for rec_type, rec_data in recommendations.items():
            if isinstance(rec_data, dict):
                filtered_recs[rec_type] = {}
                for sub_type, sub_data in rec_data.items():
                    if isinstance(sub_data, list):
                        filtered_items = []
                        for item in sub_data:
                            if isinstance(item, dict) and 'action' in item:
                                action_text = item['action'].lower()
                                if any(keyword in action_text for keyword in keywords):
                                    filtered_items.append(item)
                        if filtered_items:
                            filtered_recs[rec_type][sub_type] = filtered_items
                    else:
                        filtered_recs[rec_type][sub_type] = sub_data
            else:
                filtered_recs[rec_type] = rec_data
        
        return filtered_recs if any(filtered_recs.values()) else recommendations
        
    except Exception as e:
        logger.error(f"焦点领域过滤失败: {str(e)}")
        return recommendations

def _prioritize_recommendations(recommendations, priority_level, time_horizon):
    """根据优先级和时间范围排序推荐"""
    try:
        # 优先级权重映射
        priority_weights = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        
        # 时间范围映射
        time_horizon_map = {
            'immediate': ['立即执行', '1周内'],
            'short_term': ['1-2周', '2-4周', '1-3周'],
            'medium_term': ['2-4个月', '3-6周', '3-6个月'],
            'long_term': ['4-8个月', '6-12个月', '6-18个月']
        }
        
        prioritized_recs = {}
        
        for rec_type, rec_data in recommendations.items():
            if isinstance(rec_data, dict):
                prioritized_recs[rec_type] = {}
                for sub_type, sub_data in rec_data.items():
                    if isinstance(sub_data, list):
                        # 过滤和排序推荐项
                        filtered_items = []
                        for item in sub_data:
                            if isinstance(item, dict):
                                # 优先级过滤
                                item_priority = item.get('priority', 'medium')
                                if priority_weights.get(item_priority, 2) >= priority_weights.get(priority_level, 2):
                                    # 时间范围过滤
                                    item_time = item.get('implementation_time', '')
                                    if (time_horizon == 'all' or 
                                        any(time_phrase in item_time for time_phrase in time_horizon_map.get(time_horizon, []))):
                                        filtered_items.append(item)
                        
                        # 按优先级排序
                        filtered_items.sort(
                            key=lambda x: priority_weights.get(x.get('priority', 'medium'), 2),
                            reverse=True
                        )
                        
                        if filtered_items:
                            prioritized_recs[rec_type][sub_type] = filtered_items
                    else:
                        prioritized_recs[rec_type][sub_type] = sub_data
            else:
                prioritized_recs[rec_type] = rec_data
        
        # 生成优先级排名
        all_recommendations = []
        for rec_type, rec_data in prioritized_recs.items():
            if isinstance(rec_data, dict):
                for sub_type, sub_data in rec_data.items():
                    if isinstance(sub_data, list):
                        for item in sub_data:
                            if isinstance(item, dict) and 'action' in item:
                                all_recommendations.append({
                                    'category': f"{rec_type}.{sub_type}",
                                    'action': item['action'],
                                    'priority': item.get('priority', 'medium'),
                                    'expected_impact': item.get('expected_impact', 'medium'),
                                    'implementation_time': item.get('implementation_time', '未指定'),
                                    'estimated_effort': item.get('estimated_effort', 'medium')
                                })
        
        # 按优先级和影响排序
        impact_weights = {'low': 1, 'medium': 2, 'high': 3, 'very_high': 4}
        all_recommendations.sort(
            key=lambda x: (
                priority_weights.get(x['priority'], 2),
                impact_weights.get(x['expected_impact'], 2)
            ),
            reverse=True
        )
        
        prioritized_recs['priority_ranking'] = all_recommendations[:10]  # 取前10个
        
        return prioritized_recs
        
    except Exception as e:
        logger.error(f"推荐排序失败: {str(e)}")
        return recommendations

def _generate_analysis_summary(analysis_context, total_faults):
    """生成分析摘要"""
    try:
        summary = {
            'total_faults_analyzed': total_faults,
            'analysis_quality': 'high' if total_faults > 20 else 'medium' if total_faults > 10 else 'low',
            'key_findings': [],
            'data_completeness': {}
        }
        
        # 关键发现
        if 'severity_analysis' in analysis_context:
            severity_data = analysis_context['severity_analysis']
            high_severity_ratio = severity_data.get('high_severity_ratio', 0)
            if high_severity_ratio > 0.3:
                summary['key_findings'].append(f'高严重程度故障占比{high_severity_ratio*100:.1f}%，需要重点关注')
        
        if 'duration_analysis' in analysis_context:
            duration_data = analysis_context['duration_analysis']
            if 'duration_statistics' in duration_data:
                avg_duration = duration_data['duration_statistics'].get('mean_hours', 0)
                if avg_duration > 4:
                    summary['key_findings'].append(f'平均故障处理时长{avg_duration:.1f}小时，存在优化空间')
        
        if 'trend_analysis' in analysis_context:
            trend_data = analysis_context['trend_analysis']
            trend_direction = trend_data.get('trend_direction', 'stable')
            if trend_direction == 'increasing':
                summary['key_findings'].append('故障趋势呈上升态势，需要预防性措施')
            elif trend_direction == 'decreasing':
                summary['key_findings'].append('故障趋势呈下降态势，当前措施有效')
        
        # 数据完整性评估
        completeness_factors = {
            'basic_stats': 'basic_stats' in analysis_context,
            'time_patterns': 'time_patterns' in analysis_context,
            'severity_analysis': 'severity_analysis' in analysis_context,
            'duration_analysis': 'duration_analysis' in analysis_context,
            'root_cause_analysis': 'root_cause_analysis' in analysis_context
        }
        
        completeness_score = sum(completeness_factors.values()) / len(completeness_factors)
        summary['data_completeness'] = {
            'score': round(completeness_score * 100, 1),
            'level': 'excellent' if completeness_score > 0.8 else 'good' if completeness_score > 0.6 else 'fair'
        }
        
        if not summary['key_findings']:
            summary['key_findings'].append('系统运行状态良好，继续保持当前管理水平')
        
        return summary
        
    except Exception as e:
        return {'error': f'分析摘要生成失败: {str(e)}'}

@router.get('/api/recommendations/action_plan', response_model=Dict[str, Any])
async def generate_action_plan(
    plan_type: str = Query("quick_win", regex="^(quick_win|balanced|comprehensive|custom)$"),
    resource_constraint: str = Query("medium", regex="^(low|medium|high|unlimited)$"),
    target_improvement: str = Query("overall", regex="^(overall|reliability|efficiency|cost_reduction)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    生成具体行动计划
    - quick_win: 快速见效计划（优先低成本高收益项目）
    - balanced: 平衡计划（兼顾短期和长期收益）  
    - comprehensive: 全面计划（系统性改进）
    - custom: 定制计划（基于特定需求）
    """
    try:
        logger.info(f"生成行动计划，类型: {plan_type}, 资源约束: {resource_constraint}")
        
        # 获取智能推荐作为基础
        recommendations_response = await intelligent_recommendations(
            recommendation_type="comprehensive",
            priority_level="medium",
            time_horizon="short_term",
            focus_area="all",
            db=db
        )
        
        if not recommendations_response.get('success', False):
            return recommendations_response
        
        recommendations = recommendations_response['recommendations']
        
        # 生成行动计划
        action_plan = await _create_action_plan(
            recommendations, plan_type, resource_constraint, target_improvement
        )
        
        return {
            'success': True,
            'plan_type': plan_type,
            'resource_constraint': resource_constraint,
            'target_improvement': target_improvement,
            'action_plan': action_plan,
            'generated_timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"行动计划生成失败: {str(e)}")
        return {
            'success': False,
            'message': f'行动计划生成失败: {str(e)}'
        }

async def _create_action_plan(recommendations, plan_type, resource_constraint, target_improvement):
    """创建具体行动计划"""
    try:
        # 资源约束权重
        resource_limits = {
            'low': {'max_items': 3, 'max_effort': 'medium'},
            'medium': {'max_items': 6, 'max_effort': 'high'}, 
            'high': {'max_items': 10, 'max_effort': 'very_high'},
            'unlimited': {'max_items': 20, 'max_effort': 'very_high'}
        }
        
        limits = resource_limits.get(resource_constraint, resource_limits['medium'])
        
        # 从推荐中提取所有行动项
        all_actions = []
        
        # 递归提取所有推荐项
        def extract_actions(data, category_prefix=""):
            actions = []
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'priority_ranking':
                        # 优先级排名已经是处理好的格式
                        return value if isinstance(value, list) else []
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and 'action' in item:
                                action = item.copy()
                                action['category'] = f"{category_prefix}.{key}" if category_prefix else key
                                actions.append(action)
                    elif isinstance(value, dict):
                        actions.extend(extract_actions(value, f"{category_prefix}.{key}" if category_prefix else key))
            return actions
        
        all_actions = extract_actions(recommendations)
        
        # 根据计划类型筛选和排序
        if plan_type == "quick_win":
            # 快速见效：优先低成本高收益
            filtered_actions = [
                a for a in all_actions 
                if a.get('estimated_effort') in ['low', 'medium'] and 
                   a.get('expected_impact') in ['medium', 'high']
            ]
            sort_key = lambda x: (
                {'high': 3, 'medium': 2, 'low': 1}.get(x.get('expected_impact', 'medium'), 2),
                -{'low': 1, 'medium': 2, 'high': 3}.get(x.get('estimated_effort', 'medium'), 2)
            )
            
        elif plan_type == "balanced":
            # 平衡计划：兼顾短期和长期
            filtered_actions = all_actions
            sort_key = lambda x: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'medium'), 2),
                {'high': 3, 'medium': 2, 'low': 1}.get(x.get('expected_impact', 'medium'), 2)
            )
            
        elif plan_type == "comprehensive":
            # 全面计划：系统性改进
            filtered_actions = all_actions
            sort_key = lambda x: (
                {'very_high': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.get('expected_impact', 'medium'), 2),
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'medium'), 2)
            )
            
        else:  # custom
            # 基于目标改进筛选
            target_keywords = {
                'reliability': ['可靠性', '预警', '监控', '稳定'],
                'efficiency': ['效率', '时长', '处理', '响应'],
                'cost_reduction': ['成本', '节约', '资源', '投资'],
                'overall': []  # 不筛选
            }
            
            keywords = target_keywords.get(target_improvement, [])
            if keywords:
                filtered_actions = [
                    a for a in all_actions
                    if any(keyword in a.get('action', '').lower() for keyword in keywords)
                ]
            else:
                filtered_actions = all_actions
            
            sort_key = lambda x: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'medium'), 2),
                {'high': 3, 'medium': 2, 'low': 1}.get(x.get('expected_impact', 'medium'), 2)
            )
        
        # 排序并限制数量
        filtered_actions.sort(key=sort_key, reverse=True)
        selected_actions = filtered_actions[:limits['max_items']]
        
        # 生成时间线
        timeline = _create_implementation_timeline(selected_actions)
        
        # 计算资源需求
        resource_summary = _calculate_resource_requirements(selected_actions)
        
        # 生成风险评估
        risk_assessment = _assess_implementation_risks(selected_actions)
        
        return {
            'selected_actions': selected_actions,
            'implementation_timeline': timeline,
            'resource_requirements': resource_summary,
            'risk_assessment': risk_assessment,
            'success_metrics': _define_success_metrics(selected_actions),
            'total_actions': len(selected_actions),
            'estimated_duration': timeline.get('total_duration', '未确定')
        }
        
    except Exception as e:
        return {'error': f'行动计划创建失败: {str(e)}'}

def _create_implementation_timeline(actions):
    """创建实施时间线"""
    try:
        # 时间映射（以周为单位）
        time_to_weeks = {
            '立即执行': 0.5,
            '1周内': 1,
            '1-2周': 1.5,
            '2-4周': 3,
            '1-3周': 2,
            '3-6周': 4.5,
            '2-4个月': 12,
            '3-6个月': 18,
            '4-8个月': 24,
            '6-12个月': 39,
            '6-18个月': 52
        }
        
        timeline = {
            'immediate': [],  # 0-2周
            'short_term': [],  # 2-8周
            'medium_term': [],  # 2-6个月
            'long_term': []  # 6个月以上
        }
        
        total_weeks = 0
        
        for action in actions:
            impl_time = action.get('implementation_time', '未指定')
            weeks = time_to_weeks.get(impl_time, 4)  # 默认4周
            
            action_with_weeks = action.copy()
            action_with_weeks['estimated_weeks'] = weeks
            
            if weeks <= 2:
                timeline['immediate'].append(action_with_weeks)
            elif weeks <= 8:
                timeline['short_term'].append(action_with_weeks)
            elif weeks <= 24:
                timeline['medium_term'].append(action_with_weeks)
            else:
                timeline['long_term'].append(action_with_weeks)
            
            total_weeks = max(total_weeks, weeks)
        
        timeline['total_duration'] = f'{total_weeks}周' if total_weeks < 52 else f'{total_weeks//4:.1f}个月'
        
        return timeline
        
    except Exception as e:
        return {'error': f'时间线创建失败: {str(e)}'}

def _calculate_resource_requirements(actions):
    """计算资源需求"""
    try:
        # 工作量权重（人周）
        effort_weights = {
            'low': 1,
            'medium': 3,
            'high': 8,
            'very_high': 20
        }
        
        total_effort = 0
        effort_distribution = {'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
        priority_distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        
        for action in actions:
            effort = action.get('estimated_effort', 'medium')
            priority = action.get('priority', 'medium')
            
            total_effort += effort_weights.get(effort, 3)
            effort_distribution[effort] = effort_distribution.get(effort, 0) + 1
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        return {
            'total_person_weeks': total_effort,
            'effort_distribution': effort_distribution,
            'priority_distribution': priority_distribution,
            'resource_intensity': 'high' if total_effort > 50 else 'medium' if total_effort > 20 else 'low'
        }
        
    except Exception as e:
        return {'error': f'资源需求计算失败: {str(e)}'}

def _assess_implementation_risks(actions):
    """评估实施风险"""
    try:
        risks = {
            'high_risk_actions': [],
            'resource_conflicts': [],
            'dependencies': [],
            'overall_risk_level': 'low'
        }
        
        high_effort_count = sum(1 for a in actions if a.get('estimated_effort') in ['high', 'very_high'])
        critical_priority_count = sum(1 for a in actions if a.get('priority') == 'critical')
        
        # 高风险行动识别
        for action in actions:
            if (action.get('estimated_effort') == 'very_high' and 
                action.get('expected_impact') == 'high'):
                risks['high_risk_actions'].append({
                    'action': action['action'],
                    'risk_factors': ['高工作量', '高影响期望'],
                    'mitigation': '分阶段实施，增加里程碑检查点'
                })
        
        # 资源冲突风险
        if high_effort_count > 3:
            risks['resource_conflicts'].append('高工作量项目过多，可能导致资源冲突')
        
        if critical_priority_count > 2:
            risks['resource_conflicts'].append('关键优先级项目过多，需要仔细安排时序')
        
        # 总体风险评级
        if high_effort_count > 5 or critical_priority_count > 3:
            risks['overall_risk_level'] = 'high'
        elif high_effort_count > 2 or critical_priority_count > 1:
            risks['overall_risk_level'] = 'medium'
        else:
            risks['overall_risk_level'] = 'low'
        
        return risks
        
    except Exception as e:
        return {'error': f'风险评估失败: {str(e)}'}

def _define_success_metrics(actions):
    """定义成功指标"""
    try:
        metrics = {
            'quantitative_metrics': [],
            'qualitative_metrics': [],
            'milestone_metrics': []
        }
        
        # 基于行动类型定义指标
        action_keywords = {
            '监控': {
                'quantitative': ['监控覆盖率提升至95%', '告警响应时间缩短50%'],
                'qualitative': ['监控系统稳定性改善', '告警准确性提升']
            },
            '效率': {
                'quantitative': ['平均处理时长缩短30%', '自动化处理率提升至80%'],
                'qualitative': ['处理流程标准化程度提升', '用户满意度改善']
            },
            '预防': {
                'quantitative': ['预防性维护覆盖率达到90%', '主动发现故障比例提升至70%'],
                'qualitative': ['系统稳定性明显改善', '故障预防能力增强']
            }
        }
        
        # 通用指标
        metrics['quantitative'].extend([
            '故障总数较基准期下降20%',
            '高严重程度故障比例下降15%',
            '平均故障恢复时间缩短25%'
        ])
        
        metrics['qualitative'].extend([
            '整体系统可靠性提升',
            '运维团队技能水平提高',
            '故障处理流程标准化'
        ])
        
        # 里程碑指标
        metrics['milestone_metrics'].extend([
            '第4周：完成所有立即执行项目',
            '第12周：完成70%短期改进项目',
            '第24周：完成所有中期战略项目'
        ])
        
        return metrics
        
    except Exception as e:
        return {'error': f'成功指标定义失败: {str(e)}'}

# ===============================
# 指标管理和绩效评估 API
# ===============================

@router.get('/api/indicators/management', response_model=Dict[str, Any])
async def get_indicators_management(
    time_period: str = Query('last_30_days', description="统计周期"),
    category: Optional[str] = Query(None, description="指标分类"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指标管理概览
    """
    try:
        logger.info(f"获取指标管理数据: {time_period}, 分类: {category}")
        
        # 计算时间范围
        end_date = datetime.now()
        if time_period == 'last_7_days':
            start_date = end_date - timedelta(days=7)
        elif time_period == 'last_30_days':
            start_date = end_date - timedelta(days=30)
        elif time_period == 'last_90_days':
            start_date = end_date - timedelta(days=90)
        elif time_period == 'last_365_days':
            start_date = end_date - timedelta(days=365)
        elif time_period == 'all_data':
            start_date = datetime(2020, 1, 1)  # 足够早的日期来包含所有数据
        else:
            start_date = end_date - timedelta(days=30)
        
        # 核心指标统计
        query = select(FaultRecord).where(
            FaultRecord.fault_date >= start_date,
            FaultRecord.fault_date <= end_date
        )
        result = await db.execute(query)
        fault_records = result.scalars().all()
        
        # 检查数据可用性
        data_available = len(fault_records) > 0
        
        # 关键绩效指标 (KPIs)
        kpis = await _calculate_fault_kpis(fault_records, start_date, end_date)
        
        # 指标趋势分析
        trend_analysis = await _analyze_indicators_trend(fault_records, start_date, end_date)
        
        # 指标达成率评估
        achievement_rates = await _calculate_achievement_rates(fault_records)
        
        # 风险指标预警
        risk_alerts = await _identify_risk_indicators(fault_records)
        
        # 改进建议
        improvement_suggestions = await _generate_improvement_suggestions(kpis, achievement_rates)
        
        return {
            'time_period': time_period,
            'data_available': data_available,
            'total_records': len(fault_records),
            'date_range': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'kpis': kpis,
            'trend_analysis': trend_analysis,
            'achievement_rates': achievement_rates,
            'risk_alerts': risk_alerts,
            'improvement_suggestions': improvement_suggestions,
            'last_updated': datetime.now().isoformat(),
            # 数据状态信息
            'data_status': {
                'message': '数据正常' if data_available else f'指定时间范围({start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")})内无故障数据',
                'suggestion': '系统运行良好，无故障记录' if data_available else '请尝试扩大时间范围或导入更多数据',
                'action_required': not data_available
            }
        }
        
    except Exception as e:
        logger.error(f"获取指标管理数据失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'error': True,
                'error_type': 'server_error',
                'message': '指标管理数据获取失败',
                'detail': str(e),
                'suggestions': [
                    '请检查数据库连接',
                    '确认FaultRecord表存在',
                    '联系系统管理员'
                ],
                'timestamp': datetime.now().isoformat()
            }
        )

@router.get('/api/performance/evaluation', response_model=Dict[str, Any])
async def get_performance_evaluation(
    evaluation_period: str = Query('monthly', description="评估周期"),
    focus_area: Optional[str] = Query(None, description="重点评估领域"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取绩效评估报告
    """
    try:
        logger.info(f"执行绩效评估: {evaluation_period}, 重点领域: {focus_area}")
        
        # 确定评估时间范围
        end_date = datetime.now()
        if evaluation_period == 'weekly':
            start_date = end_date - timedelta(days=7)
            comparison_start = start_date - timedelta(days=7)
        elif evaluation_period == 'monthly':
            start_date = end_date - timedelta(days=30)
            comparison_start = start_date - timedelta(days=30)
        elif evaluation_period == 'quarterly':
            start_date = end_date - timedelta(days=90)
            comparison_start = start_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
            comparison_start = start_date - timedelta(days=30)
        
        # 当期数据
        current_query = select(FaultRecord).where(
            FaultRecord.fault_date >= start_date,
            FaultRecord.fault_date <= end_date
        )
        current_result = await db.execute(current_query)
        current_records = current_result.scalars().all()
        
        # 对比期数据
        comparison_query = select(FaultRecord).where(
            FaultRecord.fault_date >= comparison_start,
            FaultRecord.fault_date < start_date
        )
        comparison_result = await db.execute(comparison_query)
        comparison_records = comparison_result.scalars().all()
        
        # 绩效指标计算
        current_performance = await _calculate_performance_metrics(current_records, start_date, end_date)
        comparison_performance = await _calculate_performance_metrics(comparison_records, comparison_start, start_date)
        
        # 绩效变化分析
        performance_changes = await _analyze_performance_changes(current_performance, comparison_performance)
        
        # 团队绩效评估
        team_performance = await _evaluate_team_performance(current_records)
        
        # 目标达成评估
        goal_achievement = await _evaluate_goal_achievement(current_performance)
        
        # 绩效排名和基准比较
        benchmarking = await _perform_benchmarking(current_performance)
        
        # 改进行动计划
        action_plans = await _generate_action_plans(performance_changes, goal_achievement)
        
        evaluation_result = {
            'evaluation_period': evaluation_period,
            'date_range': {
                'current_period': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                },
                'comparison_period': {
                    'start': comparison_start.strftime('%Y-%m-%d'),
                    'end': start_date.strftime('%Y-%m-%d')
                }
            },
            'current_performance': current_performance,
            'comparison_performance': comparison_performance,
            'performance_changes': performance_changes,
            'team_performance': team_performance,
            'goal_achievement': goal_achievement,
            'benchmarking': benchmarking,
            'action_plans': action_plans,
            'evaluation_summary': await _generate_evaluation_summary(current_performance, performance_changes, goal_achievement),
            'generated_at': datetime.now().isoformat()
        }
        
        return convert_numpy_types(evaluation_result)
        
    except Exception as e:
        logger.error(f"绩效评估失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'error': True,
                'error_type': 'evaluation_error',
                'message': '绩效评估处理失败',
                'detail': str(e),
                'suggestions': [
                    '检查评估周期参数',
                    '确认数据完整性',
                    '重试或联系技术支持'
                ],
                'timestamp': datetime.now().isoformat()
            }
        )

@router.get('/api/indicators/dashboard', response_model=Dict[str, Any])
async def get_indicators_dashboard(
    dashboard_type: str = Query('comprehensive', description="仪表盘类型"),
    refresh_interval: int = Query(300, description="刷新间隔秒数"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指标管理仪表盘数据
    """
    try:
        logger.info(f"获取指标仪表盘数据: {dashboard_type}")
        
        # 实时指标数据
        realtime_data = await _get_realtime_indicators(db)
        
        # 关键指标趋势
        key_trends = await _get_key_indicator_trends(db)
        
        # 告警和异常
        alerts_and_anomalies = await _get_alerts_and_anomalies(db)
        
        # 绩效摘要
        performance_summary = await _get_performance_summary(db)
        
        # 预测性指标
        predictive_indicators = await _get_predictive_indicators(db)
        
        # 行动项跟踪
        action_tracking = await _get_action_item_tracking(db)
        
        dashboard_result = {
            'dashboard_type': dashboard_type,
            'refresh_interval': refresh_interval,
            'realtime_data': realtime_data,
            'key_trends': key_trends,
            'alerts_and_anomalies': alerts_and_anomalies,
            'performance_summary': performance_summary,
            'predictive_indicators': predictive_indicators,
            'action_tracking': action_tracking,
            'dashboard_config': {
                'auto_refresh': True,
                'alert_threshold': 0.8,
                'trend_periods': ['7d', '30d', '90d']
            },
            'last_updated': datetime.now().isoformat()
        }
        
        return convert_numpy_types(dashboard_result)
        
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")

@router.post('/api/indicators/targets', response_model=Dict[str, Any])
async def set_performance_targets(
    targets_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    设置绩效目标
    """
    try:
        logger.info("设置绩效目标")
        
        # 验证目标数据
        validated_targets = await _validate_performance_targets(targets_data)
        
        # 保存目标设置
        target_records = await _save_performance_targets(validated_targets, db)
        
        # 生成目标追踪计划
        tracking_plan = await _generate_target_tracking_plan(validated_targets)
        
        # 设置自动监控
        monitoring_setup = await _setup_target_monitoring(validated_targets)
        
        return {
            'status': 'success',
            'targets_set': len(validated_targets),
            'target_records': target_records,
            'tracking_plan': tracking_plan,
            'monitoring_setup': monitoring_setup,
            'next_review_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'created_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"设置绩效目标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"设置绩效目标失败: {str(e)}")

# ===============================
# 指标管理辅助函数
# ===============================

async def _calculate_fault_kpis(fault_records, start_date, end_date):
    """计算故障相关KPI"""
    try:
        total_records = len(fault_records)
        if total_records == 0:
            return _get_empty_kpis()
        
        # 基础KPI计算
        high_severity_count = len([f for f in fault_records if f.notification_level in ['A级', '重大', '严重']])
        
        # 计算平均处理时长
        valid_durations = [f.fault_duration_hours for f in fault_records if f.fault_duration_hours]
        avg_resolution_time = np.mean(valid_durations) if valid_durations else 0
        
        # 主动发现率
        proactive_count = len([f for f in fault_records if f.is_proactive_discovery == '是'])
        proactive_rate = (proactive_count / total_records * 100) if total_records > 0 else 0
        
        # 重复故障率（基于故障名称相似性）
        fault_names = [f.fault_name for f in fault_records if f.fault_name]
        unique_faults = len(set(fault_names))
        repeat_rate = ((len(fault_names) - unique_faults) / len(fault_names) * 100) if fault_names else 0
        
        kpis = {
            'fault_volume': {
                'value': total_records,
                'unit': '次',
                'target': 100,  # 示例目标
                'status': 'normal' if total_records <= 100 else 'warning'
            },
            'high_severity_rate': {
                'value': round((high_severity_count / total_records * 100), 2),
                'unit': '%',
                'target': 15.0,
                'status': 'normal' if (high_severity_count / total_records * 100) <= 15 else 'alert'
            },
            'avg_resolution_time': {
                'value': round(avg_resolution_time, 2),
                'unit': '小时',
                'target': 4.0,
                'status': 'normal' if avg_resolution_time <= 4 else 'warning'
            },
            'proactive_discovery_rate': {
                'value': round(proactive_rate, 2),
                'unit': '%',
                'target': 70.0,
                'status': 'good' if proactive_rate >= 70 else 'needs_improvement'
            },
            'repeat_fault_rate': {
                'value': round(repeat_rate, 2),
                'unit': '%',
                'target': 10.0,
                'status': 'normal' if repeat_rate <= 10 else 'alert'
            }
        }
        
        return kpis
        
    except Exception as e:
        logger.error(f"计算KPI失败: {str(e)}")
        return _get_empty_kpis()

async def _analyze_indicators_trend(fault_records, start_date, end_date):
    """分析指标趋势"""
    try:
        # 按天分组统计
        daily_stats = {}
        for record in fault_records:
            date_key = record.fault_date.strftime('%Y-%m-%d') if record.fault_date else 'unknown'
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'count': 0,
                    'high_severity': 0,
                    'total_duration': 0,
                    'proactive': 0
                }
            
            daily_stats[date_key]['count'] += 1
            if record.notification_level in ['A级', '重大', '严重']:
                daily_stats[date_key]['high_severity'] += 1
            if record.fault_duration_hours:
                daily_stats[date_key]['total_duration'] += record.fault_duration_hours
            if record.is_proactive_discovery == '是':
                daily_stats[date_key]['proactive'] += 1
        
        # 计算趋势
        dates = sorted([d for d in daily_stats.keys() if d != 'unknown'])
        if len(dates) < 3:
            return {'trend': 'insufficient_data', 'analysis': '数据不足，无法分析趋势'}
        
        # 故障数量趋势
        fault_counts = [daily_stats[date]['count'] for date in dates[-7:]]  # 最近7天
        fault_trend = 'stable'
        if len(fault_counts) >= 3:
            recent_avg = np.mean(fault_counts[-3:])
            earlier_avg = np.mean(fault_counts[:-3]) if len(fault_counts) > 3 else recent_avg
            if recent_avg > earlier_avg * 1.2:
                fault_trend = 'increasing'
            elif recent_avg < earlier_avg * 0.8:
                fault_trend = 'decreasing'
        
        return {
            'fault_volume_trend': fault_trend,
            'daily_analysis': {
                'peak_day': max(dates, key=lambda d: daily_stats[d]['count']),
                'lowest_day': min(dates, key=lambda d: daily_stats[d]['count']),
                'average_daily_faults': round(np.mean([daily_stats[d]['count'] for d in dates]), 2)
            },
            'severity_trend': await _analyze_severity_trend(daily_stats, dates),
            'duration_trend': await _analyze_duration_trend(daily_stats, dates),
            'proactive_trend': await _analyze_proactive_trend(daily_stats, dates)
        }
        
    except Exception as e:
        logger.error(f"趋势分析失败: {str(e)}")
        return {'error': f'趋势分析失败: {str(e)}'}

async def _calculate_achievement_rates(fault_records):
    """计算指标达成率"""
    try:
        # 预定义目标值
        targets = {
            'fault_volume_monthly': 100,      # 月度故障数量目标
            'high_severity_rate': 15.0,       # 高严重程度故障比例目标（%）
            'avg_resolution_time': 4.0,       # 平均解决时间目标（小时）
            'proactive_discovery_rate': 70.0, # 主动发现率目标（%）
            'repeat_fault_rate': 10.0         # 重复故障率目标（%）
        }
        
        # 计算实际值
        total_faults = len(fault_records)
        high_severity_count = len([f for f in fault_records if f.notification_level in ['A级', '重大', '严重']])
        
        valid_durations = [f.fault_duration_hours for f in fault_records if f.fault_duration_hours]
        avg_duration = np.mean(valid_durations) if valid_durations else 0
        
        proactive_count = len([f for f in fault_records if f.is_proactive_discovery == '是'])
        proactive_rate = (proactive_count / total_faults * 100) if total_faults > 0 else 0
        
        fault_names = [f.fault_name for f in fault_records if f.fault_name]
        unique_faults = len(set(fault_names))
        repeat_rate = ((len(fault_names) - unique_faults) / len(fault_names) * 100) if fault_names else 0
        
        # 计算达成率
        achievements = {
            'fault_volume': {
                'target': targets['fault_volume_monthly'],
                'actual': total_faults,
                'achievement_rate': min(100, (targets['fault_volume_monthly'] - total_faults) / targets['fault_volume_monthly'] * 100) if total_faults <= targets['fault_volume_monthly'] else 0,
                'status': 'achieved' if total_faults <= targets['fault_volume_monthly'] else 'not_achieved'
            },
            'high_severity_rate': {
                'target': targets['high_severity_rate'],
                'actual': round((high_severity_count / total_faults * 100), 2) if total_faults > 0 else 0,
                'achievement_rate': max(0, (targets['high_severity_rate'] - (high_severity_count / total_faults * 100)) / targets['high_severity_rate'] * 100) if total_faults > 0 else 100,
                'status': 'achieved' if (high_severity_count / total_faults * 100 <= targets['high_severity_rate']) else 'not_achieved'
            },
            'avg_resolution_time': {
                'target': targets['avg_resolution_time'],
                'actual': round(avg_duration, 2),
                'achievement_rate': max(0, (targets['avg_resolution_time'] - avg_duration) / targets['avg_resolution_time'] * 100) if avg_duration <= targets['avg_resolution_time'] else 0,
                'status': 'achieved' if avg_duration <= targets['avg_resolution_time'] else 'not_achieved'
            },
            'proactive_discovery_rate': {
                'target': targets['proactive_discovery_rate'],
                'actual': round(proactive_rate, 2),
                'achievement_rate': (proactive_rate / targets['proactive_discovery_rate'] * 100),
                'status': 'achieved' if proactive_rate >= targets['proactive_discovery_rate'] else 'not_achieved'
            }
        }
        
        # 总体达成率
        achieved_count = sum(1 for k, v in achievements.items() if v['status'] == 'achieved')
        overall_achievement = (achieved_count / len(achievements) * 100)
        
        return {
            'overall_achievement_rate': round(overall_achievement, 2),
            'individual_achievements': achievements,
            'summary': {
                'achieved_indicators': achieved_count,
                'total_indicators': len(achievements),
                'improvement_needed': len(achievements) - achieved_count
            }
        }
        
    except Exception as e:
        logger.error(f"达成率计算失败: {str(e)}")
        return {'error': f'达成率计算失败: {str(e)}'}

async def _identify_risk_indicators(fault_records):
    """识别风险指标"""
    try:
        risks = {
            'high_risk_indicators': [],
            'warning_indicators': [],
            'trend_risks': [],
            'operational_risks': []
        }
        
        if len(fault_records) == 0:
            return risks
        
        # 高严重程度故障比例风险
        high_severity_count = len([f for f in fault_records if f.notification_level in ['A级', '重大', '严重']])
        high_severity_rate = (high_severity_count / len(fault_records) * 100)
        
        if high_severity_rate > 20:
            risks['high_risk_indicators'].append({
                'indicator': '高严重程度故障比例',
                'current_value': f'{high_severity_rate:.2f}%',
                'risk_level': 'high',
                'threshold': '20%',
                'recommendation': '立即审查高严重程度故障根因，制定预防措施'
            })
        elif high_severity_rate > 15:
            risks['warning_indicators'].append({
                'indicator': '高严重程度故障比例',
                'current_value': f'{high_severity_rate:.2f}%',
                'risk_level': 'medium',
                'threshold': '15%',
                'recommendation': '关注高严重程度故障趋势，准备应对措施'
            })
        
        # 处理时长风险
        valid_durations = [f.fault_duration_hours for f in fault_records if f.fault_duration_hours and f.fault_duration_hours > 0]
        if valid_durations:
            avg_duration = np.mean(valid_durations)
            max_duration = max(valid_durations)
            
            if avg_duration > 8:
                risks['high_risk_indicators'].append({
                    'indicator': '平均处理时长',
                    'current_value': f'{avg_duration:.2f}小时',
                    'risk_level': 'high',
                    'threshold': '8小时',
                    'recommendation': '立即优化故障处理流程，提升处理效率'
                })
            elif avg_duration > 6:
                risks['warning_indicators'].append({
                    'indicator': '平均处理时长',
                    'current_value': f'{avg_duration:.2f}小时',
                    'risk_level': 'medium',
                    'threshold': '6小时',
                    'recommendation': '审查处理流程，寻找优化机会'
                })
            
            # 极长处理时间预警
            if max_duration > 24:
                risks['operational_risks'].append({
                    'risk': '存在极长处理时间的故障',
                    'details': f'最长处理时间: {max_duration:.2f}小时',
                    'impact': '可能影响服务可用性和用户满意度',
                    'action': '分析长时间故障的根因，建立升级机制'
                })
        
        # 主动发现率风险
        proactive_count = len([f for f in fault_records if f.is_proactive_discovery == '是'])
        proactive_rate = (proactive_count / len(fault_records) * 100)
        
        if proactive_rate < 50:
            risks['high_risk_indicators'].append({
                'indicator': '主动发现率',
                'current_value': f'{proactive_rate:.2f}%',
                'risk_level': 'high',
                'threshold': '50%',
                'recommendation': '加强监控系统建设，提升主动发现能力'
            })
        elif proactive_rate < 70:
            risks['warning_indicators'].append({
                'indicator': '主动发现率',
                'current_value': f'{proactive_rate:.2f}%',
                'risk_level': 'medium',
                'threshold': '70%',
                'recommendation': '继续完善监控和告警系统'
            })
        
        # 故障集中度风险
        fault_dates = [f.fault_date.date() if f.fault_date else None for f in fault_records]
        fault_dates = [d for d in fault_dates if d is not None]
        
        if fault_dates:
            from collections import Counter
            date_counts = Counter(fault_dates)
            max_daily_faults = max(date_counts.values())
            avg_daily_faults = np.mean(list(date_counts.values()))
            
            if max_daily_faults > avg_daily_faults * 3:
                risks['trend_risks'].append({
                    'risk': '故障集中爆发风险',
                    'details': f'单日最高故障数: {max_daily_faults}, 日均: {avg_daily_faults:.1f}',
                    'impact': '可能存在系统性问题或外部因素影响',
                    'action': '分析故障集中日期的共同特征，制定应急预案'
                })
        
        return risks
        
    except Exception as e:
        logger.error(f"风险指标识别失败: {str(e)}")
        return {'error': f'风险指标识别失败: {str(e)}'}

async def _generate_improvement_suggestions(kpis, achievement_rates):
    """生成改进建议"""
    try:
        suggestions = {
            'high_priority_actions': [],
            'medium_priority_actions': [],
            'long_term_improvements': [],
            'resource_requirements': []
        }
        
        # 基于KPI状态生成建议
        for kpi_name, kpi_data in kpis.items():
            if kpi_data.get('status') == 'alert':
                if kpi_name == 'high_severity_rate':
                    suggestions['high_priority_actions'].append({
                        'action': '立即开展高严重程度故障专项治理',
                        'target_kpi': kpi_name,
                        'current_value': kpi_data['value'],
                        'target_value': kpi_data['target'],
                        'timeline': '2周内',
                        'resources': ['技术专家2名', '分析工具', '专项预算']
                    })
                elif kpi_name == 'repeat_fault_rate':
                    suggestions['high_priority_actions'].append({
                        'action': '建立重复故障根因分析机制',
                        'target_kpi': kpi_name,
                        'current_value': kpi_data['value'],
                        'target_value': kpi_data['target'],
                        'timeline': '1个月内',
                        'resources': ['分析团队', '知识库系统', '流程优化工具']
                    })
            
            elif kpi_data.get('status') == 'warning':
                if kpi_name == 'avg_resolution_time':
                    suggestions['medium_priority_actions'].append({
                        'action': '优化故障处理流程，缩短平均解决时间',
                        'target_kpi': kpi_name,
                        'current_value': kpi_data['value'],
                        'target_value': kpi_data['target'],
                        'timeline': '6周内',
                        'resources': ['流程分析师', '自动化工具', '培训资源']
                    })
        
        # 基于达成率生成建议
        if achievement_rates.get('overall_achievement_rate', 0) < 70:
            suggestions['high_priority_actions'].append({
                'action': '启动指标改进专项计划',
                'description': '整体指标达成率偏低，需要综合性改进措施',
                'timeline': '立即开始',
                'success_criteria': '3个月内整体达成率提升至80%以上'
            })
        
        # 长期改进建议
        suggestions['long_term_improvements'].extend([
            {
                'improvement': '建设智能化故障预防体系',
                'description': '利用AI和机器学习技术，提升故障预测和预防能力',
                'timeline': '6-12个月',
                'expected_impact': '主动发现率提升至85%以上，故障总量下降30%'
            },
            {
                'improvement': '构建全面的性能监控平台',
                'description': '实现实时监控、智能告警、自动化响应的一体化平台',
                'timeline': '9-18个月',
                'expected_impact': '故障处理效率提升50%，客户满意度明显改善'
            }
        ])
        
        # 资源需求汇总
        suggestions['resource_requirements'] = [
            '专业技术人员：3-5名高级工程师',
            '技术工具：监控分析平台、自动化工具套件',
            '培训投入：团队技能提升培训',
            '预算支持：工具采购和外部咨询费用'
        ]
        
        return suggestions
        
    except Exception as e:
        logger.error(f"生成改进建议失败: {str(e)}")
        return {'error': f'生成改进建议失败: {str(e)}'}

def _get_empty_kpis():
    """返回空的KPI数据结构"""
    return {
        'fault_volume': {'value': 0, 'unit': '次', 'target': 0, 'status': 'normal'},
        'high_severity_rate': {'value': 0, 'unit': '%', 'target': 15, 'status': 'normal'},
        'avg_resolution_time': {'value': 0, 'unit': '小时', 'target': 4, 'status': 'normal'},
        'proactive_discovery_rate': {'value': 0, 'unit': '%', 'target': 70, 'status': 'needs_improvement'},
        'repeat_fault_rate': {'value': 0, 'unit': '%', 'target': 10, 'status': 'normal'}
    }

# ===============================
# 绩效评估辅助函数
# ===============================

async def _calculate_performance_metrics(fault_records, start_date, end_date):
    """计算绩效指标"""
    try:
        if not fault_records:
            return _get_empty_performance_metrics()
        
        total_faults = len(fault_records)
        
        # 故障严重程度分布
        severity_distribution = {}
        for record in fault_records:
            level = record.notification_level or '未知'
            severity_distribution[level] = severity_distribution.get(level, 0) + 1
        
        # 处理时长统计
        valid_durations = [r.fault_duration_hours for r in fault_records if r.fault_duration_hours and r.fault_duration_hours > 0]
        duration_stats = {
            'average': np.mean(valid_durations) if valid_durations else 0,
            'median': np.median(valid_durations) if valid_durations else 0,
            'max': max(valid_durations) if valid_durations else 0,
            'min': min(valid_durations) if valid_durations else 0,
            'std': np.std(valid_durations) if valid_durations else 0
        }
        
        # 主动/被动发现统计
        proactive_count = len([r for r in fault_records if r.is_proactive_discovery == '是'])
        discovery_metrics = {
            'proactive_count': proactive_count,
            'reactive_count': total_faults - proactive_count,
            'proactive_rate': (proactive_count / total_faults * 100) if total_faults > 0 else 0
        }
        
        # 原因分类统计
        cause_distribution = {}
        for record in fault_records:
            cause = record.cause_category or '未分类'
            cause_distribution[cause] = cause_distribution.get(cause, 0) + 1
        
        # 时间分布分析
        hourly_distribution = [0] * 24
        for record in fault_records:
            if record.start_time:
                hour = record.start_time.hour
                hourly_distribution[hour] += 1
        
        return {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_days': (end_date - start_date).days
            },
            'volume_metrics': {
                'total_faults': total_faults,
                'daily_average': round(total_faults / max(1, (end_date - start_date).days), 2),
                'peak_day_faults': max(hourly_distribution) if hourly_distribution else 0
            },
            'severity_metrics': {
                'distribution': severity_distribution,
                'high_severity_count': severity_distribution.get('A级', 0) + severity_distribution.get('重大', 0) + severity_distribution.get('严重', 0),
                'high_severity_rate': round(((severity_distribution.get('A级', 0) + severity_distribution.get('重大', 0) + severity_distribution.get('严重', 0)) / total_faults * 100), 2) if total_faults > 0 else 0
            },
            'duration_metrics': duration_stats,
            'discovery_metrics': discovery_metrics,
            'cause_metrics': {
                'distribution': cause_distribution,
                'top_causes': sorted(cause_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
            },
            'time_distribution': {
                'hourly': hourly_distribution,
                'peak_hour': hourly_distribution.index(max(hourly_distribution)) if hourly_distribution else 0
            }
        }
        
    except Exception as e:
        logger.error(f"计算绩效指标失败: {str(e)}")
        return _get_empty_performance_metrics()

async def _analyze_performance_changes(current_metrics, comparison_metrics):
    """分析绩效变化"""
    try:
        changes = {
            'volume_change': {},
            'severity_change': {},
            'duration_change': {},
            'discovery_change': {},
            'overall_trend': 'stable'
        }
        
        # 故障量变化
        current_total = current_metrics['volume_metrics']['total_faults']
        comparison_total = comparison_metrics['volume_metrics']['total_faults']
        
        if comparison_total > 0:
            volume_change_rate = ((current_total - comparison_total) / comparison_total * 100)
            changes['volume_change'] = {
                'current': current_total,
                'previous': comparison_total,
                'change_rate': round(volume_change_rate, 2),
                'trend': 'increasing' if volume_change_rate > 5 else 'decreasing' if volume_change_rate < -5 else 'stable'
            }
        
        # 严重程度变化
        current_severity_rate = current_metrics['severity_metrics']['high_severity_rate']
        comparison_severity_rate = comparison_metrics['severity_metrics']['high_severity_rate']
        
        severity_change_rate = current_severity_rate - comparison_severity_rate
        changes['severity_change'] = {
            'current_rate': current_severity_rate,
            'previous_rate': comparison_severity_rate,
            'change': round(severity_change_rate, 2),
            'trend': 'worsening' if severity_change_rate > 2 else 'improving' if severity_change_rate < -2 else 'stable'
        }
        
        # 处理时长变化
        current_avg_duration = current_metrics['duration_metrics']['average']
        comparison_avg_duration = comparison_metrics['duration_metrics']['average']
        
        if comparison_avg_duration > 0:
            duration_change_rate = ((current_avg_duration - comparison_avg_duration) / comparison_avg_duration * 100)
            changes['duration_change'] = {
                'current_avg': round(current_avg_duration, 2),
                'previous_avg': round(comparison_avg_duration, 2),
                'change_rate': round(duration_change_rate, 2),
                'trend': 'worsening' if duration_change_rate > 10 else 'improving' if duration_change_rate < -10 else 'stable'
            }
        
        # 主动发现率变化
        current_proactive_rate = current_metrics['discovery_metrics']['proactive_rate']
        comparison_proactive_rate = comparison_metrics['discovery_metrics']['proactive_rate']
        
        proactive_change = current_proactive_rate - comparison_proactive_rate
        changes['discovery_change'] = {
            'current_rate': round(current_proactive_rate, 2),
            'previous_rate': round(comparison_proactive_rate, 2),
            'change': round(proactive_change, 2),
            'trend': 'improving' if proactive_change > 5 else 'worsening' if proactive_change < -5 else 'stable'
        }
        
        # 整体趋势评估
        positive_changes = 0
        negative_changes = 0
        
        if changes['volume_change'].get('trend') == 'decreasing':
            positive_changes += 1
        elif changes['volume_change'].get('trend') == 'increasing':
            negative_changes += 1
            
        if changes['severity_change']['trend'] == 'improving':
            positive_changes += 1
        elif changes['severity_change']['trend'] == 'worsening':
            negative_changes += 1
            
        if changes['duration_change'].get('trend') == 'improving':
            positive_changes += 1
        elif changes['duration_change'].get('trend') == 'worsening':
            negative_changes += 1
            
        if changes['discovery_change']['trend'] == 'improving':
            positive_changes += 1
        elif changes['discovery_change']['trend'] == 'worsening':
            negative_changes += 1
        
        if positive_changes > negative_changes + 1:
            changes['overall_trend'] = 'improving'
        elif negative_changes > positive_changes + 1:
            changes['overall_trend'] = 'worsening'
        else:
            changes['overall_trend'] = 'stable'
        
        return changes
        
    except Exception as e:
        logger.error(f"分析绩效变化失败: {str(e)}")
        return {'error': f'分析绩效变化失败: {str(e)}'}

async def _evaluate_team_performance(fault_records):
    """评估团队绩效"""
    try:
        team_metrics = {
            'response_efficiency': {},
            'resolution_quality': {},
            'proactive_capability': {},
            'knowledge_application': {}
        }
        
        if not fault_records:
            return team_metrics
        
        # 响应效率评估
        response_times = []
        for record in fault_records:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds() / 3600
                response_times.append(duration)
        
        if response_times:
            avg_response = np.mean(response_times)
            team_metrics['response_efficiency'] = {
                'average_response_time': round(avg_response, 2),
                'fast_response_count': len([t for t in response_times if t <= 2]),  # 2小时内响应
                'fast_response_rate': round(len([t for t in response_times if t <= 2]) / len(response_times) * 100, 2),
                'efficiency_rating': 'excellent' if avg_response < 1 else 'good' if avg_response < 4 else 'needs_improvement'
            }
        
        # 解决质量评估
        high_severity_resolved = len([r for r in fault_records if r.notification_level in ['A级', '重大', '严重'] and r.end_time])
        total_high_severity = len([r for r in fault_records if r.notification_level in ['A级', '重大', '严重']])
        
        team_metrics['resolution_quality'] = {
            'high_severity_resolution_rate': round((high_severity_resolved / max(1, total_high_severity) * 100), 2),
            'repeat_incident_rate': await _calculate_repeat_incident_rate(fault_records),
            'quality_rating': 'excellent' if high_severity_resolved / max(1, total_high_severity) > 0.95 else 'good' if high_severity_resolved / max(1, total_high_severity) > 0.85 else 'needs_improvement'
        }
        
        # 主动能力评估
        proactive_count = len([r for r in fault_records if r.is_proactive_discovery == '是'])
        proactive_rate = (proactive_count / len(fault_records) * 100) if fault_records else 0
        
        team_metrics['proactive_capability'] = {
            'proactive_discovery_count': proactive_count,
            'proactive_discovery_rate': round(proactive_rate, 2),
            'monitoring_effectiveness': 'excellent' if proactive_rate > 75 else 'good' if proactive_rate > 50 else 'needs_improvement'
        }
        
        # 知识应用评估
        cause_variety = len(set([r.cause_category for r in fault_records if r.cause_category]))
        handling_consistency = await _evaluate_handling_consistency(fault_records)
        
        team_metrics['knowledge_application'] = {
            'cause_analysis_diversity': cause_variety,
            'handling_consistency_score': handling_consistency,
            'knowledge_rating': 'excellent' if handling_consistency > 0.8 else 'good' if handling_consistency > 0.6 else 'needs_improvement'
        }
        
        return team_metrics
        
    except Exception as e:
        logger.error(f"团队绩效评估失败: {str(e)}")
        return {'error': f'团队绩效评估失败: {str(e)}'}

async def _evaluate_goal_achievement(performance_metrics):
    """评估目标达成情况"""
    try:
        # 预设目标
        goals = {
            'fault_volume_reduction': {'target': 20, 'unit': '%'},  # 故障数量减少目标
            'high_severity_rate': {'target': 15, 'unit': '%'},      # 高严重程度故障比例目标
            'avg_resolution_time': {'target': 4, 'unit': 'hours'}, # 平均解决时间目标
            'proactive_discovery_rate': {'target': 70, 'unit': '%'} # 主动发现率目标
        }
        
        achievement = {
            'overall_score': 0,
            'individual_goals': {},
            'achieved_count': 0,
            'total_goals': len(goals)
        }
        
        # 评估各项目标
        # 高严重程度故障比例
        current_severity_rate = performance_metrics['severity_metrics']['high_severity_rate']
        severity_achieved = current_severity_rate <= goals['high_severity_rate']['target']
        achievement['individual_goals']['high_severity_rate'] = {
            'target': goals['high_severity_rate']['target'],
            'actual': current_severity_rate,
            'achieved': severity_achieved,
            'score': 100 if severity_achieved else max(0, (goals['high_severity_rate']['target'] - current_severity_rate) / goals['high_severity_rate']['target'] * 100)
        }
        
        # 平均解决时间
        current_avg_duration = performance_metrics['duration_metrics']['average']
        duration_achieved = current_avg_duration <= goals['avg_resolution_time']['target']
        achievement['individual_goals']['avg_resolution_time'] = {
            'target': goals['avg_resolution_time']['target'],
            'actual': round(current_avg_duration, 2),
            'achieved': duration_achieved,
            'score': 100 if duration_achieved else max(0, (goals['avg_resolution_time']['target'] - current_avg_duration) / goals['avg_resolution_time']['target'] * 100)
        }
        
        # 主动发现率
        current_proactive_rate = performance_metrics['discovery_metrics']['proactive_rate']
        proactive_achieved = current_proactive_rate >= goals['proactive_discovery_rate']['target']
        achievement['individual_goals']['proactive_discovery_rate'] = {
            'target': goals['proactive_discovery_rate']['target'],
            'actual': current_proactive_rate,
            'achieved': proactive_achieved,
            'score': min(100, (current_proactive_rate / goals['proactive_discovery_rate']['target'] * 100))
        }
        
        # 计算总体得分
        total_score = sum([goal['score'] for goal in achievement['individual_goals'].values()])
        achievement['overall_score'] = round(total_score / len(achievement['individual_goals']), 2)
        achievement['achieved_count'] = sum([1 for goal in achievement['individual_goals'].values() if goal['achieved']])
        
        # 总体评级
        if achievement['overall_score'] >= 90:
            achievement['overall_rating'] = 'excellent'
        elif achievement['overall_score'] >= 75:
            achievement['overall_rating'] = 'good'
        elif achievement['overall_score'] >= 60:
            achievement['overall_rating'] = 'satisfactory'
        else:
            achievement['overall_rating'] = 'needs_improvement'
        
        return achievement
        
    except Exception as e:
        logger.error(f"目标达成评估失败: {str(e)}")
        return {'error': f'目标达成评估失败: {str(e)}'}

async def _perform_benchmarking(current_performance):
    """进行基准比较"""
    try:
        # 行业基准数据（示例）
        industry_benchmarks = {
            'fault_volume_per_day': 3.5,
            'high_severity_rate': 12.0,
            'avg_resolution_time': 3.8,
            'proactive_discovery_rate': 68.0,
            'customer_satisfaction': 4.2
        }
        
        benchmarking = {
            'industry_comparison': {},
            'performance_ranking': {},
            'improvement_opportunities': []
        }
        
        # 与行业基准比较
        current_daily_avg = current_performance['volume_metrics']['daily_average']
        current_severity_rate = current_performance['severity_metrics']['high_severity_rate']
        current_avg_duration = current_performance['duration_metrics']['average']
        current_proactive_rate = current_performance['discovery_metrics']['proactive_rate']
        
        benchmarking['industry_comparison'] = {
            'fault_volume': {
                'current': current_daily_avg,
                'benchmark': industry_benchmarks['fault_volume_per_day'],
                'performance': 'above_benchmark' if current_daily_avg < industry_benchmarks['fault_volume_per_day'] else 'below_benchmark',
                'gap': round(current_daily_avg - industry_benchmarks['fault_volume_per_day'], 2)
            },
            'severity_rate': {
                'current': current_severity_rate,
                'benchmark': industry_benchmarks['high_severity_rate'],
                'performance': 'above_benchmark' if current_severity_rate < industry_benchmarks['high_severity_rate'] else 'below_benchmark',
                'gap': round(current_severity_rate - industry_benchmarks['high_severity_rate'], 2)
            },
            'resolution_time': {
                'current': current_avg_duration,
                'benchmark': industry_benchmarks['avg_resolution_time'],
                'performance': 'above_benchmark' if current_avg_duration < industry_benchmarks['avg_resolution_time'] else 'below_benchmark',
                'gap': round(current_avg_duration - industry_benchmarks['avg_resolution_time'], 2)
            },
            'proactive_rate': {
                'current': current_proactive_rate,
                'benchmark': industry_benchmarks['proactive_discovery_rate'],
                'performance': 'above_benchmark' if current_proactive_rate > industry_benchmarks['proactive_discovery_rate'] else 'below_benchmark',
                'gap': round(current_proactive_rate - industry_benchmarks['proactive_discovery_rate'], 2)
            }
        }
        
        # 绩效排名评估
        above_benchmark_count = sum(1 for metric in benchmarking['industry_comparison'].values() if metric['performance'] == 'above_benchmark')
        total_metrics = len(benchmarking['industry_comparison'])
        
        ranking_score = (above_benchmark_count / total_metrics * 100)
        
        if ranking_score >= 75:
            ranking_tier = 'top_quartile'
        elif ranking_score >= 50:
            ranking_tier = 'above_average'
        elif ranking_score >= 25:
            ranking_tier = 'below_average'
        else:
            ranking_tier = 'bottom_quartile'
        
        benchmarking['performance_ranking'] = {
            'score': round(ranking_score, 2),
            'tier': ranking_tier,
            'above_benchmark_count': above_benchmark_count,
            'total_metrics': total_metrics
        }
        
        # 改进机会识别
        for metric_name, metric_data in benchmarking['industry_comparison'].items():
            if metric_data['performance'] == 'below_benchmark':
                improvement_potential = abs(metric_data['gap'])
                priority = 'high' if improvement_potential > metric_data['benchmark'] * 0.2 else 'medium'
                
                benchmarking['improvement_opportunities'].append({
                    'metric': metric_name,
                    'current_gap': metric_data['gap'],
                    'improvement_potential': round(improvement_potential, 2),
                    'priority': priority,
                    'recommendation': _get_improvement_recommendation(metric_name, metric_data['gap'])
                })
        
        return benchmarking
        
    except Exception as e:
        logger.error(f"基准比较失败: {str(e)}")
        return {'error': f'基准比较失败: {str(e)}'}

def _get_improvement_recommendation(metric_name, gap):
    """获取改进建议"""
    recommendations = {
        'fault_volume': '通过加强预防性维护和监控系统优化，减少故障发生',
        'severity_rate': '重点关注高严重程度故障的根因分析和预防措施',
        'resolution_time': '优化故障处理流程，提升团队响应效率和技术能力',
        'proactive_rate': '增强监控覆盖范围，提升告警系统的准确性和及时性'
    }
    return recommendations.get(metric_name, '需要制定针对性的改进计划')

def _get_empty_performance_metrics():
    """返回空的绩效指标结构"""
    return {
        'period': {'start_date': '', 'end_date': '', 'total_days': 0},
        'volume_metrics': {'total_faults': 0, 'daily_average': 0, 'peak_day_faults': 0},
        'severity_metrics': {'distribution': {}, 'high_severity_count': 0, 'high_severity_rate': 0},
        'duration_metrics': {'average': 0, 'median': 0, 'max': 0, 'min': 0, 'std': 0},
        'discovery_metrics': {'proactive_count': 0, 'reactive_count': 0, 'proactive_rate': 0},
        'cause_metrics': {'distribution': {}, 'top_causes': []},
        'time_distribution': {'hourly': [0] * 24, 'peak_hour': 0}
    }

# ===============================
# 剩余辅助函数实现
# ===============================

async def _analyze_severity_trend(daily_stats, dates):
    """分析严重程度趋势"""
    try:
        if len(dates) < 2:
            return {'trend': 'insufficient_data'}
        
        severity_rates = []
        for date in dates:
            total = daily_stats[date]['count']
            high_severity = daily_stats[date]['high_severity']
            rate = (high_severity / total * 100) if total > 0 else 0
            severity_rates.append(rate)
        
        # 计算趋势
        recent_avg = np.mean(severity_rates[-3:]) if len(severity_rates) >= 3 else severity_rates[-1]
        earlier_avg = np.mean(severity_rates[:-3]) if len(severity_rates) > 3 else severity_rates[0]
        
        if recent_avg > earlier_avg * 1.2:
            trend = 'worsening'
        elif recent_avg < earlier_avg * 0.8:
            trend = 'improving'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'current_rate': round(recent_avg, 2),
            'previous_rate': round(earlier_avg, 2),
            'change': round(recent_avg - earlier_avg, 2)
        }
        
    except Exception as e:
        return {'trend': 'error', 'message': str(e)}

async def _analyze_duration_trend(daily_stats, dates):
    """分析处理时长趋势"""
    try:
        if len(dates) < 2:
            return {'trend': 'insufficient_data'}
        
        daily_averages = []
        for date in dates:
            total_duration = daily_stats[date]['total_duration']
            count = daily_stats[date]['count']
            avg_duration = total_duration / count if count > 0 else 0
            daily_averages.append(avg_duration)
        
        # 计算趋势
        recent_avg = np.mean(daily_averages[-3:]) if len(daily_averages) >= 3 else daily_averages[-1]
        earlier_avg = np.mean(daily_averages[:-3]) if len(daily_averages) > 3 else daily_averages[0]
        
        if recent_avg > earlier_avg * 1.15:
            trend = 'worsening'
        elif recent_avg < earlier_avg * 0.85:
            trend = 'improving'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'current_avg': round(recent_avg, 2),
            'previous_avg': round(earlier_avg, 2),
            'change': round(recent_avg - earlier_avg, 2)
        }
        
    except Exception as e:
        return {'trend': 'error', 'message': str(e)}

async def _analyze_proactive_trend(daily_stats, dates):
    """分析主动发现趋势"""
    try:
        if len(dates) < 2:
            return {'trend': 'insufficient_data'}
        
        proactive_rates = []
        for date in dates:
            proactive = daily_stats[date]['proactive']
            total = daily_stats[date]['count']
            rate = (proactive / total * 100) if total > 0 else 0
            proactive_rates.append(rate)
        
        # 计算趋势
        recent_avg = np.mean(proactive_rates[-3:]) if len(proactive_rates) >= 3 else proactive_rates[-1]
        earlier_avg = np.mean(proactive_rates[:-3]) if len(proactive_rates) > 3 else proactive_rates[0]
        
        if recent_avg > earlier_avg * 1.1:
            trend = 'improving'
        elif recent_avg < earlier_avg * 0.9:
            trend = 'worsening'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'current_rate': round(recent_avg, 2),
            'previous_rate': round(earlier_avg, 2),
            'change': round(recent_avg - earlier_avg, 2)
        }
        
    except Exception as e:
        return {'trend': 'error', 'message': str(e)}

async def _calculate_repeat_incident_rate(fault_records):
    """计算重复事件率"""
    try:
        if not fault_records:
            return 0
        
        # 基于故障名称的相似性判断重复事件
        fault_names = [r.fault_name.lower() if r.fault_name else '' for r in fault_records]
        fault_names = [name for name in fault_names if name]  # 过滤空名称
        
        if not fault_names:
            return 0
        
        # 简单的重复率计算（基于完全匹配）
        unique_names = set(fault_names)
        repeat_count = len(fault_names) - len(unique_names)
        repeat_rate = (repeat_count / len(fault_names) * 100)
        
        return round(repeat_rate, 2)
        
    except Exception as e:
        logger.error(f"计算重复事件率失败: {str(e)}")
        return 0

async def _evaluate_handling_consistency(fault_records):
    """评估处理一致性"""
    try:
        if not fault_records:
            return 0
        
        # 按故障类型分组，评估处理时间的一致性
        type_groups = {}
        for record in fault_records:
            fault_type = record.province_fault_type or record.cause_category or 'unknown'
            if fault_type not in type_groups:
                type_groups[fault_type] = []
            
            if record.fault_duration_hours:
                type_groups[fault_type].append(record.fault_duration_hours)
        
        # 计算各类型的变异系数
        consistency_scores = []
        for fault_type, durations in type_groups.items():
            if len(durations) >= 2:
                mean_duration = np.mean(durations)
                std_duration = np.std(durations)
                cv = std_duration / mean_duration if mean_duration > 0 else 1
                consistency_score = max(0, 1 - cv)  # 变异系数越小，一致性越高
                consistency_scores.append(consistency_score)
        
        if consistency_scores:
            overall_consistency = np.mean(consistency_scores)
            return round(overall_consistency, 3)
        else:
            return 0.5  # 默认中等一致性
        
    except Exception as e:
        logger.error(f"评估处理一致性失败: {str(e)}")
        return 0.5

async def _generate_action_plans(performance_changes, goal_achievement):
    """生成行动计划"""
    try:
        action_plans = {
            'immediate_actions': [],
            'short_term_plans': [],
            'long_term_strategies': []
        }
        
        # 基于绩效变化生成即时行动
        if performance_changes.get('overall_trend') == 'worsening':
            action_plans['immediate_actions'].append({
                'action': '启动绩效改进紧急响应',
                'description': '针对绩效下降趋势，立即启动根因分析和应对措施',
                'timeline': '48小时内',
                'responsible': '运维团队负责人',
                'success_metric': '阻止绩效进一步恶化'
            })
        
        # 基于具体变化生成行动
        if performance_changes.get('severity_change', {}).get('trend') == 'worsening':
            action_plans['immediate_actions'].append({
                'action': '高严重程度故障专项治理',
                'description': '重点关注和分析高严重程度故障的根因，制定预防措施',
                'timeline': '1周内',
                'responsible': '技术专家团队',
                'success_metric': '高严重程度故障率降低至目标水平'
            })
        
        if performance_changes.get('duration_change', {}).get('trend') == 'worsening':
            action_plans['short_term_plans'].append({
                'plan': '故障处理流程优化',
                'description': '分析处理时长延长的原因，优化响应和处理流程',
                'timeline': '2-4周',
                'phases': ['流程分析', '瓶颈识别', '优化实施', '效果验证'],
                'expected_outcome': '平均处理时长缩短至目标范围'
            })
        
        # 基于目标达成情况生成计划
        overall_score = goal_achievement.get('overall_score', 0)
        if overall_score < 70:
            action_plans['short_term_plans'].append({
                'plan': '综合绩效提升计划',
                'description': '针对未达标的关键指标，制定系统性改进方案',
                'timeline': '1-3个月',
                'focus_areas': ['监控能力提升', '团队技能培训', '工具平台优化'],
                'expected_outcome': '整体目标达成率提升至80%以上'
            })
        
        # 长期战略规划
        action_plans['long_term_strategies'].extend([
            {
                'strategy': '智能化运维体系建设',
                'description': '构建基于AI和大数据的智能运维平台',
                'timeline': '6-12个月',
                'key_components': ['智能监控', '故障预测', '自动化响应', '知识图谱'],
                'investment_requirement': '中高',
                'expected_roi': '显著降低故障率和处理时间'
            },
            {
                'strategy': '团队能力持续提升',
                'description': '建立系统化的技能培训和认证体系',
                'timeline': '持续进行',
                'key_areas': ['故障诊断技能', '新技术掌握', '协作能力', '创新思维'],
                'investment_requirement': '中等',
                'expected_roi': '团队整体能力和效率提升'
            }
        ])
        
        return action_plans
        
    except Exception as e:
        logger.error(f"生成行动计划失败: {str(e)}")
        return {'error': f'生成行动计划失败: {str(e)}'}

async def _generate_evaluation_summary(current_performance, performance_changes, goal_achievement):
    """生成评估总结"""
    try:
        summary = {
            'overall_assessment': '',
            'key_findings': [],
            'performance_highlights': [],
            'areas_for_improvement': [],
            'strategic_recommendations': []
        }
        
        # 总体评估
        overall_score = goal_achievement.get('overall_score', 0)
        overall_trend = performance_changes.get('overall_trend', 'stable')
        
        if overall_score >= 85 and overall_trend == 'improving':
            summary['overall_assessment'] = '绩效表现优秀，各项指标持续改善，运维水平达到先进水平'
        elif overall_score >= 70 and overall_trend in ['stable', 'improving']:
            summary['overall_assessment'] = '绩效表现良好，大部分指标达标，运维能力稳步提升'
        elif overall_score >= 60:
            summary['overall_assessment'] = '绩效表现一般，部分指标需要改进，存在提升空间'
        else:
            summary['overall_assessment'] = '绩效表现不理想，多项指标未达标，需要重点关注和改进'
        
        # 关键发现
        fault_volume = current_performance['volume_metrics']['total_faults']
        severity_rate = current_performance['severity_metrics']['high_severity_rate']
        avg_duration = current_performance['duration_metrics']['average']
        proactive_rate = current_performance['discovery_metrics']['proactive_rate']
        
        summary['key_findings'] = [
            f'评估期内共发生故障 {fault_volume} 次，日均 {current_performance["volume_metrics"]["daily_average"]} 次',
            f'高严重程度故障占比 {severity_rate}%，{"达到预期水平" if severity_rate <= 15 else "高于预期水平"}',
            f'平均处理时长 {avg_duration:.1f} 小时，{"符合目标要求" if avg_duration <= 4 else "超出目标时间"}',
            f'主动发现率 {proactive_rate:.1f}%，{"达到良好水平" if proactive_rate >= 70 else "有待提升"}'
        ]
        
        # 绩效亮点
        if severity_rate <= 12:
            summary['performance_highlights'].append('高严重程度故障控制良好，严重故障比例较低')
        if avg_duration <= 3:
            summary['performance_highlights'].append('故障处理效率高，平均解决时间优于行业标准')
        if proactive_rate >= 75:
            summary['performance_highlights'].append('主动监控能力强，故障预防效果显著')
        
        # 改进领域
        if severity_rate > 15:
            summary['areas_for_improvement'].append('高严重程度故障比例偏高，需要加强预防和根因分析')
        if avg_duration > 6:
            summary['areas_for_improvement'].append('故障处理时长偏长，需要优化响应流程和提升技术能力')
        if proactive_rate < 60:
            summary['areas_for_improvement'].append('主动发现能力不足，需要完善监控系统和告警机制')
        
        # 战略建议
        summary['strategic_recommendations'] = [
            '建立故障预测模型，提升预防性维护能力',
            '完善知识库和经验共享机制，提高处理效率',
            '加强团队技能培训，提升专业能力水平',
            '引入自动化工具，减少人工干预和错误'
        ]
        
        return summary
        
    except Exception as e:
        logger.error(f"生成评估总结失败: {str(e)}")
        return {'error': f'生成评估总结失败: {str(e)}'}

# ===============================
# 仪表盘数据获取函数
# ===============================

async def _get_realtime_indicators(db: AsyncSession):
    """获取实时指标数据"""
    try:
        # 获取最近24小时的故障数据
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        query = select(FaultRecord).where(
            FaultRecord.fault_date >= start_time,
            FaultRecord.fault_date <= end_time
        )
        result = await db.execute(query)
        recent_faults = result.scalars().all()
        
        return {
            'current_fault_count': len(recent_faults),
            'high_severity_count': len([f for f in recent_faults if f.notification_level in ['A级', '重大', '严重']]),
            'active_incidents': len([f for f in recent_faults if not f.end_time]),
            'avg_resolution_time': np.mean([f.fault_duration_hours for f in recent_faults if f.fault_duration_hours]) if recent_faults else 0,
            'proactive_discovery_rate': (len([f for f in recent_faults if f.is_proactive_discovery == '是']) / len(recent_faults) * 100) if recent_faults else 0,
            'last_update': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取实时指标数据失败: {str(e)}")
        return {'error': str(e)}

async def _get_key_indicator_trends(db: AsyncSession):
    """获取关键指标趋势"""
    try:
        # 获取最近30天的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        query = select(FaultRecord).where(
            FaultRecord.fault_date >= start_date,
            FaultRecord.fault_date <= end_date
        )
        result = await db.execute(query)
        fault_records = result.scalars().all()
        
        # 按天分组统计
        daily_trends = {}
        for record in fault_records:
            date_key = record.fault_date.strftime('%Y-%m-%d') if record.fault_date else 'unknown'
            if date_key not in daily_trends:
                daily_trends[date_key] = {
                    'total_count': 0,
                    'high_severity_count': 0,
                    'total_duration': 0,
                    'proactive_count': 0
                }
            
            daily_trends[date_key]['total_count'] += 1
            if record.notification_level in ['A级', '重大', '严重']:
                daily_trends[date_key]['high_severity_count'] += 1
            if record.fault_duration_hours:
                daily_trends[date_key]['total_duration'] += record.fault_duration_hours
            if record.is_proactive_discovery == '是':
                daily_trends[date_key]['proactive_count'] += 1
        
        return {
            'fault_volume_trend': daily_trends,
            'trend_analysis': await _analyze_indicators_trend(fault_records, start_date, end_date),
            'period': '30天'
        }
        
    except Exception as e:
        logger.error(f"获取关键指标趋势失败: {str(e)}")
        return {'error': str(e)}

async def _get_alerts_and_anomalies(db: AsyncSession):
    """获取告警和异常"""
    try:
        # 获取最近7天的数据用于异常检测
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        query = select(FaultRecord).where(
            FaultRecord.fault_date >= start_date,
            FaultRecord.fault_date <= end_date
        )
        result = await db.execute(query)
        recent_faults = result.scalars().all()
        
        alerts = []
        anomalies = []
        
        # 检测异常
        if recent_faults:
            # 故障量异常
            daily_counts = {}
            for fault in recent_faults:
                date_key = fault.fault_date.strftime('%Y-%m-%d') if fault.fault_date else 'unknown'
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
            
            if daily_counts:
                avg_daily = np.mean(list(daily_counts.values()))
                max_daily = max(daily_counts.values())
                
                if max_daily > avg_daily * 2:
                    anomalies.append({
                        'type': '故障量异常',
                        'description': f'单日故障数量 {max_daily} 次，超出平均值 {avg_daily:.1f} 次的2倍',
                        'severity': 'high',
                        'detected_at': datetime.now().isoformat()
                    })
            
            # 处理时长异常
            durations = [f.fault_duration_hours for f in recent_faults if f.fault_duration_hours]
            if durations:
                avg_duration = np.mean(durations)
                max_duration = max(durations)
                
                if max_duration > avg_duration * 3:
                    anomalies.append({
                        'type': '处理时长异常',
                        'description': f'发现超长处理时间故障：{max_duration:.1f}小时，远超平均值 {avg_duration:.1f}小时',
                        'severity': 'medium',
                        'detected_at': datetime.now().isoformat()
                    })
            
            # 严重程度预警
            high_severity_count = len([f for f in recent_faults if f.notification_level in ['A级', '重大', '严重']])
            severity_rate = (high_severity_count / len(recent_faults) * 100)
            
            if severity_rate > 20:
                alerts.append({
                    'type': '高严重程度故障预警',
                    'description': f'高严重程度故障比例 {severity_rate:.1f}% 超出预警阈值 20%',
                    'level': 'critical',
                    'action_required': '立即启动专项分析和改进措施',
                    'triggered_at': datetime.now().isoformat()
                })
        
        return {
            'alerts': alerts,
            'anomalies': anomalies,
            'alert_count': len(alerts),
            'anomaly_count': len(anomalies)
        }
        
    except Exception as e:
        logger.error(f"获取告警和异常失败: {str(e)}")
        return {'error': str(e)}

async def _get_performance_summary(db: AsyncSession):
    """获取绩效摘要"""
    try:
        # 获取最近30天和上个30天的数据进行对比
        current_end = datetime.now()
        current_start = current_end - timedelta(days=30)
        previous_start = current_start - timedelta(days=30)
        
        # 当前期间数据
        current_query = select(FaultRecord).where(
            FaultRecord.fault_date >= current_start,
            FaultRecord.fault_date <= current_end
        )
        current_result = await db.execute(current_query)
        current_faults = current_result.scalars().all()
        
        # 对比期间数据
        previous_query = select(FaultRecord).where(
            FaultRecord.fault_date >= previous_start,
            FaultRecord.fault_date < current_start
        )
        previous_result = await db.execute(previous_query)
        previous_faults = previous_result.scalars().all()
        
        # 计算关键指标
        current_metrics = await _calculate_performance_metrics(current_faults, current_start, current_end)
        previous_metrics = await _calculate_performance_metrics(previous_faults, previous_start, current_start)
        
        # 变化分析
        changes = await _analyze_performance_changes(current_metrics, previous_metrics)
        
        return {
            'current_period': {
                'fault_count': current_metrics['volume_metrics']['total_faults'],
                'high_severity_rate': current_metrics['severity_metrics']['high_severity_rate'],
                'avg_resolution_time': current_metrics['duration_metrics']['average'],
                'proactive_rate': current_metrics['discovery_metrics']['proactive_rate']
            },
            'performance_changes': changes,
            'overall_trend': changes.get('overall_trend', 'stable'),
            'summary_period': '最近30天'
        }
        
    except Exception as e:
        logger.error(f"获取绩效摘要失败: {str(e)}")
        return {'error': str(e)}

async def _get_predictive_indicators(db: AsyncSession):
    """获取预测性指标"""
    try:
        # 基于历史数据预测未来趋势
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # 使用60天数据进行预测
        
        query = select(FaultRecord).where(
            FaultRecord.fault_date >= start_date,
            FaultRecord.fault_date <= end_date
        )
        result = await db.execute(query)
        fault_records = result.scalars().all()
        
        # 简单的预测分析
        predictions = {
            'fault_volume_forecast': {},
            'trend_predictions': {},
            'risk_indicators': {}
        }
        
        if fault_records:
            # 按周统计做预测
            weekly_stats = {}
            for record in fault_records:
                if record.fault_date:
                    week_key = record.fault_date.strftime('%Y-W%U')
                    if week_key not in weekly_stats:
                        weekly_stats[week_key] = {'count': 0, 'high_severity': 0}
                    weekly_stats[week_key]['count'] += 1
                    if record.notification_level in ['A级', '重大', '严重']:
                        weekly_stats[week_key]['high_severity'] += 1
            
            if len(weekly_stats) >= 4:
                recent_weeks = sorted(weekly_stats.keys())[-4:]
                weekly_counts = [weekly_stats[week]['count'] for week in recent_weeks]
                
                # 简单线性预测下周故障数量
                if len(weekly_counts) >= 2:
                    trend = np.mean([weekly_counts[i] - weekly_counts[i-1] for i in range(1, len(weekly_counts))])
                    next_week_forecast = weekly_counts[-1] + trend
                    
                    predictions['fault_volume_forecast'] = {
                        'next_week_predicted': round(max(0, next_week_forecast), 1),
                        'confidence': 'medium',
                        'trend': 'increasing' if trend > 0.5 else 'decreasing' if trend < -0.5 else 'stable'
                    }
                
                # 预测风险指标
                recent_severity_rates = [weekly_stats[week]['high_severity'] / weekly_stats[week]['count'] * 100 
                                       for week in recent_weeks if weekly_stats[week]['count'] > 0]
                
                if recent_severity_rates:
                    avg_severity_rate = np.mean(recent_severity_rates)
                    predictions['risk_indicators'] = {
                        'severity_risk_level': 'high' if avg_severity_rate > 20 else 'medium' if avg_severity_rate > 15 else 'low',
                        'predicted_severity_rate': round(avg_severity_rate, 1),
                        'recommendation': '加强预防措施' if avg_severity_rate > 15 else '保持当前水平'
                    }
        
        return predictions
        
    except Exception as e:
        logger.error(f"获取预测性指标失败: {str(e)}")
        return {'error': str(e)}

async def _get_action_item_tracking(db: AsyncSession):
    """获取行动项跟踪"""
    try:
        # 这里可以集成真实的行动项跟踪系统
        # 目前返回示例数据
        
        action_items = [
            {
                'id': 1,
                'title': '高严重程度故障专项治理',
                'status': 'in_progress',
                'progress': 75,
                'assigned_to': '技术团队',
                'due_date': '2024-01-15',
                'priority': 'high'
            },
            {
                'id': 2,
                'title': '监控系统升级',
                'status': 'planning',
                'progress': 25,
                'assigned_to': '运维团队',
                'due_date': '2024-02-01',
                'priority': 'medium'
            },
            {
                'id': 3,
                'title': '故障处理流程优化',
                'status': 'completed',
                'progress': 100,
                'assigned_to': '流程团队',
                'due_date': '2023-12-31',
                'priority': 'medium'
            }
        ]
        
        return {
            'action_items': action_items,
            'total_items': len(action_items),
            'completed_items': len([item for item in action_items if item['status'] == 'completed']),
            'in_progress_items': len([item for item in action_items if item['status'] == 'in_progress']),
            'overdue_items': len([item for item in action_items if item['status'] != 'completed' and item['due_date'] < datetime.now().strftime('%Y-%m-%d')])
        }
        
    except Exception as e:
        logger.error(f"获取行动项跟踪失败: {str(e)}")
        return {'error': str(e)}

# ===============================
# 目标管理相关函数
# ===============================

async def _validate_performance_targets(targets_data):
    """验证绩效目标数据"""
    try:
        validated_targets = {}
        
        required_fields = ['fault_volume_target', 'high_severity_rate_target', 'avg_resolution_time_target', 'proactive_discovery_rate_target']
        
        for field in required_fields:
            if field in targets_data:
                value = targets_data[field]
                # 基本数据验证
                if isinstance(value, (int, float)) and value >= 0:
                    validated_targets[field] = value
                else:
                    raise ValueError(f'目标 {field} 数值无效')
        
        return validated_targets
        
    except Exception as e:
        logger.error(f"目标数据验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"目标数据验证失败: {str(e)}")

async def _save_performance_targets(targets, db: AsyncSession):
    """保存绩效目标"""
    try:
        # 这里应该将目标保存到数据库
        # 由于没有专门的目标表，这里返回示例响应
        
        target_records = []
        for target_name, target_value in targets.items():
            target_records.append({
                'target_name': target_name,
                'target_value': target_value,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            })
        
        return target_records
        
    except Exception as e:
        logger.error(f"保存绩效目标失败: {str(e)}")
        return []

async def _generate_target_tracking_plan(targets):
    """生成目标追踪计划"""
    try:
        tracking_plan = {
            'review_frequency': 'weekly',
            'tracking_metrics': [],
            'milestone_dates': [],
            'alert_thresholds': {}
        }
        
        for target_name, target_value in targets.items():
            tracking_plan['tracking_metrics'].append({
                'metric': target_name,
                'target': target_value,
                'measurement_method': '系统自动计算',
                'data_source': '故障记录系统'
            })
            
            # 设置告警阈值
            if 'rate' in target_name:
                tracking_plan['alert_thresholds'][target_name] = target_value * 1.2  # 超出20%告警
            else:
                tracking_plan['alert_thresholds'][target_name] = target_value * 0.8  # 低于80%告警
        
        # 里程碑日期
        now = datetime.now()
        tracking_plan['milestone_dates'] = [
            {'date': (now + timedelta(days=30)).strftime('%Y-%m-%d'), 'milestone': '第一次月度评审'},
            {'date': (now + timedelta(days=90)).strftime('%Y-%m-%d'), 'milestone': '季度目标评估'},
            {'date': (now + timedelta(days=180)).strftime('%Y-%m-%d'), 'milestone': '半年度总结评审'}
        ]
        
        return tracking_plan
        
    except Exception as e:
        logger.error(f"生成追踪计划失败: {str(e)}")
        return {}

async def _setup_target_monitoring(targets):
    """设置目标监控"""
    try:
        monitoring_setup = {
            'monitoring_enabled': True,
            'dashboard_widgets': [],
            'automated_reports': {
                'frequency': 'weekly',
                'recipients': ['运维团队', '管理层'],
                'report_format': 'PDF + 邮件摘要'
            },
            'alert_rules': []
        }
        
        # 为每个目标创建监控配置
        for target_name, target_value in targets.items():
            monitoring_setup['dashboard_widgets'].append({
                'widget_type': 'gauge',
                'metric': target_name,
                'target_value': target_value,
                'alert_enabled': True
            })
            
            monitoring_setup['alert_rules'].append({
                'rule_name': f'{target_name}_threshold_alert',
                'condition': f'超出目标值的15%',
                'action': '发送告警邮件给运维团队'
            })
        
        return monitoring_setup
        
    except Exception as e:
        logger.error(f"设置目标监控失败: {str(e)}")
        return {}

# 最后更新日志记录
logger.info("故障分析模块已完成指标管理和绩效评估功能扩展")
