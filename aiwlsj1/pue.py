from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from typing import Optional, List, Union
from pydantic import BaseModel
import pandas as pd
import statistics
from io import BytesIO
from db.models import PUEData
from common import bi_templates_env  # 使用大屏模板环境
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import distinct, func, and_, or_
from db.session import get_db

router = APIRouter()

# ------------- PUE指标12个月趋势接口 -------------
@router.get("/pue_trend_data")
async def pue_trend_data(location: str, year: str, month: str, db: AsyncSession = Depends(get_db)):
    """返回指定地点截止到 year-month 的近 12 个月 PUE 平均值列表，供弹窗 sparkline 使用"""
    # 计算 12 个日期元组 (year, month) 字符串，最近的在最后
    year_i = int(year)
    month_i = int(month)
    ym_list = []
    for _ in range(12):
        ym_list.append((year_i, month_i))
        month_i -= 1
        if month_i == 0:
            month_i = 12
            year_i -= 1
    ym_list.reverse()
    # 查询对应数据
    q = select(PUEData).where(PUEData.location == location, PUEData.year.in_([str(y) for y, _ in ym_list]))
    result = await db.execute(q)
    rows = result.scalars().all()
    # 聚合同月多条取平均
    agg = {}
    for r in rows:
        key = (int(r.year), int(r.month))
        agg.setdefault(key, []).append(r.pue_value)
    values = []
    labels = []
    for y, m in ym_list:
        labels.append(f"{y}-{m:02d}")
        vals = agg.get((y, m))
        values.append(round(sum(vals)/len(vals), 3) if vals else None)
    return {"months": labels, "values": values}

# ------------------ PUE备注接口 ------------------
from db.models import PUEComment
from fastapi import Body
from pydantic import BaseModel

class CommentIn(BaseModel):
    location: str
    year: str
    month: str
    content: str
    creator: str = ""

@router.get("/pue_comment")
async def get_pue_comments(location: str, year: str, month: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PUEComment).where(PUEComment.location == location, PUEComment.year == year, PUEComment.month == month).order_by(PUEComment.created_at))).scalars().all()
    return {"items": [
        {"id": r.id, "content": r.content, "creator": r.creator, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")} for r in rows
    ]}

@router.post("/pue_comment")
async def add_pue_comment(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    comment = PUEComment(location=str(payload.get('location','')), year=str(payload.get('year','')), month=str(payload.get('month','')), content=payload.get('content',''), creator=payload.get('creator',''))
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"id": comment.id, "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M")}

@router.delete("/pue_comment/{cid}")
async def delete_pue_comment(cid: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(PUEComment, cid)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(row)
    await db.commit()
    return {"success": True}

# ----------------整改记录接口----------------
from db.models import PUERectifyRecord

@router.post("/pue_rectify_record")
async def create_pue_rectify_record(
    drill_down_id: int = Form(...),
    status: str = Form(...),
    description: str = Form(""),
    file: Union[UploadFile, None] = File(None),
    db: AsyncSession = Depends(get_db)):
    """新增整改记录
    接收 multipart/form-data，可携带图片文件。若未指定工单号则自动生成。
    """
    import os, random, string, datetime as dt
    from db.models import PUERectifyRecord

    # 自动生成工单号 PUEYYYYMMDDxxxxxx
    order_no = "PUE" + dt.datetime.utcnow().strftime("%Y%m%d") + "".join(random.choices(string.digits, k=6))

    image_url = ""
    if file and file.filename:
        # 保存到 static/rectify 目录
        save_dir = os.path.join(os.getcwd(), "static", "rectify")
        os.makedirs(save_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        fname = order_no + ext
        save_path = os.path.join(save_dir, fname)
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        image_url = f"/static/rectify/{fname}"

    record = PUERectifyRecord(drill_down_id=drill_down_id, order_no=order_no, status=status, image_url=image_url, description=description)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"success": True, "id": record.id, "order_no": order_no}


@router.get("/pue_rectify_record")
async def get_pue_rectify_record(drill_down_id: int, db: AsyncSession = Depends(get_db)):
    """根据下钻数据ID获取整改记录列表"""
    rows = (await db.execute(select(PUERectifyRecord).where(PUERectifyRecord.drill_down_id == drill_down_id).order_by(PUERectifyRecord.created_at))).scalars().all()
    return {"items": [
        {
            "id": r.id,
            "order_no": r.order_no,
            "status": r.status,
            "image_url": r.image_url,
            "description": r.description,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        } for r in rows
    ]}

@router.post("/pue_rectify_record")
async def add_pue_rectify_record(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """添加整改记录"""
    record = PUERectifyRecord(
        drill_down_id=int(payload.get('drill_down_id', 0)),
        order_no=payload.get('order_no', ''),
        status=payload.get('status', ''),
        image_url=payload.get('image_url', ''),
        description=payload.get('description', '')
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"id": record.id, "created_at": record.created_at.strftime("%Y-%m-%d %H:%M")} 

# ----------------PUE下钻--------------------------------------------------------
from db.models import PUEDrillDownData

# PUE下钻数据管理路由

@router.get("/add_pue_drill_down", response_class=HTMLResponse)
async def add_pue_drill_down_form(request: Request):
    return bi_templates_env.TemplateResponse("add_pue_drill_down.html", {"request": request})

@router.post("/add_pue_drill_down")
async def add_pue_drill_down(
    location: str = Form(...),
    year: str = Form(...),
    month: str = Form(...),
    work_type: str = Form(...),
    work_category: str = Form(...),
    sequence_no: int = Form(...),
    work_object: str = Form(...),
    check_item: str = Form(...),
    operation_method: str = Form(...),
    benchmark_value: str = Form(...),
    execution_standard: str = Form(...),
    execution_status: str = Form(...),
    detailed_situation: str = Form(...),
    quantification_standard: str = Form(...),
    last_month_standard: str = Form(...),
    quantification_unit: str = Form(...),
    executor: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    new_row = PUEDrillDownData(
        location=location,
        year=year,
        month=month,
        work_type=work_type,
        work_category=work_category,
        sequence_no=sequence_no,
        work_object=work_object,
        check_item=check_item,
        operation_method=operation_method,
        benchmark_value=benchmark_value,
        execution_standard=execution_standard,
        execution_status=execution_status,
        detailed_situation=detailed_situation,
        quantification_standard=quantification_standard,
        last_month_standard=last_month_standard,
        quantification_unit=quantification_unit,
        executor=executor
    )
    db.add(new_row)
    await db.commit()
    return RedirectResponse(url="/pue_drill_down_manage", status_code=303)

@router.get("/edit_pue_drill_down/{id}", response_class=HTMLResponse)
async def edit_pue_drill_down_form(request: Request, id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(PUEDrillDownData, id)
    return bi_templates_env.TemplateResponse("edit_pue_drill_down.html", {"request": request, "row": row})

@router.post("/edit_pue_drill_down/{id}")
async def edit_pue_drill_down(
    id: int,
    location: str = Form(...),
    year: str = Form(...),
    month: str = Form(...),
    work_type: str = Form(...),
    work_category: str = Form(...),
    sequence_no: int = Form(...),
    work_object: str = Form(...),
    check_item: str = Form(...),
    operation_method: str = Form(...),
    benchmark_value: str = Form(...),
    execution_standard: str = Form(...),
    execution_status: str = Form(...),
    detailed_situation: str = Form(...),
    quantification_standard: str = Form(...),
    last_month_standard: str = Form(...),
    quantification_unit: str = Form(...),
    executor: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    row = await db.get(PUEDrillDownData, id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    row.location = location
    row.year = year
    row.month = month
    row.work_type = work_type
    row.work_category = work_category
    row.sequence_no = sequence_no
    row.work_object = work_object
    row.check_item = check_item
    row.operation_method = operation_method
    row.benchmark_value = benchmark_value
    row.execution_standard = execution_standard
    row.execution_status = execution_status
    row.detailed_situation = detailed_situation
    row.quantification_standard = quantification_standard
    row.last_month_standard = last_month_standard
    row.quantification_unit = quantification_unit
    row.executor = executor
    await db.commit()
    return RedirectResponse(url="/pue_drill_down_manage", status_code=303)
@router.get("/pue_drill_down_manage", response_class=HTMLResponse)
async def pue_drill_down_manage(request: Request, page: int = 1, location: str = None, year: str = None, month: str = None, db: AsyncSession = Depends(get_db)):
    PAGE_SIZE = 15

    # 下拉列表数据
    result = await db.execute(select(distinct(PUEDrillDownData.location)))
    all_locations = [row[0] for row in result.all()]
    result = await db.execute(select(distinct(PUEDrillDownData.year)))
    all_years = [row[0] for row in result.all()]

    # 构建查询
    query = select(PUEDrillDownData)
    if location:
        query = query.where(PUEDrillDownData.location.like(f"%{location}%"))
    if year:
        query = query.where(PUEDrillDownData.year == year)
    if month:
        query = query.where(PUEDrillDownData.month == month)

    # 统计总数
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    # 分页
    rows = await db.execute(query.order_by(PUEDrillDownData.created_at.desc()).offset((page-1)*PAGE_SIZE).limit(PAGE_SIZE))
    drill_list = rows.scalars().all()

    return bi_templates_env.TemplateResponse(
        "pue_drill_down_manage.html",
        {
            "request": request,
            "drill_list": drill_list,
            "page": page,
            "pages": pages,
            "total": total,
            "all_locations": all_locations,
            "all_years": all_years,
            "current_location": location,
            "current_year": year,
            "current_month": month
        }
    )

@router.get("/delete_pue_drill_down/{id}")
async def delete_pue_drill_down(id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(PUEDrillDownData, id)
    if row:
        await db.delete(row)
        await db.commit()
    return RedirectResponse(url="/pue_drill_down_manage", status_code=303)

@router.post("/pue_drill_down/batch_delete")
async def batch_delete_pue_drill_down(request: Request, db: AsyncSession = Depends(get_db)):
    """批量删除PUE下钻数据"""
    try:
        body = await request.json()
        ids = body.get('ids', [])
        
        if not ids:
            return {"success": False, "message": "未提供要删除的ID列表"}
        
        # 查询要删除的记录
        result = await db.execute(select(PUEDrillDownData).where(PUEDrillDownData.id.in_(ids)))
        items_to_delete = result.scalars().all()
        
        if not items_to_delete:
            return {"success": False, "message": "没有找到要删除的记录"}
        
        # 执行批量删除
        deleted_count = 0
        for item in items_to_delete:
            await db.delete(item)
            deleted_count += 1
        
        await db.commit()
        
        return {"success": True, "deleted_count": deleted_count, "message": f"成功删除 {deleted_count} 条记录"}
        
    except Exception as e:
        await db.rollback()
        return {"success": False, "message": f"删除失败：{str(e)}"}

# Pydantic模型用于API请求和响应
class PUEDataCreate(BaseModel):
    location: str
    month: str
    pue_value: float
    year: str

class PUEDataUpdate(BaseModel):
    location: Optional[str] = None
    month: Optional[str] = None
    pue_value: Optional[float] = None
    year: Optional[str] = None


# PUE数据管理路由
@router.get("/pue_data", response_class=HTMLResponse)
async def pue_data_page(request: Request, page: int = 1, location: str = None, year: str = None, db: AsyncSession = Depends(get_db)):
    """渲染PUE数据页面，支持分页和筛选"""
    PAGE_SIZE = 10
    # 查询所有地点
    result = await db.execute(select(distinct(PUEData.location)))
    all_locations = [row[0] for row in result.all()]
    # 查询所有年份
    result = await db.execute(select(distinct(PUEData.year)))
    all_years = [row[0] for row in result.all()]
    # 构建查询
    query = select(PUEData)
    if location:
        query = query.where(PUEData.location == location)
    if year:
        query = query.where(PUEData.year == year)
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
    paged_query = query.order_by(PUEData.created_at.desc()).offset((page-1)*PAGE_SIZE).limit(PAGE_SIZE)
    result = await db.execute(paged_query)
    pue_data_list = result.scalars().all()
    return bi_templates_env.TemplateResponse(
        "pue_data.html",
        {
            "request": request,
            "pue_data_list": pue_data_list,
            "page": page,
            "pages": pages,
            "total": total,
            "all_locations": all_locations,
            "all_years": all_years,
            "current_location": location,
            "current_year": year
        }
    )

@router.get("/add_pue_data", response_class=HTMLResponse)
async def add_pue_data_form(request: Request):
    """渲染添加PUE数据页面"""
    return bi_templates_env.TemplateResponse(
        "add_pue.html",
        {"request": request}
    )

@router.post("/add_pue_data")
async def add_pue_data(
        location: str = Form(...),
        month: str = Form(...),
        pue_value: float = Form(...),
        year: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """添加新PUE数据"""
    new_data = PUEData(
        location=location,
        month=month,
        pue_value=pue_value,
        year=year
    )
    db.add(new_data)
    await db.commit()
    return RedirectResponse(url="/pue_data", status_code=303)

@router.get("/edit_pue_data/{id}", response_class=HTMLResponse)
async def edit_pue_data_form(request: Request, id: int, db: AsyncSession = Depends(get_db)):
    """渲染编辑PUE数据页面"""
    result = await db.execute(select(PUEData).where(PUEData.id == id))
    pue_data = result.scalar_one_or_none()
    return bi_templates_env.TemplateResponse(
        "edit_pue.html",
        {"request": request, "pue_data": pue_data}
    )

@router.post("/edit_pue_data/{id}")
async def edit_pue_data(
        id: int,
        location: str = Form(...),
        month: str = Form(...),
        pue_value: float = Form(...),
        year: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """更新PUE数据信息"""
    result = await db.execute(select(PUEData).where(PUEData.id == id))
    pue_data = result.scalar_one_or_none()
    if pue_data is None:
        raise HTTPException(status_code=404, detail="PUE数据不存在")
    pue_data.location = location
    pue_data.month = month
    pue_data.pue_value = pue_value
    pue_data.year = year
    await db.commit()
    return RedirectResponse(url="/pue_data", status_code=303)

@router.get("/delete_pue_data/{id}")
async def delete_pue_data(id: int, db: AsyncSession = Depends(get_db)):
    """删除PUE数据"""
    result = await db.execute(select(PUEData).where(PUEData.id == id))
    pue_data = result.scalar_one_or_none()
    if pue_data is None:
        raise HTTPException(status_code=404, detail="PUE数据不存在")
    await db.delete(pue_data)
    await db.commit()
    return RedirectResponse(url="/pue_data", status_code=303)

@router.post("/pue_data/batch_delete")
async def batch_delete_pue_data(request: Request, db: AsyncSession = Depends(get_db)):
    """批量删除PUE数据"""
    try:
        body = await request.json()
        ids = body.get('ids', [])
        
        if not ids:
            return {"success": False, "message": "未提供要删除的ID列表"}
        
        # 查询要删除的记录
        result = await db.execute(select(PUEData).where(PUEData.id.in_(ids)))
        items_to_delete = result.scalars().all()
        
        if not items_to_delete:
            return {"success": False, "message": "没有找到要删除的记录"}
        
        # 执行批量删除
        deleted_count = 0
        for item in items_to_delete:
            await db.delete(item)
            deleted_count += 1
        
        await db.commit()
        
        return {"success": True, "deleted_count": deleted_count, "message": f"成功删除 {deleted_count} 条记录"}
        
    except Exception as e:
        await db.rollback()
        return {"success": False, "message": f"删除失败：{str(e)}"}

@router.get("/download_pue_template")
async def download_pue_template():
    """生成并下载PUE数据Excel模板"""
    data = {
        '地点': ['机房A', '机房B'],
        '月份': ['1', '2'],
        'PUE值': [1.45, 1.38],
        '年份': ['2025', '2025']
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='PUE数据')
        worksheet = writer.sheets['PUE数据']
        for i, col in enumerate(df.columns):
            max_length = max(
                len(str(col)),
                df[col].astype(str).map(len).max()
            )
            worksheet.column_dimensions[worksheet.cell(1, i + 1).column_letter].width = max_length + 4
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=pue_data_template.xlsx"}
    )

@router.post("/upload-pue-excel")
async def upload_pue_excel(file: UploadFile = File(...)):
    """从Excel文件批量导入PUE数据"""
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="仅支持Excel文件格式（.xls, .xlsx）")
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        required_columns = ['地点', '月份', 'PUE值', '年份']
        col_mapping = {}
        for req_col in required_columns:
            if req_col in df.columns:
                col_mapping[req_col] = req_col
                continue
            for col in df.columns:
                if req_col in col:
                    col_mapping[req_col] = col
                    break
            if req_col not in col_mapping:
                raise HTTPException(
                    status_code=400,
                    detail=f"Excel文件缺少必要的列: {req_col}"
                )
        for _, row in df.iterrows():
            try:
                pue_value = float(row[col_mapping['PUE值']])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"PUE值必须是有效的数字"
                )
            await PUEData.create(
                location=str(row[col_mapping['地点']]),
                month=str(row[col_mapping['月份']]),
                pue_value=pue_value,
                year=str(row[col_mapping['年份']])
            )
        return RedirectResponse(url="/pue_data", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

# PUE数据API端点
@router.get("/api/pue_data", response_model=List[dict])
async def get_all_pue_data():
    """获取所有PUE数据"""
    return await PUEData.all().values()

@router.get("/api/pue_data/{id}", response_model=dict)
async def get_pue_data(id: int):
    """获取单个PUE数据"""
    return await PUEData.get(id=id).values()

@router.post("/api/pue_data", status_code=201)
async def create_pue_data(pue_data: PUEDataCreate):
    """创建新PUE数据"""
    obj = await PUEData.create(**pue_data.dict())
    return await PUEData.get(id=obj.id).values()

@router.put("/api/pue_data/{id}")
async def update_pue_data_api(id: int, pue_data: PUEDataUpdate):
    """更新PUE数据"""
    await PUEData.filter(id=id).update(**{k: v for k, v in pue_data.dict().items() if v is not None})
    return await PUEData.get(id=id).values()

@router.delete("/api/pue_data/{id}", status_code=204)
async def delete_pue_data_api(id: int):
    """删除PUE数据"""
    await PUEData.filter(id=id).delete()
    return None

@router.get("/pue_analyze", response_class=HTMLResponse)
async def pue_analyze(request: Request, location: str = None, date_range: str = None, period: str = None, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    
    # 初始化所有必需的变量为默认值，防止模板渲染错误
    key_metrics = {
        "current_month_pue": None,
        "monthly_change": None,
        "yearly_change": None,
        "year_avg_pue": None,
        "best_location": "-",
        "best_pue": None,
        "worst_location": "-",
        "worst_pue": None,
        "compliance_rate": 0,
        "energy_savings": 0,
        "carbon_reduction": 0,
        "current_month": ""
    }
    heatmap_html = ""
    radar_html = ""
    chart_html = ""
    line_chart_html = ""
    all_locations = []
    table_data = []
    locations = []
    years = []
    months = []
    multi_table = {}
    red_months = []
    yellow_months = []
    green_months = []
    
    try:
        # 获取所有地点
        result = await db.execute(select(distinct(PUEData.location)))
        all_locations = [row[0] for row in result.all()]
        now = datetime.now()
        this_year = str(now.year)
        last_year = str(now.year - 1)
        
        # 根据日期范围参数确定数据筛选条件
        from datetime import timedelta
        if date_range == 'last6months':
            # 近6个月
            start_date = now - timedelta(days=180)
            query_filter = and_(
                PUEData.year >= str(start_date.year),
                or_(
                    PUEData.year > str(start_date.year),
                    PUEData.month >= str(start_date.month)
                )
            )
            months = [str(i) for i in range(max(1, start_date.month), 13)]
            if start_date.year < now.year:
                months.extend([str(i) for i in range(1, now.month + 1)])
        elif date_range == 'last12months':
            # 近12个月
            start_date = now - timedelta(days=365)
            query_filter = and_(
                PUEData.year >= str(start_date.year),
                or_(
                    PUEData.year > str(start_date.year),
                    PUEData.month >= str(start_date.month)
                )
            )
            months = [str(i) for i in range(max(1, start_date.month), 13)]
            if start_date.year < now.year:
                months.extend([str(i) for i in range(1, now.month + 1)])
        else:
            # 默认：当前年度
            query_filter = PUEData.year == this_year
            months = [str(i) for i in range(1, 13)]
        
        # 处理period参数，调整月份和x轴显示
        if period == "quarter":
            # 季度视图：显示Q1-Q4所有季度，即使某些季度没有数据
            quarter_months = ['3', '6', '9', '12']
            months = quarter_months
            x_axis = [f"Q{(int(m)-1)//3 + 1}" for m in months]
        elif period == "year":
            # 年度视图：只显示年末数据（12月）
            months = ['12']
            x_axis = [f"{this_year}年"]
        else:
            # 默认月度视图
            x_axis = [f"{m}月" for m in months]
        # -- 关键：无论 location 参数如何，折线图都用全市数据 --
        # 1. 查询全量数据用于全市折线（应用日期范围筛选）
        all_pue_data = await db.execute(select(PUEData).where(query_filter))
        all_pue_data = all_pue_data.scalars().all()
        all_locations_set = sorted(set([p.location for p in all_pue_data]))
        years = [last_year, this_year]
        multi_table_all = {m: {loc: {y: None for y in years} for loc in all_locations_set} for m in months}
        for p in all_pue_data:
            if p.year in years and p.location in all_locations_set and p.month in months:
                multi_table_all[p.month][p.location][p.year] = p.pue_value
        city_avg = {}
        for m in months:
            vals = [multi_table_all[m][loc][this_year] for loc in all_locations_set if loc != '全市' and multi_table_all[m][loc][this_year] is not None]
            city_avg[m] = round(sum(vals)/len(vals), 3) if vals else None
        city_line_months = months.copy()
        city_line_values = []
        for m in city_line_months:
            over_count = 0
            total_count = 0
            for loc in all_locations_set:
                this_v = multi_table_all[m][loc][this_year]
                if this_v is not None:
                    total_count += 1
                    if this_v > 1.5:
                        over_count += 1
            if total_count == 0:
                city_line_values.append(None)
            else:
                percent = max(100 - over_count * 10, 0)
                city_line_values.append(percent)
        from pyecharts.charts import Line
        from pyecharts import options as opts
        line = (
            Line(init_opts=opts.InitOpts(width="100%", height="334px"))
        .add_xaxis(city_line_months)
        .add_yaxis(f"全市{this_year}", city_line_values, is_symbol_show=True, is_smooth=True, color="#5470C6")
        .set_global_opts(
            title_opts=opts.TitleOpts(title="全市", subtitle="", pos_left="center", pos_top="top", title_textstyle_opts=opts.TextStyleOpts(font_size=12)),
            xaxis_opts=opts.AxisOpts(name="", axislabel_opts=opts.LabelOpts(font_size=10)),
            yaxis_opts=opts.AxisOpts(name="", axislabel_opts=opts.LabelOpts(font_size=10), min_=0, max_=100),
            legend_opts=opts.LegendOpts(is_show=True),
            tooltip_opts=opts.TooltipOpts(trigger="axis")
        )
        )
        line_chart_html = line.render_embed()
        # 2. 获取图表用的完整数据（按地点筛选，但不按日期筛选）
        chart_query = select(PUEData)
        if location:
            chart_query = chart_query.where(PUEData.location == location)
        chart_result = await db.execute(chart_query)
        chart_data_list = chart_result.scalars().all()
        
        # 3. 获取关键指标用的筛选数据（按地点和日期筛选）
        metrics_query = select(PUEData).where(query_filter)
        if location:
            metrics_query = metrics_query.where(PUEData.location == location)
        metrics_result = await db.execute(metrics_query)
        pue_data_list = metrics_result.scalars().all()

        def build_year_series(records, target_year):
            # 为当前视图的月份创建映射
            month_map = {m: [] for m in months}
            
            # 收集数据
            for rec in records:
                if rec.year == target_year and str(rec.month) in month_map:
                    month_map[str(rec.month)].append(rec.pue_value)
            
            # 构建series数据
            series = []
            for m in months:
                vals = month_map[m]
                if vals:
                    avg_value = sum(vals) / len(vals)
                    series.append(round(avg_value, 3))
                else:
                    series.append(None)
            
            
            return series

        last_year_values = build_year_series(chart_data_list, last_year)
        this_year_values = build_year_series(chart_data_list, this_year)
        
        # 确保数据长度匹配x_axis
        target_len = len(x_axis)
        while len(last_year_values) < target_len:
            last_year_values.append(None)
        while len(this_year_values) < target_len:
            this_year_values.append(None)
        
        last_year_values = last_year_values[:target_len]
        this_year_values = this_year_values[:target_len]

        # 构造月份到数值的映射，便于后续比较
        this_dict = {months[i]: this_year_values[i] for i in range(len(months))}
        last_dict = {months[i]: last_year_values[i] for i in range(len(months))}
        # 生成用电量模拟数据（基于PUE值估算）
        estimated_power_this_year = []
        estimated_power_last_year = []
        base_power = 800000  # 基础用电量 kWh
    
        for pue_val in this_year_values:
            if pue_val is not None:
                # 假设PUE值越高，用电量越大
                power = base_power * pue_val
                estimated_power_this_year.append(round(power, 0))
            else:
                estimated_power_this_year.append(None)
    
        for pue_val in last_year_values:
            if pue_val is not None:
                power = base_power * pue_val
                estimated_power_last_year.append(round(power, 0))
            else:
                estimated_power_last_year.append(None)

        from pyecharts.charts import Bar, Line, HeatMap, Radar
        from pyecharts.commons.utils import JsCode
    
        bar_width = "100%"
        color_bar1 = "#3498db"
        color_bar2 = "#e74c3c"
        color_line1 = "#2ecc71"
        color_line2 = "#f39c12"
    
        # 创建双Y轴混合图表
        bar = (
            Bar(init_opts=opts.InitOpts(width=bar_width, height="480px", chart_id="pue_bar"))
        .add_xaxis(x_axis)
        .add_yaxis(
            f"{this_year}年PUE",
            this_year_values,
            color=color_bar2,
            label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10),
            yaxis_index=0
        )
        .add_yaxis(
            f"{last_year}年PUE", 
            last_year_values,
            color=color_bar1,
            label_opts=opts.LabelOpts(is_show=True, position="top", font_size=10),
            yaxis_index=0
        )
        .extend_axis(
            yaxis=opts.AxisOpts(
                name="用电量(kWh)",
                type_="value",
                min_=0,
                position="right",
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color=color_line1)
                ),
                axislabel_opts=opts.LabelOpts(formatter="{value}k")
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="PUE指标与用电量双轴分析",
                pos_left="center"
            ),
            xaxis_opts=opts.AxisOpts(
                name="月份", 
                axislabel_opts=opts.LabelOpts(rotate=30),
                type_="category"
            ),
            yaxis_opts=opts.AxisOpts(
                name="PUE值",
                type_="value",
                min_=0,
                position="left",
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color=color_bar2)
                )
            ),
            legend_opts=opts.LegendOpts(pos_top="8%"),
            toolbox_opts=opts.ToolboxOpts(
                is_show=True,
                feature={
                    "dataView": {"show": True, "readOnly": False},
                    "magicType": {"show": True, "type": ["line", "bar"]},
                    "restore": {"show": True},
                    "saveAsImage": {"show": True}
                }
            ),
            datazoom_opts=[
                opts.DataZoomOpts(range_start=0, range_end=100, pos_bottom="2%"),
                opts.DataZoomOpts(type_="inside")
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(0,0,0,0.8)",
                border_color="#777",
                border_width=1,
                formatter=JsCode("""
                    function(params) {
                        var month = params[0].name;
                        var content = '<div style="margin:0;padding:8px;"><b>' + month + '</b><br/>';
                        params.forEach(function(item) {
                            if(item.value !== null && item.value !== undefined) {
                                var unit = item.seriesName.includes('PUE') ? '' : 'kWh';
                                content += '<div style="margin:4px 0;">';
                                content += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + item.color + ';margin-right:8px;"></span>';
                                content += item.seriesName + ': <b>' + item.value + unit + '</b>';
                                content += '</div>';
                            }
                        });
                        content += '<div style="margin-top:8px;font-size:11px;color:#999;">点击柱状图查看详细信息</div>';
                        return content + '</div>';
                    }
                """)
            )
        )
        .set_series_opts(
            animation_opts=opts.AnimationOpts(
                animation=True,
                animation_easing="cubicOut",
                animation_duration=1500
            )
        )
        )
    
        # 添加用电量折线图
        line = (
        Line()
        .add_xaxis(x_axis)
        .add_yaxis(
            f"{this_year}年用电量",
            [round(v/1000, 1) if v is not None else None for v in estimated_power_this_year],
            color=color_line1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=3)
        )
        .add_yaxis(
            f"{last_year}年用电量",
            [round(v/1000, 1) if v is not None else None for v in estimated_power_last_year],
            color=color_line2,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=3)
        )
        )
    
        # 合并图表
        bar.overlap(line)
    
        # 添加 click 事件，在点击柱状图时触发下钻弹窗
        bar_id = bar.chart_id  # pyecharts 会用该 id 作为 DOM 容器 id 和变量前缀
        js_code = f"""
        var chartDom = document.getElementById('{bar_id}');
        if (chartDom) {{
        var chartInstance = echarts.getInstanceByDom(chartDom) || echarts.init(chartDom);
        chartInstance.on('click', function(params) {{
            if (params.componentType === 'series') {{
                var month = params.dataIndex + 1; // 月份从1开始
                var year = (params.seriesIndex === 0) ? '{this_year}' : '{last_year}';
                // 从当前 URL 参数获取 location，更可靠
                var urlParams = new URLSearchParams(window.location.search);
                var location = urlParams.get('location') || '';
                if (location) {{
                    showDrillDownModal(location, month, year);
                 }}
            }}
        }});
        }}
        """
        bar.add_js_funcs(js_code)
        chart_html = bar.render_embed()
        table_data = []
        for p in pue_data_list:
            table_data.append({
                'location': p.location,
                'year': p.year,
                'month': p.month,
                'pue_value': p.pue_value
            })
        locations = sorted(set([p.location for p in pue_data_list]))
        
        # 为multi_table获取完整的两年数据（last_year和this_year）
        multi_table_query = select(PUEData).where(
            and_(
                PUEData.year.in_(years),
                PUEData.month.in_(months)
            )
        )
        multi_table_result = await db.execute(multi_table_query)
        multi_table_data = multi_table_result.scalars().all()
        
        # 确保locations包含完整数据中的所有地点
        all_multi_locations = sorted(set([p.location for p in multi_table_data]))
        locations = sorted(set(locations + all_multi_locations))
        
        multi_table = {m: {loc: {y: None for y in years} for loc in locations} for m in months}
        for p in multi_table_data:
            if p.year in years and p.location in locations and p.month in months:
                multi_table[p.month][p.location][p.year] = p.pue_value
        # 其它红绿灯等业务逻辑保持不变
        red_months = []
        yellow_months = []
        green_months = []
        month_down = []
        for i, m in enumerate(months):
            this_v = this_dict.get(m)
            last_v = last_dict.get(m)
            if this_v is not None and last_v is not None and this_v < last_v:
                month_down.append(True)
            else:
                month_down.append(False)
        i = 0
        while i < len(months):
            if i+1 < len(months) and month_down[i] and month_down[i+1]:
                red_months.append(months[i+1])
                i += 2
            elif month_down[i]:
                yellow_months.append(months[i])
                i += 1
            else:
                green_months.append(months[i])
                i += 1
        yellow_months = [m for m in yellow_months if m not in red_months]
        green_months = [m for m in green_months if m not in red_months and m not in yellow_months]
    
        # ============ 计算关键指标卡片数据 ============
        # 基于筛选后的数据计算指标
        filtered_pue_values = [p.pue_value for p in pue_data_list if p.pue_value is not None]
        
        # 获取筛选数据中的最新月份作为"当前"值
        latest_data = None
        if pue_data_list:
            # 按年月排序，获取最新数据
            sorted_data = sorted(pue_data_list, key=lambda x: (int(x.year), int(x.month)), reverse=True)
            latest_data = sorted_data[0] if sorted_data else None
        
        current_month_pue = latest_data.pue_value if latest_data else None
        current_month = str(latest_data.month) if latest_data else str(now.month)
        
        # 计算环比变化（使用筛选数据中的上一个月）
        monthly_change = None
        last_month_pue = None
        if len(pue_data_list) >= 2:
            sorted_data = sorted(pue_data_list, key=lambda x: (int(x.year), int(x.month)), reverse=True)
            if len(sorted_data) >= 2:
                last_month_pue = sorted_data[1].pue_value
                if current_month_pue is not None and last_month_pue is not None:
                    monthly_change = ((current_month_pue - last_month_pue) / last_month_pue) * 100
    
        # 计算同比变化（使用去年同月数据，如果有的话）
        yearly_change = None
        if latest_data and current_month_pue is not None:
            current_year = int(latest_data.year)
            current_month_num = int(latest_data.month)
            last_year_same_month = None
            
            # 查找去年同月数据
            for p in pue_data_list:
                if int(p.year) == current_year - 1 and int(p.month) == current_month_num:
                    last_year_same_month = p.pue_value
                    break
            
            if last_year_same_month is not None:
                yearly_change = ((current_month_pue - last_year_same_month) / last_year_same_month) * 100
    
        # 筛选数据的平均PUE
        year_avg_pue = round(sum(filtered_pue_values) / len(filtered_pue_values), 3) if filtered_pue_values else None
    
        # 最优/最差地点（基于筛选数据）
        best_location = None
        worst_location = None
        best_pue = None
        worst_pue = None
    
        # 获取筛选数据中各地点的平均PUE
        location_averages = {}
        for p in pue_data_list:
            if p.pue_value is not None:
                if p.location not in location_averages:
                    location_averages[p.location] = []
                location_averages[p.location].append(p.pue_value)
    
        # 计算各地点平均值
        for loc, values in location_averages.items():
            location_averages[loc] = sum(values) / len(values)
    
        if location_averages:
            best_location = min(location_averages.items(), key=lambda x: x[1])
            worst_location = max(location_averages.items(), key=lambda x: x[1])
            best_pue = round(best_location[1], 3)
            worst_pue = round(worst_location[1], 3)
            best_location = best_location[0]
            worst_location = worst_location[0]
    
        # 达标率（假设PUE <= 1.5为达标）基于筛选数据
        compliance_rate = None
        total_records = len(pue_data_list)
        compliant_records = 0
    
        for p in pue_data_list:
            if p.pue_value is not None and p.pue_value <= 1.5:
                compliant_records += 1
    
        if total_records > 0:
            compliance_rate = round((compliant_records / total_records) * 100, 1)
    
        # 节能量估算（假设基准PUE为2.0，单位kWh）基于筛选数据
        energy_savings = None
        if year_avg_pue is not None:
            baseline_pue = 2.0
            estimated_monthly_kwh = 1000000  # 假设月用电量100万kWh
            months_with_data = len(filtered_pue_values)
            if year_avg_pue < baseline_pue:
                savings_per_month = estimated_monthly_kwh * (baseline_pue - year_avg_pue) / baseline_pue
                energy_savings = round(savings_per_month * months_with_data, 0)
    
        # 碳减排量（假设每kWh电力产生0.5kg CO2）
        carbon_reduction = None
        if energy_savings is not None:
            carbon_factor = 0.5  # kg CO2 per kWh
            carbon_reduction = round(energy_savings * carbon_factor / 1000, 1)  # 转换为吨
    
        # 关键指标数据
        key_metrics = {
        "current_month_pue": current_month_pue,
        "monthly_change": round(monthly_change, 2) if monthly_change is not None else None,
        "yearly_change": round(yearly_change, 2) if yearly_change is not None else None,
        "year_avg_pue": year_avg_pue,
        "best_location": best_location,
        "best_pue": best_pue,
        "worst_location": worst_location,
        "worst_pue": worst_pue,
        "compliance_rate": compliance_rate,
        "energy_savings": energy_savings,
        "carbon_reduction": carbon_reduction,
        "current_month": current_month
        }
    
        # ============ 生成热力图 ============
        # 准备热力图数据：地点-月份的PUE值分布
        heatmap_data = []
        location_list = list(all_locations) if all_locations else []
        month_list = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
    
        # 为每个地点和月份组合准备数据
        for j, month in enumerate(month_list):
            for i, loc in enumerate(location_list):
                pue_val = multi_table.get(month, {}).get(loc, {}).get(this_year)
                if pue_val is not None:
                    # [月份索引, 地点索引, PUE值]
                    heatmap_data.append([j, i, round(float(pue_val), 3)])
    
        # 生成热力图
        if heatmap_data and location_list:
            heatmap = (
                HeatMap(init_opts=opts.InitOpts(width="100%", height="500px"))
                .add_xaxis([f"{m}月" for m in month_list])
                .add_yaxis(
                    "",
                    location_list,
                    heatmap_data,
                    label_opts=opts.LabelOpts(is_show=True, font_size=9),
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(
                        title="PUE指标热力图",
                        subtitle=f"{this_year}年各地点月度PUE分布",
                        pos_left="center",
                        pos_top="10px"
                    ),
                    visualmap_opts=opts.VisualMapOpts(
                        min_=1.0,
                        max_=3.0,
                        is_calculable=True,
                        is_show=False,
                        range_color=["#313695", "#4575b4", "#74add1", "#abd9e9", 
                                   "#e0f3f8", "#fee090", "#fdae61", "#f46d43", "#d73027"]
                    ),
                    xaxis_opts=opts.AxisOpts(
                        name="月份",
                        name_location="middle",
                        name_gap=30,
                        axislabel_opts=opts.LabelOpts(rotate=0)
                    ),
                    yaxis_opts=opts.AxisOpts(
                        name="地点",
                        name_location="middle",
                        name_gap=60
                    ),
                    tooltip_opts=opts.TooltipOpts(
                        formatter=JsCode(
                            "function(params) {"
                            "return params.marker + '地点: ' + params.name + '<br/>' + "
                            "'月份: ' + params.value[0] + '月<br/>' + "
                            "'PUE值: ' + params.value[2];"
                            "}"
                        )
                    )
                )
            )
            heatmap_html = heatmap.render_embed()
        else:
            heatmap_html = "<div style='text-align:center;padding:50px;color:#999;'>暂无热力图数据</div>"
    
        # ============ 生成雷达图 ============
        # 准备雷达图数据：多维度PUE性能评估
        radar_indicators = [
        {"name": "当月PUE", "max": 100},    # 使用百分制
        {"name": "年均PUE", "max": 100},    # 使用百分制
        {"name": "稳定性", "max": 100},      # 基于标准差计算
        {"name": "改善趋势", "max": 100},    # 基于同比变化
        {"name": "合规率", "max": 100},
        {"name": "能效水平", "max": 100}     # 基于与基准值对比
        ]
    
        # 为每个地点计算雷达图指标
        radar_data = []
        current_month = str(datetime.now().month)
        
        if location_list:
            for loc in location_list[:5]:  # 限制显示前5个地点
                # 获取该地点当年的所有月份数据
                loc_data = {}
                for month in month_list:
                    pue_val = multi_table.get(month, {}).get(loc, {}).get(this_year)
                    if pue_val is not None:
                        loc_data[month] = float(pue_val)
                
                if not loc_data:
                    continue
                    
                # 当月PUE (转换为百分制，3.0对应0，1.0对应100)
                current_pue = loc_data.get(current_month)
                current_pue_score = max(0, (3.0 - current_pue) / 2.0 * 100) if current_pue else 0
                
                # 年均PUE
                loc_values = list(loc_data.values())
                avg_pue = sum(loc_values) / len(loc_values) if loc_values else 2.5
                avg_pue_score = max(0, (3.0 - avg_pue) / 2.0 * 100)
                
                # 稳定性 (基于标准差，标准差越小稳定性越高)
                if len(loc_values) > 1:
                    std_dev = statistics.stdev(loc_values)
                    stability_score = max(0, 100 - std_dev * 200)
                else:
                    stability_score = 50
                
                # 改善趋势 (基于现有数据变化)
                if len(loc_values) >= 2:
                    recent_avg = sum(loc_values[-3:]) / len(loc_values[-3:])
                    early_avg = sum(loc_values[:3]) / len(loc_values[:3])
                    trend_change = (early_avg - recent_avg) / early_avg
                    trend_score = max(0, min(100, 50 + trend_change * 100))
                else:
                    trend_score = 50
                
                # 合规率 (假设1.8以下为优秀)
                compliance_count = sum(1 for v in loc_values if v <= 1.8)
                compliance_score = (compliance_count / len(loc_values)) * 100 if loc_values else 0
                
                # 能效水平 (与行业基准2.0对比)
                if avg_pue <= 2.0:
                    efficiency_score = (2.0 - avg_pue) / 1.0 * 100
                else:
                    efficiency_score = 0
                efficiency_score = max(0, min(100, efficiency_score))
                
                radar_data.append({
                    "value": [
                        round(current_pue_score, 1),
                        round(avg_pue_score, 1), 
                        round(stability_score, 1),
                        round(trend_score, 1),
                        round(compliance_score, 1),
                        round(efficiency_score, 1)
                    ],
                    "name": loc
                })
    
        # 生成雷达图
        if radar_data:
            radar = (
                Radar(init_opts=opts.InitOpts(width="100%", height="520px"))
                .add_schema(
                    schema=radar_indicators,
                    splitarea_opt=opts.SplitAreaOpts(is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=0.1)),
                    textstyle_opts=opts.TextStyleOpts(color="#666", font_size=11)
                )
                .add(
                    series_name="PUE综合评估",
                    data=radar_data,
                    linestyle_opts=opts.LineStyleOpts(width=2),
                    areastyle_opts=opts.AreaStyleOpts(opacity=0.2)
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(
                        title="PUE多维度性能雷达图",
                        pos_left="center",
                        pos_top="0px"
                    ),
                    legend_opts=opts.LegendOpts(
                        orient="vertical",
                        pos_right="20px",
                        pos_top="80px"
                    ),
                    tooltip_opts=opts.TooltipOpts(
                        trigger="item",
                        formatter=JsCode(
                            "function(params) {"
                            "var data = params.data;"
                            "var indicators = ['当月PUE', '年均PUE', '稳定性', '改善趋势', '合规率', '能效水平'];"
                            "var result = params.seriesName + '<br/>' + data.name + '<br/>';"
                            "for(var i = 0; i < data.value.length; i++) {"
                            "result += indicators[i] + ': ' + data.value[i] + '<br/>';"
                            "}"
                            "return result;"
                            "}"
                        )
                    )
                )
            )
            radar_html = radar.render_embed()
        else:
            radar_html = "<div style='text-align:center;padding:50px;color:#999;'>暂无雷达图数据</div>"
    
    except Exception as e:
        # 如果数据处理失败，记录错误并使用默认值
        print(f"PUE分析页面数据处理错误: {e}")
        import traceback
        traceback.print_exc()
    
    return bi_templates_env.TemplateResponse(
        "pue_analyze.html",
        {"request": request, "pue_bar_chart": chart_html, "all_locations": all_locations, "current_location": location, "table_data": table_data, "last_year": last_year, "this_year": this_year, "locations": locations, "years": years, "months": months, "multi_table": multi_table, "red_months": red_months, "yellow_months": yellow_months, "green_months": green_months, "line_chart_html": line_chart_html, "key_metrics": key_metrics, "heatmap_html": heatmap_html, "radar_html": radar_html}
    )

# ========== AI智能分析接口，对齐汇聚骨干指标分析体验 ==========
from fastapi.responses import JSONResponse
import requests
import re

# 可复用huijugugan.py的AI分析函数，或本地定义

def analyze_and_predict_with_deepseek(df, location=None, max_rounds=3):
    api_url = "https://DeepSeek-R1-wzrba.eastus2.models.ai.azure.com/chat/completions"
    api_key = "HyYc4J6EcwlktQLXMcXQJNAtkRgioiqi"
    prompt = f"请对如下{('地点：'+location) if location else '全部地点'}的PUE指标数据进行简要分析、总结规律，并预测未来几个月的趋势：\n{df.to_string(index=False)}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = [{"role": "user", "content": prompt}]
    all_content = ""
    for i in range(max_rounds):
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7
        }
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            all_content += content
            if len(content) < 900 or "已完成" in content or "END" in content:
                break
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "请继续输出剩余内容"})
        except Exception as e:
            all_content += f"\n[AI分析补全失败：{e}]"
            break
    # 清洗AI输出
    cleaned_content = re.sub(r'<think>[\s\S]*?</think>', '', all_content)
    cleaned_content = re.sub(r'^[#>*\-\s]+', '', cleaned_content, flags=re.MULTILINE)
    cleaned_content = cleaned_content.replace('*', '')
    return cleaned_content.strip()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.models import PUEData
from fastapi import Depends
from fastapi import APIRouter

@router.get("/pue_ai_analysis")
async def get_pue_ai_analysis(location: str = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PUEData))
    data = result.scalars().all()
    if not data:
        return JSONResponse(content={"ai_analysis": "暂无数据"})
    df_data = []
    for item in data:
        if location and item.location != location:
            continue
        df_data.append({
            "month": item.month,
            "location": item.location,
            "pue_value": item.pue_value,
            "year": item.year
        })
    import pandas as pd
    df = pd.DataFrame(df_data)
    ai_analysis = analyze_and_predict_with_deepseek(df if not location else df[df['location'] == location], location)
    return JSONResponse(content={"ai_analysis": ai_analysis})

# PUE下钻数据API
@router.get("/pue_drill_down_data")
async def get_pue_drill_down_data(location: str = None, month: str = None, year: str = None, db: AsyncSession = Depends(get_db)):
    """获取PUE下钻数据"""
    from db.models import PUEDrillDownData
    
    query = select(PUEDrillDownData)
    
    # 添加筛选条件
    if location:
        query = query.where(PUEDrillDownData.location.like(f"%{location}%"))
    if month:
        query = query.where(PUEDrillDownData.month == month)
    if year:
        query = query.where(PUEDrillDownData.year == year)
    
    result = await db.execute(query)
    drill_down_data = result.scalars().all()
    
    # 转换为字典格式
    data_list = []
    for item in drill_down_data:
        data_list.append({
            "id": item.id,
            "location": item.location,
            "month": item.month,
            "year": item.year,
            "work_type": item.work_type,
            "work_category": item.work_category,
            "sequence_no": item.sequence_no,
            "work_object": item.work_object,
            "check_item": item.check_item,
            "operation_method": item.operation_method,
            "benchmark_value": item.benchmark_value,
            "execution_standard": item.execution_standard,
            "execution_status": item.execution_status,
            "detailed_situation": item.detailed_situation,
            "quantification_standard": item.quantification_standard,
            "last_month_standard": item.last_month_standard,
            "quantification_unit": item.quantification_unit,
            "executor": item.executor
        })

    # 返回所有数据
    return JSONResponse(content={
        "success": True,
        "data": data_list,
        "total": len(data_list)
    })

# 导出下钻数据为 Excel
@router.get("/pue_drill_down_excel")
async def export_pue_drill_down_excel(location: str, year: str, month: str, db: AsyncSession = Depends(get_db)):
    """生成符合筛选条件的下钻数据 Excel 并返回下载"""
    query = select(PUEDrillDownData).where(PUEDrillDownData.location == location, PUEDrillDownData.year == year, PUEDrillDownData.month == month)
    result = await db.execute(query)
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="no data")
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame([{
        "序号": r.sequence_no,
        "作业形式": r.work_type,
        "作业分类": r.work_category,
        "作业对象": r.work_object,
        "检查项": r.check_item,
        "操作方法": r.operation_method,
        "执行标准": r.execution_standard,
        "执行情况": r.execution_status,
        "执行人": r.executor,
    } for r in rows])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="drill_down")
    buffer.seek(0)
    from urllib.parse import quote
    filename = f"drill_down_{location}_{year}{month}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
