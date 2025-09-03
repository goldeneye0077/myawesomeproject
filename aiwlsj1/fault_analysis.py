#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障指标分析模块
提供故障数据的分析和可视化功能
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.orm import Session
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

@router.get('/dashboard_legacy')
async def fault_dashboard(request: Request):
    """故障分析仪表板主页面"""
    return templates.TemplateResponse('fault_dashboard.html', {'request': request})

@router.get('/api/overview')
async def fault_overview(db: Session = Depends(get_db)):
    """获取故障概览数据"""
    try:
        # 总故障数
        total_faults = db.query(FaultRecord).count()
        
        # 本月故障数
        current_month = datetime.now().replace(day=1)
        monthly_faults = db.query(FaultRecord).filter(
            FaultRecord.fault_date >= current_month
        ).count()
        
        # 平均处理时长
        avg_duration = db.query(func.avg(FaultRecord.fault_duration_hours)).scalar()
        avg_duration = round(avg_duration, 2) if avg_duration else 0
        
        # 主动发现率
        total_with_discovery = db.query(FaultRecord).filter(
            FaultRecord.is_proactive_discovery.isnot(None)
        ).count()
        
        proactive_count = db.query(FaultRecord).filter(
            FaultRecord.is_proactive_discovery == '是'
        ).count()
        
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

@fault_bp.route('/api/fault/trend')
def fault_trend():
    """获取故障趋势数据"""
    session = Session()
    try:
        # 按月统计故障数量
        monthly_stats = session.query(
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
        
        return jsonify({
            'success': True,
            'data': trend_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@fault_bp.route('/api/fault/category_analysis')
def fault_category_analysis():
    """故障分类分析"""
    session = Session()
    try:
        # 按原因分类统计
        cause_stats = session.query(
            FaultRecord.cause_category,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.cause_category.isnot(None),
            FaultRecord.cause_category != ''
        ).group_by(FaultRecord.cause_category).all()
        
        # 按故障类型统计
        type_stats = session.query(
            FaultRecord.province_fault_type,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.province_fault_type.isnot(None),
            FaultRecord.province_fault_type != ''
        ).group_by(FaultRecord.province_fault_type).all()
        
        # 按通报级别统计
        level_stats = session.query(
            FaultRecord.notification_level,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.notification_level.isnot(None),
            FaultRecord.notification_level != ''
        ).group_by(FaultRecord.notification_level).all()
        
        return jsonify({
            'success': True,
            'data': {
                'cause_category': [{'name': name, 'value': count} for name, count in cause_stats],
                'fault_type': [{'name': name, 'value': count} for name, count in type_stats],
                'notification_level': [{'name': name, 'value': count} for name, count in level_stats]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@fault_bp.route('/api/fault/duration_analysis')
def fault_duration_analysis():
    """故障处理时长分析"""
    session = Session()
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
                count = session.query(FaultRecord).filter(
                    FaultRecord.fault_duration_hours >= min_hours
                ).count()
            else:
                count = session.query(FaultRecord).filter(
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
        monthly_avg_duration = session.query(
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
        
        return jsonify({
            'success': True,
            'data': {
                'duration_distribution': duration_stats,
                'duration_trend': duration_trend
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@fault_bp.route('/api/fault/proactive_analysis')
def fault_proactive_analysis():
    """主动发现分析"""
    session = Session()
    try:
        # 主动发现vs被动发现统计
        proactive_stats = session.query(
            FaultRecord.is_proactive_discovery,
            func.count(FaultRecord.id).label('count')
        ).filter(
            FaultRecord.is_proactive_discovery.isnot(None)
        ).group_by(FaultRecord.is_proactive_discovery).all()
        
        # 主动发现率趋势（按月）
        monthly_proactive = session.query(
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
        
        return jsonify({
            'success': True,
            'data': {
                'proactive_distribution': [{'name': name if name else '未知', 'value': count} for name, count in proactive_stats],
                'proactive_trend': proactive_trend
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@fault_bp.route('/api/fault/detail_list')
def fault_detail_list():
    """获取故障详细列表"""
    session = Session()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # 构建查询
        query = session.query(FaultRecord)
        
        # 添加筛选条件
        fault_type = request.args.get('fault_type')
        if fault_type:
            query = query.filter(FaultRecord.province_fault_type == fault_type)
        
        cause_category = request.args.get('cause_category')
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
        
        return jsonify({
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
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@fault_bp.route('/api/fault/search')
def fault_search():
    """故障搜索"""
    session = Session()
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({'success': False, 'error': '搜索关键词不能为空'})
        
        # 在多个字段中搜索
        query = session.query(FaultRecord).filter(
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
        
        return jsonify({
            'success': True,
            'data': fault_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()
