#!/usr/bin/env python3
"""
故障指标分析模块 - 简化版本
只包含数据管理功能，确保基本功能正常工作
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_, or_, distinct
from db.session import get_db
from db.models import FaultRecord
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import os
import logging
import traceback
from typing import Optional

# 配置日志
logger = logging.getLogger(__name__)
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie, Line, Scatter
from pyecharts.globals import ThemeType
from fault_analysis_helpers import (
    get_distinct_values,
    generate_fault_trend_chart,
    generate_fault_type_pie_chart,
    generate_cause_category_pie_chart,
    generate_duration_analysis_chart,
    generate_monthly_trend_chart,
    calculate_avg_duration,
    calculate_proactive_rate,
    calculate_complaint_count,
    calculate_notification_level_stats
)

# ========== AI智能分析接口，对齐PUE指标分析体验 ==========
import requests
import re

def analyze_and_predict_with_deepseek(df, location=None, max_rounds=2):
    """使用DeepSeek API进行故障数据智能分析和预测"""
    try:
        # 如果数据量过大，限制行数以避免超时
        if len(df) > 50:
            df_sample = df.head(50)
            data_summary = f"数据样本（前50条，共{len(df)}条）"
        else:
            df_sample = df
            data_summary = f"完整数据（共{len(df)}条）"
        
        # 如果没有数据，返回默认分析
        if len(df) == 0:
            return "暂无故障数据进行分析。建议检查筛选条件或数据源。"
        
        api_url = "https://DeepSeek-R1-wzrba.eastus2.models.ai.azure.com/chat/completions"
        api_key = "HyYc4J6EcwlktQLXMcXQJNAtkRgioiqi"
        
        # 简化提示词，减少API负载
        prompt = f"请简要分析以下{('筛选条件：'+location) if location else '全部'}的故障数据（{data_summary}），总结主要规律和趋势：\n{df_sample.to_string(index=False)}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 减少max_tokens和增加超时时间
        payload = {
            "model": "deepseek-reasoner", 
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            return f"AI分析服务暂时不可用（状态码: {response.status_code}），请稍后重试。"
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not content:
            return "AI分析服务返回空结果，请稍后重试。"
        
        # 清洗AI输出
        cleaned_content = re.sub(r'<think>[\s\S]*?</think>', '', content)
        cleaned_content = re.sub(r'^[#>*\-\s]+', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = cleaned_content.replace('*', '').strip()
        
        return cleaned_content if cleaned_content else "AI分析完成，但未生成有效内容。"
        
    except requests.exceptions.Timeout:
        return "AI分析请求超时，请稍后重试。如问题持续，请联系管理员。"
    except requests.exceptions.ConnectionError:
        return "AI分析服务连接失败，请检查网络连接或稍后重试。"
    except Exception as e:
        return f"AI分析过程中出现错误，请稍后重试。错误信息：{str(e)[:100]}"

# 创建路由器
router = APIRouter(prefix="/fault", tags=["故障分析"])

# 配置模板
templates = Jinja2Templates(directory="templates")

# 分页配置
PAGE_SIZE = 10  # 每页显示数量

@router.get("/dashboard", response_class=HTMLResponse)
async def fault_analysis_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    fault_type: str = Query(None, description="故障类型筛选"),
    cause_category: str = Query(None, description="原因分类筛选"),
    notification_level: str = Query(None, description="通报级别筛选"),
    duration_range: str = Query(None, description="处理时长区间筛选: 0-2/2-8/8-24/24+"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    time_range: str = Query(None, description="时间范围(天): 7/30/90/365"),
    page: int = Query(1, ge=1, description="页码")
):
    """故障分析仪表板页面"""
    try:
        # 构建基础查询
        query = select(FaultRecord)
        
        # 应用筛选条件
        if fault_type:
            query = query.where(FaultRecord.province_fault_type == fault_type)
        if cause_category:
            query = query.where(FaultRecord.cause_category == cause_category)
        if notification_level:
            query = query.where(FaultRecord.notification_level == notification_level)
        if duration_range:
            # 处理时长区间筛选
            if duration_range == '0-2':
                query = query.where(FaultRecord.fault_duration_hours <= 2)
            elif duration_range == '2-8':
                query = query.where(FaultRecord.fault_duration_hours > 2, FaultRecord.fault_duration_hours <= 8)
            elif duration_range == '8-24':
                query = query.where(FaultRecord.fault_duration_hours > 8, FaultRecord.fault_duration_hours <= 24)
            elif duration_range == '24+':
                query = query.where(FaultRecord.fault_duration_hours > 24)
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.where(FaultRecord.fault_date >= start_datetime)
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.where(FaultRecord.fault_date <= end_datetime)
        # 若未提供明确的起止日期，则支持 time_range 快捷筛选
        if not start_date and not end_date and time_range:
            try:
                days = int(time_range)
                start_dt = datetime.now() - timedelta(days=days)
                query = query.where(FaultRecord.fault_date >= start_dt)
            except ValueError:
                pass
        
        # 获取总数
        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()
        
        # 分页查询
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = min(max(1, page), pages) if pages > 0 else 1
        
        paged_query = query.order_by(FaultRecord.fault_date.desc()).offset(
            (page - 1) * PAGE_SIZE
        ).limit(PAGE_SIZE)
        
        result = await db.execute(paged_query)
        fault_records = result.scalars().all()
        
        # 优化：只在数据量小于1000时才生成图表和AI分析，否则使用简化版本
        if total <= 1000:
            # 获取所有记录用于统计和图表（不分页）
            all_result = await db.execute(query.order_by(FaultRecord.fault_date.desc()))
            all_fault_records = all_result.scalars().all()
            
            # 生成图表
            trend_chart = generate_fault_trend_chart(all_fault_records)
            fault_type_chart = generate_fault_type_pie_chart(all_fault_records)
            cause_category_chart = generate_cause_category_pie_chart(all_fault_records)
            duration_chart = generate_duration_analysis_chart(all_fault_records)
            monthly_trend_chart = generate_monthly_trend_chart(all_fault_records)
            
            # 计算关键指标
            total_faults = len(all_fault_records)
            avg_duration = calculate_avg_duration(all_fault_records)
            proactive_rate = calculate_proactive_rate(all_fault_records)
            complaint_count = calculate_complaint_count(all_fault_records)
            notification_level_stats = calculate_notification_level_stats(all_fault_records)
            
            # AI分析改为按需加载，页面加载时不调用API
            ai_analysis = "点击上方'开始分析'按钮获取AI智能分析报告"
        else:
            # 大数据量时使用简化版本，只显示基本统计
            trend_chart = "<div style='text-align: center; padding: 40px; color: #666;'>数据量较大，图表已禁用以提高性能</div>"
            fault_type_chart = trend_chart
            cause_category_chart = trend_chart
            duration_chart = trend_chart
            monthly_trend_chart = None
            
            total_faults = total
            avg_duration = "0"
            proactive_rate = "0"
            complaint_count = 0
            notification_level_stats = []
            ai_analysis = "数据量较大，为提高性能，AI分析功能已禁用。请使用筛选条件缩小数据范围。"
        
        # 获取筛选选项（缓存优化）
        fault_types = await get_distinct_values(db, FaultRecord.province_fault_type)
        cause_categories = await get_distinct_values(db, FaultRecord.cause_category)
        notification_levels = await get_distinct_values(db, FaultRecord.notification_level)
        
        return templates.TemplateResponse("fault_analyze.html", {
            "request": request,
            "fault_records": fault_records,
            "total": total,
            "pages": pages,
            "current_page": page,
            "page_size": PAGE_SIZE,
            "current_fault_type": fault_type,
            "current_cause_category": cause_category,
            "current_notification_level": notification_level,
            "current_duration_range": duration_range,
            "current_start_date": start_date,
            "current_end_date": end_date,
            "current_time_range": time_range,
            "fault_types": fault_types,
            "cause_categories": cause_categories,
            "notification_levels": notification_levels,
            "fault_trend_chart": trend_chart,
            "fault_type_pie_chart": fault_type_chart,
            "cause_category_pie_chart": cause_category_chart,
            "duration_analysis_chart": duration_chart,
            "monthly_trend_chart": monthly_trend_chart,
            "total_faults": total_faults,
            "avg_duration": avg_duration,
            "proactive_rate": proactive_rate,
            "complaint_count": complaint_count,
            "notification_level_stats": notification_level_stats,
            "ai_analysis": ai_analysis
        })
        
    except Exception as e:
        logger.error(f"故障分析页面错误: {str(e)}")
        return templates.TemplateResponse("fault_analyze.html", {
            "request": request,
            "error": f"加载数据时出现错误: {str(e)}",
            "fault_records": [],
            "total": 0,
            "pages": 0,
            "current_page": 1,
            "page_size": PAGE_SIZE,
            "fault_types": [],
            "cause_categories": [],
            "notification_levels": [],
            "fault_trend_chart": "",
            "fault_type_pie_chart": "",
            "cause_category_pie_chart": "",
            "duration_analysis_chart": "",
            "monthly_trend_chart": "",
            "total_faults": 0,
            "avg_duration": "0",
            "proactive_rate": "0",
            "complaint_count": 0,
            "notification_level_stats": [],
            "ai_analysis": "分析功能暂时不可用"
        })

@router.get("/detail/{fault_id}")
async def get_fault_detail(fault_id: int, db: AsyncSession = Depends(get_db)):
    """获取故障详细信息"""
    try:
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        return {
            "success": True,
            "data": {
                "id": fault_record.id,
                "fault_date": fault_record.fault_date.strftime('%Y-%m-%d %H:%M:%S') if fault_record.fault_date else None,
                "fault_name": fault_record.fault_name,
                "province_fault_type": fault_record.province_fault_type,
                "cause_category": fault_record.cause_category,
                "notification_level": fault_record.notification_level,
                "fault_duration_hours": round(fault_record.fault_duration_hours, 2) if fault_record.fault_duration_hours is not None else None,
                "complaint_situation": fault_record.complaint_situation,
                "start_time": fault_record.start_time.strftime('%Y-%m-%d %H:%M:%S') if fault_record.start_time else None,
                "end_time": fault_record.end_time.strftime('%Y-%m-%d %H:%M:%S') if fault_record.end_time else None,
                "fault_cause": fault_record.fault_cause,
                "fault_handling": fault_record.fault_handling,
                "is_proactive_discovery": fault_record.is_proactive_discovery,
                "province_cause_category": fault_record.province_cause_category,
                "province_cause_analysis": fault_record.province_cause_analysis,
                "remarks": fault_record.remarks,
                "created_at": fault_record.created_at.strftime('%Y-%m-%d %H:%M:%S') if fault_record.created_at else None,
                "updated_at": fault_record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if fault_record.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取故障详情错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取故障详情失败")

@router.post("/ai_analysis")
async def get_ai_analysis(
    request: Request,
    db: AsyncSession = Depends(get_db),
    fault_type: str = Form(None),
    cause_category: str = Form(None),
    notification_level: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None)
):
    """获取AI分析报告"""
    try:
        # 构建查询条件（与dashboard相同的逻辑）
        query = select(FaultRecord)
        
        if fault_type:
            query = query.where(FaultRecord.province_fault_type == fault_type)
        if cause_category:
            query = query.where(FaultRecord.cause_category == cause_category)
        if notification_level:
            query = query.where(FaultRecord.notification_level == notification_level)
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.where(FaultRecord.fault_date >= start_datetime)
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.where(FaultRecord.fault_date <= end_datetime)
        
        # 获取数据
        result = await db.execute(query.order_by(FaultRecord.fault_date.desc()))
        fault_records = result.scalars().all()
        
        # 生成AI分析 - 使用与PUE页面一致的DeepSeek API
        df_data = []
        for record in fault_records:
            df_data.append({
                "故障日期": record.fault_date.strftime('%Y-%m-%d') if record.fault_date else '',
                "故障名称": record.fault_name or '',
                "故障类型": record.province_fault_type or '',
                "原因分类": record.cause_category or '',
                "通报级别": record.notification_level or '',
                "处理时长(小时)": record.fault_duration_hours or 0,
                "主动发现": record.is_proactive_discovery or '',
                "投诉情况": record.complaint_situation or ''
            })
        import pandas as pd
        df = pd.DataFrame(df_data)
        filter_desc = f"故障类型:{fault_type}" if fault_type else ""
        if cause_category:
            filter_desc += f", 原因分类:{cause_category}"
        if notification_level:
            filter_desc += f", 通报级别:{notification_level}"
        analysis = analyze_and_predict_with_deepseek(df, filter_desc or None)
        
        return {
            "success": True,
            "analysis": analysis,
            "record_count": len(fault_records)
        }
        
    except Exception as e:
        logger.error(f"AI分析错误: {str(e)}")
        return {
            "success": False,
            "error": f"生成分析报告时出现错误: {str(e)}",
            "analysis": "分析功能暂时不可用，请稍后重试。"
        }

@router.get("/ai_analysis")
async def get_ai_analysis_get(
    request: Request,
    db: AsyncSession = Depends(get_db),
    fault_type: str = Query(None, description="故障类型筛选"),
    cause_category: str = Query(None, description="原因分类筛选"),
    notification_level: str = Query(None, description="通报级别筛选"),
    start_date: str = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期(YYYY-MM-DD)"),
    time_range: str = Query(None, description="时间范围(天): 7/30/90/365")
):
    """获取AI分析报告 (GET 方式，支持与页面相同的查询参数)
    前端 `fault_analyze.html` 的 refreshAIAnalysis() 使用 GET + URL 查询参数。
    该端点返回 `ai_analysis` 字段，保持与前端预期一致。
    """
    try:
        # 构建查询条件
        query = select(FaultRecord)

        # 若提供明确的起止日期，优先生效；否则支持 time_range 快捷筛选
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.where(FaultRecord.fault_date >= start_datetime)
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.where(FaultRecord.fault_date <= end_datetime)
        if not start_date and not end_date and time_range:
            try:
                days = int(time_range)
                start_dt = datetime.now() - timedelta(days=days)
                query = query.where(FaultRecord.fault_date >= start_dt)
            except ValueError:
                # 忽略非法的 time_range 值
                pass

        if fault_type:
            query = query.where(FaultRecord.province_fault_type == fault_type)
        if cause_category:
            query = query.where(FaultRecord.cause_category == cause_category)
        if notification_level:
            query = query.where(FaultRecord.notification_level == notification_level)

        # 获取数据
        result = await db.execute(query.order_by(FaultRecord.fault_date.desc()))
        fault_records = result.scalars().all()

        # 生成AI分析 - 使用与PUE页面一致的DeepSeek API
        df_data = []
        for record in fault_records:
            df_data.append({
                "故障日期": record.fault_date.strftime('%Y-%m-%d') if record.fault_date else '',
                "故障名称": record.fault_name or '',
                "故障类型": record.province_fault_type or '',
                "原因分类": record.cause_category or '',
                "通报级别": record.notification_level or '',
                "处理时长(小时)": record.fault_duration_hours or 0,
                "主动发现": record.is_proactive_discovery or '',
                "投诉情况": record.complaint_situation or ''
            })
        import pandas as pd
        df = pd.DataFrame(df_data)
        filter_desc = f"故障类型:{fault_type}" if fault_type else ""
        if cause_category:
            filter_desc += f", 原因分类:{cause_category}"
        if notification_level:
            filter_desc += f", 通报级别:{notification_level}"
        if start_date or end_date:
            filter_desc += f", 时间范围:{start_date or '开始'}-{end_date or '结束'}"
        elif time_range:
            filter_desc += f", 近{time_range}天"
        analysis = analyze_and_predict_with_deepseek(df, filter_desc or None)

        return {
            "success": True,
            "ai_analysis": analysis,  # 前端期望的字段名
            "analysis": analysis,      # 兼容旧字段名
            "record_count": len(fault_records)
        }
    except Exception as e:
        logger.error(f"AI分析(GET)错误: {str(e)}")
        return {
            "success": False,
            "error": f"生成分析报告时出现错误: {str(e)}",
            "ai_analysis": "分析功能暂时不可用，请稍后重试。",
            "analysis": "分析功能暂时不可用，请稍后重试。"
        }

 

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
        
        # 分页查询（按故障日期降序排列）
        paged_query = query.order_by(FaultRecord.fault_date.desc()).offset(
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
        print(f"故障数据管理页面错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# ==================== 数据管理相关路由 ====================

@router.get('/import_fault_data', response_class=HTMLResponse)
async def import_fault_data_page(request: Request):
    """批量导入页面"""
    return templates.TemplateResponse('import_fault_data.html', {'request': request})

@router.get('/add_fault_data', response_class=HTMLResponse)
async def add_fault_data_page(request: Request):
    """添加故障数据页面"""
    return templates.TemplateResponse('add_fault_data.html', {'request': request})

@router.get('/export_fault_data')
async def export_fault_data(db: AsyncSession = Depends(get_db)):
    """导出故障数据"""
    try:
        result = await db.execute(select(FaultRecord).order_by(FaultRecord.created_at.desc()))
        fault_data_list = result.scalars().all()
        
        # 这里可以实现导出逻辑，暂时返回JSON
        return JSONResponse({
            'success': True,
            'message': f'共导出 {len(fault_data_list)} 条记录',
            'count': len(fault_data_list)
        })
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': str(e)
        })

@router.get('/edit_fault_data/{fault_id}', response_class=HTMLResponse)
async def edit_fault_data_page(request: Request, fault_id: int, db: AsyncSession = Depends(get_db)):
    """编辑故障数据页面"""
    try:
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        return templates.TemplateResponse('edit_fault_data.html', {
            'request': request,
            'fault_record': fault_record
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get('/view_fault_data/{fault_id}', response_class=HTMLResponse)
async def view_fault_data_page(request: Request, fault_id: int, db: AsyncSession = Depends(get_db)):
    """查看故障数据详情页面"""
    try:
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        return templates.TemplateResponse('view_fault_data.html', {
            'request': request,
            'fault_record': fault_record
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

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
        
        return RedirectResponse(url="/fault/data", status_code=302)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post('/update_fault_data/{fault_id}')
async def update_fault_data(
    fault_id: int,
    sequence_no: int = Form(...),
    fault_date: str = Form(...),
    fault_name: str = Form(...),
    province_cause_analysis: str = Form(None),
    province_cause_category: str = Form(None),
    province_fault_type: str = Form(None),
    notification_level: str = Form(None),
    cause_category: str = Form(None),
    fault_duration_hours: float = Form(None),
    complaint_situation: str = Form(None),
    start_time: str = Form(None),
    end_time: str = Form(None),
    fault_cause: str = Form(None),
    fault_handling: str = Form(None),
    is_proactive_discovery: str = Form(None),
    remarks: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """更新故障数据"""
    try:
        from datetime import datetime
        
        result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
        fault_record = result.scalar_one_or_none()
        
        if not fault_record:
            raise HTTPException(status_code=404, detail="故障记录不存在")
        
        # 更新字段
        fault_record.sequence_no = sequence_no
        fault_record.fault_date = datetime.fromisoformat(fault_date) if fault_date else None
        fault_record.fault_name = fault_name
        fault_record.province_cause_analysis = province_cause_analysis
        fault_record.province_cause_category = province_cause_category
        fault_record.province_fault_type = province_fault_type
        fault_record.notification_level = notification_level
        fault_record.cause_category = cause_category
        fault_record.fault_duration_hours = fault_duration_hours
        fault_record.complaint_situation = complaint_situation
        fault_record.start_time = datetime.fromisoformat(start_time) if start_time else None
        fault_record.end_time = datetime.fromisoformat(end_time) if end_time else None
        fault_record.fault_cause = fault_cause
        fault_record.fault_handling = fault_handling
        fault_record.is_proactive_discovery = is_proactive_discovery
        fault_record.remarks = remarks
        fault_record.updated_at = datetime.now()
        
        await db.commit()
        
        return RedirectResponse(url="/fault/data", status_code=302)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.post('/batch_delete')
async def batch_delete_fault_data(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """批量删除故障数据"""
    try:
        form_data = await request.form()
        ids = form_data.getlist('ids')
        
        if not ids:
            raise HTTPException(status_code=400, detail="未选择要删除的记录")
        
        # 转换为整数列表
        id_list = [int(id_str) for id_str in ids]
        
        # 查找要删除的记录
        result = await db.execute(
            select(FaultRecord).where(FaultRecord.id.in_(id_list))
        )
        records_to_delete = result.scalars().all()
        
        if not records_to_delete:
            raise HTTPException(status_code=404, detail="未找到要删除的记录")
        
        # 批量删除
        for record in records_to_delete:
            await db.delete(record)
        
        await db.commit()
        
        return RedirectResponse(url="/fault/data", status_code=302)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="无效的ID格式")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")

@router.post('/upload_fault_data')
async def upload_fault_data(
    file: UploadFile = File(...),
    skip_first_row: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """上传并处理Excel文件"""
    try:
        # 检查文件类型
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="仅支持Excel文件(.xlsx, .xls)")
        
        # 读取文件内容
        contents = await file.read()
        
        # 使用pandas读取Excel文件
        df = pd.read_excel(BytesIO(contents))
        
        # 如果需要跳过第一行，则从第二行开始
        if skip_first_row and len(df) > 0:
            df = df.iloc[1:].reset_index(drop=True)
        
        # 定义列名映射（根据实际Excel文件的列名）
        column_mapping = {
            '序号': 'sequence_no',
            '日期': 'fault_date',
            '故障名称': 'fault_name',
            ' 省-故障原因析': 'province_cause_analysis',  # 注意前面有空格，后面缺少"分"字  
            '省-原因分类': 'province_cause_category',
            '省-故障类型': 'province_fault_type',
            '通报级别': 'notification_level',
            '原因分类': 'cause_category',
            '故障处理时长（小时）': 'fault_duration_hours',
            '投诉情况': 'complaint_situation',
            '发生时间': 'start_time',
            '结束时间': 'end_time',
            '故障原因': 'fault_cause',
            '故障处理': 'fault_handling',
            '是否主动发现': 'is_proactive_discovery',  
            '备注': 'remarks'
        }
        
        # 打印调试信息
        print(f"Excel文件列名: {list(df.columns)}")
        print(f"映射后的列名: {list(df.rename(columns=column_mapping).columns)}")
        
        # 重命名列
        df_renamed = df.rename(columns=column_mapping)
        
        # 统计信息
        total_rows = len(df_renamed)
        success_count = 0
        error_count = 0
        duplicate_count = 0
        errors = []
        
        # 逐行处理数据
        for index, row in df_renamed.iterrows():
            try:
                # 创建故障记录对象
                fault_record = FaultRecord()
                
                # 设置字段值
                if 'sequence_no' in row and pd.notna(row['sequence_no']):
                    fault_record.sequence_no = int(row['sequence_no'])
                
                if 'fault_date' in row and pd.notna(row['fault_date']):
                    fault_record.fault_date = pd.to_datetime(row['fault_date'])
                
                if 'fault_name' in row and pd.notna(row['fault_name']):
                    fault_record.fault_name = str(row['fault_name'])
                
                if 'province_cause_analysis' in row and pd.notna(row['province_cause_analysis']):
                    fault_record.province_cause_analysis = str(row['province_cause_analysis'])
                
                if 'province_cause_category' in row and pd.notna(row['province_cause_category']):
                    fault_record.province_cause_category = str(row['province_cause_category'])
                
                if 'province_fault_type' in row and pd.notna(row['province_fault_type']):
                    fault_record.province_fault_type = str(row['province_fault_type'])
                
                if 'notification_level' in row and pd.notna(row['notification_level']):
                    fault_record.notification_level = str(row['notification_level'])
                
                if 'cause_category' in row and pd.notna(row['cause_category']):
                    fault_record.cause_category = str(row['cause_category'])
                
                if 'fault_duration_hours' in row and pd.notna(row['fault_duration_hours']):
                    fault_record.fault_duration_hours = float(row['fault_duration_hours'])
                
                if 'complaint_situation' in row and pd.notna(row['complaint_situation']):
                    fault_record.complaint_situation = str(row['complaint_situation'])
                
                if 'start_time' in row and pd.notna(row['start_time']):
                    fault_record.start_time = pd.to_datetime(row['start_time'])
                
                if 'end_time' in row and pd.notna(row['end_time']):
                    fault_record.end_time = pd.to_datetime(row['end_time'])
                
                if 'fault_cause' in row and pd.notna(row['fault_cause']):
                    fault_record.fault_cause = str(row['fault_cause'])
                
                if 'fault_handling' in row and pd.notna(row['fault_handling']):
                    fault_record.fault_handling = str(row['fault_handling'])
                
                if 'is_proactive_discovery' in row and pd.notna(row['is_proactive_discovery']):
                    fault_record.is_proactive_discovery = str(row['is_proactive_discovery'])
                
                if 'remarks' in row and pd.notna(row['remarks']):
                    fault_record.remarks = str(row['remarks'])
                
                # 设置创建和更新时间
                fault_record.created_at = datetime.now()
                fault_record.updated_at = datetime.now()
                
                # 保存到数据库
                db.add(fault_record)
                await db.flush()  # 立即刷新但不提交
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"第{index + 1}行: {str(e)}")
                continue
        
        # 提交所有成功的记录
        await db.commit()
        
        return JSONResponse({
            'success': True,
            'message': '文件处理完成',
            'total_rows': total_rows,
            'success_count': success_count,
            'error_count': error_count,
            'duplicate_count': duplicate_count,
            'errors': errors[:10]  # 只返回前10个错误
        })
        
    except Exception as e:
        await db.rollback()
        return JSONResponse({
            'success': False,
            'error': f'文件处理失败: {str(e)}',
            'traceback': traceback.format_exc()
        }, status_code=500)
 # Duplicate /fault/dashboard route removed; using the primary implementation above.

 # Duplicate /fault/detail/{fault_id} removed; using the earlier implementation that returns {success, data}.

# AI分析API
# 已移除重复的 AI 分析 GET 端点，统一使用上方的 /fault/ai_analysis (GET) 实现

# 简化的API端点用于测试
@router.get('/api/test')
async def test_connection(db: AsyncSession = Depends(get_db)):
    """测试数据库连接"""
    try:
        result = await db.execute(select(func.count()).select_from(FaultRecord))
        count = result.scalar()
        return JSONResponse({
            'success': True,
            'message': f'数据库连接正常，共有 {count} 条故障记录'
        })
    except Exception as e:
        return JSONResponse({
            'success': False,
            'error': str(e)
        })
