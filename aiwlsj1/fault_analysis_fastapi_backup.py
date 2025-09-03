#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障指标分析模块 - FastAPI版本
提供故障数据的分析和可视化功能
"""

from fastapi import APIRouter, Request, Depends, Query, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy import func, extract, and_, or_, distinct
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

@router.get('/dashboard_client_backup')
async def fault_dashboard(request: Request):
    """故障分析仪表板主页面"""
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
        monthly_stats = db.query(
            extract('year', FaultRecord.fault_date).label('year'),
            extract('month', FaultRecord.fault_date).label('month'),
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.fault_date.isnot(None)
        ).group_by(
            extract('year', FaultRecord.fault_date),
            extract('month', FaultRecord.fault_date)
        ).order_by('year', 'month').all()
        
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
async def fault_category_analysis(db: Session = Depends(get_db)):
    """故障分类分析"""
    try:
        # 按原因分类统计
        cause_stats = db.query(
            FaultRecord.cause_category,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.cause_category.isnot(None),
            FaultRecord.cause_category != ''
        ).group_by(FaultRecord.cause_category).all()
        
        # 按故障类型统计
        type_stats = db.query(
            FaultRecord.province_fault_type,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.province_fault_type.isnot(None),
            FaultRecord.province_fault_type != ''
        ).group_by(FaultRecord.province_fault_type).all()
        
        # 按通报级别统计
        level_stats = db.query(
            FaultRecord.notification_level,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.notification_level.isnot(None),
            FaultRecord.notification_level != ''
        ).group_by(FaultRecord.notification_level).all()
        
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
async def fault_duration_analysis(db: Session = Depends(get_db)):
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
                count = db.query(FaultRecord).filter(
                    FaultRecord.fault_duration_hours >= min_hours
                ).count()
            else:
                count = db.query(FaultRecord).filter(
                    and_(
                        FaultRecord.fault_duration_hours >= min_hours,
                        FaultRecord.fault_duration_hours < max_hours
                    )
                ).count()
            
            duration_stats.append({
                'range': range_name,
                'count': count
            })
        
        # 平均处理时长趋势（按月）
        monthly_avg_duration = db.query(
            extract('year', FaultRecord.fault_date).label('year'),
            extract('month', FaultRecord.fault_date).label('month'),
            func.avg(FaultRecord.fault_duration_hours).label('avg_duration')
        ).filter(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.fault_duration_hours.isnot(None)
            )
        ).group_by(
            extract('year', FaultRecord.fault_date),
            extract('month', FaultRecord.fault_date)
        ).order_by('year', 'month').all()
        
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
async def fault_proactive_analysis(db: Session = Depends(get_db)):
    """主动发现分析"""
    try:
        # 主动发现vs被动发现统计
        proactive_stats = db.query(
            FaultRecord.is_proactive_discovery,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.is_proactive_discovery.isnot(None)
        ).group_by(FaultRecord.is_proactive_discovery).all()
        
        # 主动发现率趋势（按月）
        monthly_proactive = db.query(
            extract('year', FaultRecord.fault_date).label('year'),
            extract('month', FaultRecord.fault_date).label('month'),
            func.sum(func.case([(FaultRecord.is_proactive_discovery == '是', 1)], else_=0)).label('proactive_count'),
            func.count(FaultRecord.id).label('total_count')
        ).filter(
            and_(
                FaultRecord.fault_date.isnot(None),
                FaultRecord.is_proactive_discovery.isnot(None)
            )
        ).group_by(
            extract('year', FaultRecord.fault_date),
            extract('month', FaultRecord.fault_date)
        ).order_by('year', 'month').all()
        
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
    db: Session = Depends(get_db)
):
    """获取故障详细列表"""
    try:
        # 构建查询
        query = db.query(FaultRecord)
        
        # 添加筛选条件
        if fault_type:
            query = query.filter(FaultRecord.province_fault_type == fault_type)
        
        if cause_category:
            query = query.filter(FaultRecord.cause_category == cause_category)
        
        # 分页
        total = query.count()
        faults = query.order_by(FaultRecord.fault_date.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
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
                'fault_duration_hours': fault.fault_duration_hours,
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
    db: Session = Depends(get_db)
):
    """故障搜索"""
    try:
        # 在多个字段中搜索
        query = db.query(FaultRecord).filter(
            or_(
                FaultRecord.fault_name.like(f'%{keyword}%'),
                FaultRecord.fault_cause.like(f'%{keyword}%'),
                FaultRecord.fault_handling.like(f'%{keyword}%'),
                FaultRecord.remarks.like(f'%{keyword}%')
            )
        )
        
        faults = query.order_by(FaultRecord.fault_date.desc()).limit(50).all()
        
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
                'fault_duration_hours': fault.fault_duration_hours,
                'is_proactive_discovery': fault.is_proactive_discovery
            })
        
        return JSONResponse({
            'success': True,
            'data': fault_list
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
    db: Session = Depends(get_db)
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
        db.commit()
        
        return RedirectResponse(url='/fault/data', status_code=303)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/edit_fault_data/{fault_id}', response_class=HTMLResponse)
async def edit_fault_data_form(request: Request, fault_id: int, db: Session = Depends(get_db)):
    """编辑故障数据表单页面"""
    fault_record = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
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
    db: Session = Depends(get_db)
):
    """更新故障数据"""
    try:
        fault_record = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
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
        
        db.commit()
        
        return RedirectResponse(url='/fault/data', status_code=303)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/delete_fault_data/{fault_id}')
async def delete_fault_data(fault_id: int, db: Session = Depends(get_db)):
    """删除故障数据"""
    try:
        fault_record = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        db.delete(fault_record)
        db.commit()
        
        return RedirectResponse(url='/fault/data', status_code=303)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/view_fault_data/{fault_id}', response_class=HTMLResponse)
async def view_fault_data(request: Request, fault_id: int, db: Session = Depends(get_db)):
    """查看故障数据详情"""
    fault_record = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
    if not fault_record:
        raise HTTPException(status_code=404, detail="故障记录不存在")
    
    return templates.TemplateResponse(
        'view_fault_data.html',
        {'request': request, 'fault_record': fault_record}
    )
