"""
新指标模块模板
请按照此模板创建新的指标模块

使用方法:
1. 复制此文件并重命名为你的指标名称
2. 修改类名、表名和相关业务逻辑
3. 在main.py中注册路由
4. 创建对应的HTML模板
"""

from fastapi import APIRouter, Request, Depends, Query, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, distinct, and_, or_, desc
from typing import Optional, List
from pydantic import BaseModel
import pandas as pd
from io import BytesIO
import json
import logging

# 导入公共组件
from db.session import get_db
from db.models import Base  # 替换为你的数据模型
from common import bi_templates_env
from utils.response import handle_success, handle_error, handle_paginated_success
from utils.exceptions import DatabaseException, ValidationException, FileUploadException
from config import settings

# 创建路由器
router = APIRouter(prefix="/your_indicator", tags=["你的指标名称"])
logger = logging.getLogger(__name__)

# Pydantic模型定义
class YourIndicatorCreate(BaseModel):
    """创建指标数据模型"""
    name: str
    value: float
    category: Optional[str] = None
    description: Optional[str] = None

class YourIndicatorUpdate(BaseModel):
    """更新指标数据模型"""
    name: Optional[str] = None
    value: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None

class YourIndicatorResponse(BaseModel):
    """指标响应模型"""
    id: int
    name: str
    value: float
    category: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str

# 页面路由
@router.get("/", response_class=HTMLResponse)
async def indicator_index(request: Request):
    """指标管理主页面"""
    try:
        return bi_templates_env.TemplateResponse(
            "your_indicator_index.html",  # 需要创建对应模板
            {"request": request}
        )
    except Exception as e:
        logger.error(f"渲染指标主页失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="页面加载失败")

@router.get("/add", response_class=HTMLResponse)
async def show_add_form(request: Request):
    """显示添加指标表单"""
    return bi_templates_env.TemplateResponse(
        "add_your_indicator.html",  # 需要创建对应模板
        {"request": request}
    )

@router.get("/edit/{indicator_id}", response_class=HTMLResponse)
async def show_edit_form(request: Request, indicator_id: int, db: AsyncSession = Depends(get_db)):
    """显示编辑指标表单"""
    try:
        # 获取指标数据 - 替换为你的数据模型
        # result = await db.execute(select(YourModel).where(YourModel.id == indicator_id))
        # indicator = result.scalar_one_or_none()
        # 
        # if not indicator:
        #     raise HTTPException(status_code=404, detail="指标不存在")
        
        return bi_templates_env.TemplateResponse(
            "edit_your_indicator.html",  # 需要创建对应模板
            {"request": request, "indicator": {}}  # 替换为实际数据
        )
    except Exception as e:
        logger.error(f"渲染编辑表单失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="页面加载失败")

@router.get("/analyze", response_class=HTMLResponse)
async def show_analyze_page(request: Request):
    """显示数据分析页面"""
    return bi_templates_env.TemplateResponse(
        "your_indicator_analyze.html",  # 需要创建对应模板
        {"request": request}
    )

# API接口
@router.get("/api/data")
async def get_indicators(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类筛选"),
    db: AsyncSession = Depends(get_db)
):
    """获取指标数据列表（分页）"""
    try:
        # 构建查询 - 替换为你的数据模型查询
        # query = select(YourModel)
        # if search:
        #     query = query.where(YourModel.name.contains(search))
        # if category:
        #     query = query.where(YourModel.category == category)
        
        # 获取总数
        # count_query = select(func.count()).select_from(YourModel)
        # if search:
        #     count_query = count_query.where(YourModel.name.contains(search))
        # if category:
        #     count_query = count_query.where(YourModel.category == category)
        # total = (await db.execute(count_query)).scalar()
        
        # 分页查询
        # offset = (page - 1) * page_size
        # query = query.offset(offset).limit(page_size).order_by(YourModel.created_at.desc())
        # result = await db.execute(query)
        # indicators = result.scalars().all()
        
        # 示例返回数据
        indicators = []
        total = 0
        
        return handle_paginated_success(
            data=indicators,
            total=total,
            page=page,
            page_size=page_size,
            message="查询成功"
        )
    
    except Exception as e:
        logger.error(f"查询指标数据失败: {str(e)}", exc_info=True)
        raise DatabaseException("查询数据失败")

@router.post("/api/create")
async def create_indicator(
    indicator_data: YourIndicatorCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新指标"""
    try:
        # 数据验证
        if not indicator_data.name or not indicator_data.name.strip():
            raise ValidationException("指标名称不能为空")
        
        # 创建数据库记录 - 替换为你的数据模型
        # new_indicator = YourModel(
        #     name=indicator_data.name.strip(),
        #     value=indicator_data.value,
        #     category=indicator_data.category,
        #     description=indicator_data.description
        # )
        # db.add(new_indicator)
        # await db.commit()
        # await db.refresh(new_indicator)
        
        logger.info(f"成功创建指标: {indicator_data.name}")
        return handle_success(
            data={"id": 1},  # 替换为实际ID
            message="指标创建成功"
        )
    
    except ValidationException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建指标失败: {str(e)}", exc_info=True)
        raise DatabaseException("创建指标失败")

@router.put("/api/update/{indicator_id}")
async def update_indicator(
    indicator_id: int,
    indicator_data: YourIndicatorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新指标"""
    try:
        # 查询现有记录 - 替换为你的数据模型
        # result = await db.execute(select(YourModel).where(YourModel.id == indicator_id))
        # indicator = result.scalar_one_or_none()
        # 
        # if not indicator:
        #     raise HTTPException(status_code=404, detail="指标不存在")
        
        # 更新字段
        # if indicator_data.name is not None:
        #     indicator.name = indicator_data.name.strip()
        # if indicator_data.value is not None:
        #     indicator.value = indicator_data.value
        # if indicator_data.category is not None:
        #     indicator.category = indicator_data.category
        # if indicator_data.description is not None:
        #     indicator.description = indicator_data.description
        
        # await db.commit()
        
        logger.info(f"成功更新指标: {indicator_id}")
        return handle_success(message="指标更新成功")
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新指标失败: {str(e)}", exc_info=True)
        raise DatabaseException("更新指标失败")

@router.delete("/api/delete/{indicator_id}")
async def delete_indicator(indicator_id: int, db: AsyncSession = Depends(get_db)):
    """删除指标"""
    try:
        # 查询并删除 - 替换为你的数据模型
        # result = await db.execute(select(YourModel).where(YourModel.id == indicator_id))
        # indicator = result.scalar_one_or_none()
        # 
        # if not indicator:
        #     raise HTTPException(status_code=404, detail="指标不存在")
        # 
        # await db.delete(indicator)
        # await db.commit()
        
        logger.info(f"成功删除指标: {indicator_id}")
        return handle_success(message="指标删除成功")
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除指标失败: {str(e)}", exc_info=True)
        raise DatabaseException("删除指标失败")

@router.post("/api/import")
async def import_data(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """批量导入数据"""
    try:
        # 验证文件格式
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise FileUploadException("仅支持Excel和CSV文件格式")
        
        # 读取文件内容
        contents = await file.read()
        
        # 根据文件类型读取数据
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
        
        # 数据验证和处理
        if df.empty:
            raise ValidationException("文件为空或格式不正确")
        
        # 数据导入逻辑 - 根据你的需求实现
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 创建数据库记录 - 替换为你的业务逻辑
                # new_record = YourModel(
                #     name=row.get('name'),
                #     value=float(row.get('value', 0)),
                #     category=row.get('category'),
                #     description=row.get('description')
                # )
                # db.add(new_record)
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.warning(f"导入第{index+1}行数据失败: {str(e)}")
        
        # await db.commit()
        
        logger.info(f"数据导入完成: 成功{success_count}条, 失败{error_count}条")
        return handle_success(
            data={
                "success_count": success_count,
                "error_count": error_count,
                "total_count": len(df)
            },
            message=f"导入完成，成功{success_count}条，失败{error_count}条"
        )
    
    except (FileUploadException, ValidationException):
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"数据导入失败: {str(e)}", exc_info=True)
        raise FileUploadException("数据导入失败")

@router.get("/api/export")
async def export_data(
    format: str = Query("xlsx", description="导出格式: xlsx, csv"),
    category: Optional[str] = Query(None, description="分类筛选"),
    db: AsyncSession = Depends(get_db)
):
    """导出数据"""
    try:
        # 查询数据 - 替换为你的数据模型
        # query = select(YourModel)
        # if category:
        #     query = query.where(YourModel.category == category)
        # result = await db.execute(query)
        # data = result.scalars().all()
        
        # 转换为DataFrame
        df = pd.DataFrame([])  # 替换为实际数据
        
        # 生成文件
        output = BytesIO()
        filename = f"your_indicator_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format.lower() == "csv":
            df.to_csv(output, index=False, encoding='utf-8-sig')
            filename += ".csv"
            media_type = "text/csv"
        else:
            df.to_excel(output, index=False)
            filename += ".xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        output.seek(0)
        
        return StreamingResponse(
            BytesIO(output.getvalue()),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        logger.error(f"数据导出失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="数据导出失败")

@router.get("/api/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """获取统计数据"""
    try:
        # 统计查询 - 替换为你的数据模型
        # total_count = (await db.execute(select(func.count()).select_from(YourModel))).scalar()
        # category_stats = await db.execute(
        #     select(YourModel.category, func.count())
        #     .group_by(YourModel.category)
        # )
        
        stats = {
            "total_count": 0,  # 替换为实际统计
            "category_distribution": {},
            "recent_additions": 0
        }
        
        return handle_success(
            data=stats,
            message="统计数据获取成功"
        )
    
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}", exc_info=True)
        raise DatabaseException("获取统计数据失败")

# 可选：图表数据接口
@router.get("/api/chart-data")
async def get_chart_data(
    chart_type: str = Query("line", description="图表类型: line, bar, pie"),
    date_range: int = Query(30, description="日期范围(天)"),
    db: AsyncSession = Depends(get_db)
):
    """获取图表数据"""
    try:
        # 根据图表类型和日期范围查询数据
        # 这里需要根据具体业务逻辑实现
        
        chart_data = {
            "labels": [],
            "datasets": [],
            "options": {}
        }
        
        return handle_success(
            data=chart_data,
            message="图表数据获取成功"
        )
    
    except Exception as e:
        logger.error(f"获取图表数据失败: {str(e)}", exc_info=True)
        raise DatabaseException("获取图表数据失败")