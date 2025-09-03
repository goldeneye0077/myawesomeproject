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
from collections import defaultdict, Counter
from typing import Optional

# 创建路由器
router = APIRouter(prefix="/fault", tags=["故障分析"])

# 配置模板
templates = Jinja2Templates(directory="templates")

@router.get('/dashboard_client')
async def fault_dashboard_client(request: Request):
    """故障分析仪表板主页面（客户端渲染版）"""
    return templates.TemplateResponse('fault_dashboard.html', {'request': request})

# 与侧边栏导航保持一致的别名路由，确保 /fault/dashboard 进入客户端仪表板
@router.get('/dashboard')
async def fault_dashboard_alias(request: Request):
    """故障分析仪表板主页面（别名: /dashboard）"""
    return templates.TemplateResponse('fault_dashboard.html', {'request': request})

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
        case_expr = case([(FaultRecord.is_proactive_discovery == '是', 1)], else_=0)
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
