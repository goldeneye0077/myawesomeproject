from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from typing import Optional, List
import io
import pandas as pd
from db.models import Zbk, CenterTopTop, CenterTopBottom, LeftTop, LeftMiddle, RightTop, RightMiddle, Bottom, LeftMiddleKPI, CenterMiddleKPI, RightMiddleKPI, LeftBottomKPI, RightBottomKPI, TopKPI, PUEData, FaultRecord
from common import bi_data_templates, bi_data_templates_env
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import Depends
from db.session import get_db

router = APIRouter()

# 定义指标类型枚举
from enum import Enum
class IndicatorType(str, Enum):
    CONTRACT = "contract"
    KPI = "kpi"

# Pydantic模型用于API请求和响应
from pydantic import BaseModel
class ZbkCreate(BaseModel):
    zbx: str
    fz: str
    qspm: str
    qnljdfzb: str
    nddcpg: str
    y1zb: str
    y2zb: str
    y3zb: str
    y4zb: str
    y5zb: str
    y6zb: str
    jzz: str
    tzz: str
    type: str = "contract"  # 默认为契约化指标

class ZbkUpdate(BaseModel):
    zbx: Optional[str] = None
    fz: Optional[str] = None
    qspm: Optional[str] = None
    qnljdfzb: Optional[str] = None
    nddcpg: Optional[str] = None
    y1zb: Optional[str] = None
    y2zb: Optional[str] = None
    y3zb: Optional[str] = None
    y4zb: Optional[str] = None
    y5zb: Optional[str] = None
    y6zb: Optional[str] = None
    jzz: Optional[str] = None
    tzz: Optional[str] = None
    type: Optional[str] = None

# CenterTopTop管理页面及增删改查接口
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

templates = Jinja2Templates(directory="templates")

@router.get("/center_top_top", response_class=HTMLResponse)
async def center_top_top_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CenterTopTop))
    rows = result.scalars().all()
    return templates.TemplateResponse("CenterTopTop.html", {"request": request, "rows": rows})

@router.post("/center_top_top/add")
async def center_top_top_add(
    type: str = Form(...),
    status: str = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = CenterTopTop(type=type, status=status, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/center_top_top", status_code=303)

@router.post("/center_top_top/update")
async def center_top_top_update(
    id: int = Form(...),
    type: str = Form(...),
    status: str = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CenterTopTop).where(CenterTopTop.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.type = type
    obj.status = status
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/center_top_top", status_code=303)

@router.post("/center_top_top/delete")
async def center_top_top_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CenterTopTop).where(CenterTopTop.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/center_top_top", status_code=303)

# CenterTopBottom管理页面及增删改查接口
@router.get("/center_top_bottom", response_class=HTMLResponse)
async def center_top_bottom_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CenterTopBottom))
    rows = result.scalars().all()
    return templates.TemplateResponse("CenterTopBottom.html", {"request": request, "rows": rows})

@router.post("/center_top_bottom/add")
async def center_top_bottom_add(
    region: str = Form(...),
    value: float = Form(...),
    ratio: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = CenterTopBottom(region=region, value=value, ratio=ratio, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/center_top_bottom", status_code=303)

@router.post("/center_top_bottom/update")
async def center_top_bottom_update(
    id: int = Form(...),
    region: str = Form(...),
    value: float = Form(...),
    ratio: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CenterTopBottom).where(CenterTopBottom.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.region = region
    obj.value = value
    obj.ratio = ratio
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/center_top_bottom", status_code=303)

@router.post("/center_top_bottom/delete")
async def center_top_bottom_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CenterTopBottom).where(CenterTopBottom.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/center_top_bottom", status_code=303)

# LeftTop管理页面及增删改查接口
@router.get("/left_top", response_class=HTMLResponse)
async def left_top_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LeftTop))
    rows = result.scalars().all()
    return templates.TemplateResponse("LeftTop.html", {"request": request, "rows": rows})

@router.post("/left_top/add")
async def left_top_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = LeftTop(month=month, baseline=baseline, challenge=challenge, indicator=indicator, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/left_top", status_code=303)

@router.post("/left_top/update")
async def left_top_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftTop).where(LeftTop.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.indicator = indicator
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/left_top", status_code=303)

@router.post("/left_top/delete")
async def left_top_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftTop).where(LeftTop.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/left_top", status_code=303)

# LeftMiddle管理页面及增删改查接口
@router.get("/left_middle", response_class=HTMLResponse)
async def left_middle_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LeftMiddle))
    rows = result.scalars().all()
    return templates.TemplateResponse("LeftMiddle.html", {"request": request, "rows": rows})

@router.post("/left_middle/add")
async def left_middle_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = LeftMiddle(month=month, baseline=baseline, challenge=challenge, indicator=indicator, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/left_middle", status_code=303)

@router.post("/left_middle/update")
async def left_middle_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftMiddle).where(LeftMiddle.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.indicator = indicator
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/left_middle", status_code=303)

@router.post("/left_middle/delete")
async def left_middle_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftMiddle).where(LeftMiddle.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/left_middle", status_code=303)

# RightTop管理页面及增删改查接口
@router.get("/right_top", response_class=HTMLResponse)
async def right_top_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RightTop))
    rows = result.scalars().all()
    return templates.TemplateResponse("RightTop.html", {"request": request, "rows": rows})

@router.post("/right_top/add")
async def right_top_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = RightTop(month=month, baseline=baseline, challenge=challenge, indicator=indicator, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/right_top", status_code=303)

@router.post("/right_top/update")
async def right_top_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightTop).where(RightTop.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.indicator = indicator
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/right_top", status_code=303)

@router.post("/right_top/delete")
async def right_top_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightTop).where(RightTop.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/right_top", status_code=303)

# RightMiddle管理页面及增删改查接口
@router.get("/right_middle", response_class=HTMLResponse)
async def right_middle_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RightMiddle))
    rows = result.scalars().all()
    return templates.TemplateResponse("RightMiddle.html", {"request": request, "rows": rows})

@router.post("/right_middle/add")
async def right_middle_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = RightMiddle(month=month, baseline=baseline, challenge=challenge, indicator=indicator, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/right_middle", status_code=303)

@router.post("/right_middle/update")
async def right_middle_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    indicator: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightMiddle).where(RightMiddle.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.indicator = indicator
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/right_middle", status_code=303)

@router.post("/right_middle/delete")
async def right_middle_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightMiddle).where(RightMiddle.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/right_middle", status_code=303)

# Bottom管理页面及增删改查接口
@router.get("/bottom", response_class=HTMLResponse)
async def bottom_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bottom))
    rows = result.scalars().all()
    return templates.TemplateResponse("Bottom.html", {"request": request, "rows": rows})

@router.post("/bottom/add")
async def bottom_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    battery_voltage_ratio: float = Form(...),
    mains_load_ratio: float = Form(...),
    ups_load_ratio: float = Form(...),
    env_signal_ratio: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = Bottom(
        month=month,
        baseline=baseline,
        challenge=challenge,
        battery_voltage_ratio=battery_voltage_ratio,
        mains_load_ratio=mains_load_ratio,
        ups_load_ratio=ups_load_ratio,
        env_signal_ratio=env_signal_ratio,
        year=year
    )
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/bottom", status_code=303)

@router.post("/bottom/update")
async def bottom_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    battery_voltage_ratio: float = Form(...),
    mains_load_ratio: float = Form(...),
    ups_load_ratio: float = Form(...),
    env_signal_ratio: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Bottom).where(Bottom.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.battery_voltage_ratio = battery_voltage_ratio
    obj.mains_load_ratio = mains_load_ratio
    obj.ups_load_ratio = ups_load_ratio
    obj.env_signal_ratio = env_signal_ratio
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/bottom", status_code=303)

@router.post("/bottom/delete")
async def bottom_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Bottom).where(Bottom.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/bottom", status_code=303)

# left_middle_kpi 管理
@router.get("/left_middle_kpi", response_class=HTMLResponse)
async def left_middle_kpi_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LeftMiddleKPI))
    rows = result.scalars().all()
    return templates.TemplateResponse("LeftMiddleKPI.html", {"request": request, "rows": rows})

@router.post("/left_middle_kpi/add")
async def left_middle_kpi_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    offline_duration: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = LeftMiddleKPI(month=month, baseline=baseline, challenge=challenge, offline_duration=offline_duration, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/left_middle_kpi", status_code=303)

@router.post("/left_middle_kpi/update")
async def left_middle_kpi_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    offline_duration: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftMiddleKPI).where(LeftMiddleKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.offline_duration = offline_duration
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/left_middle_kpi", status_code=303)

@router.post("/left_middle_kpi/delete")
async def left_middle_kpi_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftMiddleKPI).where(LeftMiddleKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/left_middle_kpi", status_code=303)

# center_middle_kpi 管理
@router.get("/center_middle_kpi", response_class=HTMLResponse)
async def center_middle_kpi_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CenterMiddleKPI))
    rows = result.scalars().all()
    return templates.TemplateResponse("CenterMiddleKPI.html", {"request": request, "rows": rows})

@router.post("/center_middle_kpi/add")
async def center_middle_kpi_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    broadband_rate: float = Form(...),
    delivery_rate: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = CenterMiddleKPI(month=month, baseline=baseline, challenge=challenge, broadband_rate=broadband_rate, delivery_rate=delivery_rate, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/center_middle_kpi", status_code=303)

@router.post("/center_middle_kpi/update")
async def center_middle_kpi_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    broadband_rate: float = Form(...),
    delivery_rate: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CenterMiddleKPI).where(CenterMiddleKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.broadband_rate = broadband_rate
    obj.delivery_rate = delivery_rate
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/center_middle_kpi", status_code=303)

@router.post("/center_middle_kpi/delete")
async def center_middle_kpi_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CenterMiddleKPI).where(CenterMiddleKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/center_middle_kpi", status_code=303)

# right_middle_kpi 管理
@router.get("/right_middle_kpi", response_class=HTMLResponse)
async def right_middle_kpi_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RightMiddleKPI))
    rows = result.scalars().all()
    return templates.TemplateResponse("RightMiddleKPI.html", {"request": request, "rows": rows})

@router.post("/right_middle_kpi/add")
async def right_middle_kpi_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    r_and_d_completion: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = RightMiddleKPI(month=month, baseline=baseline, challenge=challenge, r_and_d_completion=r_and_d_completion, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/right_middle_kpi", status_code=303)

@router.post("/right_middle_kpi/update")
async def right_middle_kpi_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    r_and_d_completion: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightMiddleKPI).where(RightMiddleKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.r_and_d_completion = r_and_d_completion
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/right_middle_kpi", status_code=303)

@router.post("/right_middle_kpi/delete")
async def right_middle_kpi_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightMiddleKPI).where(RightMiddleKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/right_middle_kpi", status_code=303)

# left_bottom_kpi 管理
@router.get("/left_bottom_kpi", response_class=HTMLResponse)
async def left_bottom_kpi_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LeftBottomKPI))
    rows = result.scalars().all()
    return templates.TemplateResponse("LeftBottomKPI.html", {"request": request, "rows": rows})

@router.post("/left_bottom_kpi/add")
async def left_bottom_kpi_add(
    indicator: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    current: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = LeftBottomKPI(indicator=indicator, baseline=baseline, challenge=challenge, current=current, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/left_bottom_kpi", status_code=303)

@router.post("/left_bottom_kpi/update")
async def left_bottom_kpi_update(
    id: int = Form(...),
    indicator: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    current: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftBottomKPI).where(LeftBottomKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.indicator = indicator
    obj.baseline = baseline
    obj.challenge = challenge
    obj.current = current
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/left_bottom_kpi", status_code=303)

@router.post("/left_bottom_kpi/delete")
async def left_bottom_kpi_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeftBottomKPI).where(LeftBottomKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/left_bottom_kpi", status_code=303)

# right_bottom_kpi 管理
@router.get("/right_bottom_kpi", response_class=HTMLResponse)
async def right_bottom_kpi_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RightBottomKPI))
    rows = result.scalars().all()
    return templates.TemplateResponse("RightBottomKPI.html", {"request": request, "rows": rows})

@router.post("/right_bottom_kpi/add")
async def right_bottom_kpi_add(
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    broadband_rate: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = RightBottomKPI(month=month, baseline=baseline, challenge=challenge, broadband_rate=broadband_rate, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/right_bottom_kpi", status_code=303)

@router.post("/right_bottom_kpi/update")
async def right_bottom_kpi_update(
    id: int = Form(...),
    month: str = Form(...),
    baseline: float = Form(...),
    challenge: float = Form(...),
    broadband_rate: float = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightBottomKPI).where(RightBottomKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.month = month
    obj.baseline = baseline
    obj.challenge = challenge
    obj.broadband_rate = broadband_rate
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/right_bottom_kpi", status_code=303)

@router.post("/right_bottom_kpi/delete")
async def right_bottom_kpi_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RightBottomKPI).where(RightBottomKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/right_bottom_kpi", status_code=303)

# top_kpi 管理
@router.get("/top_kpi", response_class=HTMLResponse)
async def top_kpi_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TopKPI))
    rows = result.scalars().all()
    return templates.TemplateResponse("TopKPI.html", {"request": request, "rows": rows})

@router.post("/top_kpi/add")
async def top_kpi_add(
    type: str = Form(...),
    status: str = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    obj = TopKPI(type=type, status=status, year=year)
    db.add(obj)
    await db.commit()
    return RedirectResponse(url="/top_kpi", status_code=303)

@router.post("/top_kpi/update")
async def top_kpi_update(
    id: int = Form(...),
    type: str = Form(...),
    status: str = Form(...),
    year: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TopKPI).where(TopKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    obj.type = type
    obj.status = status
    obj.year = year
    await db.commit()
    return RedirectResponse(url="/top_kpi", status_code=303)

@router.post("/top_kpi/delete")
async def top_kpi_delete(
    id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TopKPI).where(TopKPI.id == id))
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="数据不存在")
    await db.delete(obj)
    await db.commit()
    return RedirectResponse(url="/top_kpi", status_code=303)

# 路由定义
@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    """主页仪表板"""
    from common import bi_templates_env
    return bi_templates_env.TemplateResponse(
        "index.html",
        {"request": request}
    )

@router.get("/tools/monitor/dashboard", response_class=HTMLResponse)
async def monitor_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """系统监控仪表板"""
    from common import bi_templates_env
    return bi_templates_env.TemplateResponse(
        "monitor/simple_dashboard.html",
        {"request": request, "title": "系统监控仪表盘"}
    )

@router.get("/api/monitor/system")
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """获取系统状态"""
    try:
        # 检查数据库连接
        result = await db.execute(select(func.count()).select_from(PUEData))
        pue_count = result.scalar()
        
        result = await db.execute(select(func.count()).select_from(FaultRecord))
        fault_count = result.scalar()
        
        return {
            "status": "healthy",
            "database": {
                "status": "connected",
                "pue_records": pue_count,
                "fault_records": fault_count
            },
            "system": {
                "status": "running",
                "uptime": "运行中"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/contract_indicators", response_class=HTMLResponse)
async def contract_indicators(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.type == "contract"))
    zbk_list = result.scalars().all()
    return bi_data_templates_env.TemplateResponse(
        bi_data_templates['contract_indicators'],
        {"request": request, "zbk_list": zbk_list}
    )

@router.get("/add_contract_indicator", response_class=HTMLResponse)
async def add_contract_indicator_form(request: Request):
    return bi_data_templates_env.TemplateResponse(
        bi_data_templates['add_contract_indicator'],
        {"request": request}
    )

@router.post("/add")
async def add_contract_zbk(
        zbx: str = Form(...),
        fz: str = Form(...),
        qspm: str = Form(...),
        qnljdfzb: str = Form(...),
        nddcpg: str = Form(...),
        y1zb: str = Form(...),
        y2zb: str = Form(...),
        y3zb: str = Form(...),
        y4zb: str = Form(...),
        y5zb: str = Form(...),
        y6zb: str = Form(...),
        jzz: str = Form(...),
        tzz: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    new_zbk = Zbk(
        zbx=zbx,
        fz=fz,
        qspm=qspm,
        qnljdfzb=qnljdfzb,
        nddcpg=nddcpg,
        y1zb=y1zb,
        y2zb=y2zb,
        y3zb=y3zb,
        y4zb=y4zb,
        y5zb=y5zb,
        y6zb=y6zb,
        jzz=jzz,
        tzz=tzz,
        type="contract"
    )
    db.add(new_zbk)
    await db.commit()
    return RedirectResponse(url="/contract_indicators", status_code=303)

@router.get("/kpi_indicators", response_class=HTMLResponse)
async def kpi_indicators(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.type == "kpi"))
    kpi_list = result.scalars().all()
    return bi_data_templates_env.TemplateResponse(
        bi_data_templates['kpi_indicators'],
        {"request": request, "kpi_list": kpi_list}
    )

@router.get("/add_kpi_indicator", response_class=HTMLResponse)
async def add_kpi_indicator_form(request: Request):
    return bi_data_templates_env.TemplateResponse(
        bi_data_templates['add_kpi_indicator'],
        {"request": request}
    )

@router.post("/add_kpi")
async def add_kpi_zbk(
        zbx: str = Form(...),
        fz: str = Form(...),
        qspm: str = Form(...),
        qnljdfzb: str = Form(...),
        nddcpg: str = Form(...),
        y1zb: str = Form(...),
        y2zb: str = Form(...),
        y3zb: str = Form(...),
        y4zb: str = Form(...),
        y5zb: str = Form(...),
        y6zb: str = Form(...),
        jzz: str = Form(...),
        tzz: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    new_zbk = Zbk(
        zbx=zbx,
        fz=fz,
        qspm=qspm,
        qnljdfzb=qnljdfzb,
        nddcpg=nddcpg,
        y1zb=y1zb,
        y2zb=y2zb,
        y3zb=y3zb,
        y4zb=y4zb,
        y5zb=y5zb,
        y6zb=y6zb,
        jzz=jzz,
        tzz=tzz,
        type="kpi"
    )
    db.add(new_zbk)
    await db.commit()
    return RedirectResponse(url="/kpi_indicators", status_code=303)

@router.post("/upload-excel")
async def upload_contract_excel(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="仅支持Excel文件格式（.xls, .xlsx）")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        required_columns = ['指标项', '分值', '全省排名', '全年累计得分占比', '年度达成评估',
                            '1月指标', '2月指标', '3月指标', '4月指标', '5月指标', '6月指标', '基准值', '挑战值']
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
            new_zbk = Zbk(
                zbx=str(row[col_mapping['指标项']]),
                fz=str(row[col_mapping['分值']]),
                qspm=str(row[col_mapping['全省排名']]),
                qnljdfzb=str(row[col_mapping['全年累计得分占比']]),
                nddcpg=str(row[col_mapping['年度达成评估']]),
                y1zb=str(row[col_mapping['1月指标']]),
                y2zb=str(row[col_mapping['2月指标']]),
                y3zb=str(row[col_mapping['3月指标']]),
                y4zb=str(row[col_mapping['4月指标']]),
                y5zb=str(row[col_mapping['5月指标']]),
                y6zb=str(row[col_mapping['6月指标']]),
                jzz=str(row[col_mapping['基准值']]),
                tzz=str(row[col_mapping['挑战值']]),
                type="contract"
            )
            db.add(new_zbk)
        await db.commit()
        return RedirectResponse(url="/contract_indicators", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@router.post("/upload-kpi-excel")
async def upload_kpi_excel(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="仅支持Excel文件格式（.xls, .xlsx）")
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        required_columns = ['指标项', '分值', '全省排名', '全年累计得分占比', '年度达成评估',
                            '1月指标', '2月指标', '3月指标', '4月指标', '5月指标', '6月指标', '基准值', '挑战值']
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
            new_zbk = Zbk(
                zbx=str(row[col_mapping['指标项']]),
                fz=str(row[col_mapping['分值']]),
                qspm=str(row[col_mapping['全省排名']]),
                qnljdfzb=str(row[col_mapping['全年累计得分占比']]),
                nddcpg=str(row[col_mapping['年度达成评估']]),
                y1zb=str(row[col_mapping['1月指标']]),
                y2zb=str(row[col_mapping['2月指标']]),
                y3zb=str(row[col_mapping['3月指标']]),
                y4zb=str(row[col_mapping['4月指标']]),
                y5zb=str(row[col_mapping['5月指标']]),
                y6zb=str(row[col_mapping['6月指标']]),
                jzz=str(row[col_mapping['基准值']]),
                tzz=str(row[col_mapping['挑战值']]),
                type="kpi"
            )
            db.add(new_zbk)
        await db.commit()
        return RedirectResponse(url="/kpi_indicators", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@router.get("/edit/{xh}", response_class=HTMLResponse)
async def edit_contract_form(request: Request, xh: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    zbk = result.scalars().first()
    return bi_data_templates_env.TemplateResponse(
        bi_data_templates['edit'],
        {"request": request, "zbk": zbk, "indicator_type": "契约化攻坚", "return_url": "/contract_indicators"}
    )

@router.get("/edit_kpi/{xh}", response_class=HTMLResponse)
async def edit_kpi_form(request: Request, xh: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    zbk = result.scalars().first()
    return bi_data_templates_env.TemplateResponse(
        bi_data_templates['edit'],
        {"request": request, "zbk": zbk, "indicator_type": "KPI", "return_url": "/kpi_indicators"}
    )

@router.post("/edit/{xh}")
async def edit_zbk(
        xh: int,
        zbx: str = Form(...),
        fz: str = Form(...),
        qspm: str = Form(...),
        qnljdfzb: str = Form(...),
        nddcpg: str = Form(...),
        y1zb: str = Form(...),
        y2zb: str = Form(...),
        y3zb: str = Form(...),
        y4zb: str = Form(...),
        y5zb: str = Form(...),
        y6zb: str = Form(...),
        jzz: str = Form(...),
        tzz: str = Form(...),
        indicator_type: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    zbk = result.scalars().first()
    zbk.zbx = zbx
    zbk.fz = fz
    zbk.qspm = qspm
    zbk.qnljdfzb = qnljdfzb
    zbk.nddcpg = nddcpg
    zbk.y1zb = y1zb
    zbk.y2zb = y2zb
    zbk.y3zb = y3zb
    zbk.y4zb = y4zb
    zbk.y5zb = y5zb
    zbk.y6zb = y6zb
    zbk.jzz = jzz
    zbk.tzz = tzz
    await db.commit()
    if indicator_type == "KPI":
        return RedirectResponse(url="/kpi_indicators", status_code=303)
    else:
        return RedirectResponse(url="/contract_indicators", status_code=303)

@router.get("/delete/{xh}")
async def delete_contract_zbk(xh: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    zbk = result.scalars().first()
    await db.delete(zbk)
    await db.commit()
    return RedirectResponse(url="/contract_indicators", status_code=303)

@router.get("/delete_kpi/{xh}")
async def delete_kpi_zbk(xh: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    zbk = result.scalars().first()
    await db.delete(zbk)
    await db.commit()
    return RedirectResponse(url="/kpi_indicators", status_code=303)

@router.get("/api/zbk", response_model=List[dict])
async def get_all_zbk(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk))
    return result.scalars().all()

@router.get("/api/zbk/{xh}", response_model=dict)
async def get_zbk(xh: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    return result.scalars().first()

@router.post("/api/zbk", status_code=201)
async def create_zbk(zbk: ZbkCreate, db: AsyncSession = Depends(get_db)):
    new_zbk = Zbk(**zbk.dict())
    db.add(new_zbk)
    await db.commit()
    return new_zbk

@router.put("/api/zbk/{xh}")
async def update_zbk(xh: int, zbk: ZbkUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    old_zbk = result.scalars().first()
    for k, v in zbk.dict().items():
        if v is not None:
            setattr(old_zbk, k, v)
    await db.commit()
    return old_zbk

@router.delete("/api/zbk/{xh}", status_code=204)
async def delete_zbk_api(xh: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Zbk).where(Zbk.xh == xh))
    zbk = result.scalars().first()
    await db.delete(zbk)
    await db.commit()
    return None

@router.get("/download-template")
async def download_contract_template():
    data = {
        '指标项': ['指标项示例1', '指标项示例2'],
        '分值': ['6', '扣分项'],
        '全省排名': ['5-21', '1-1'],
        '全年累计得分占比': ['95%', '无扣分'],
        '年度达成评估': ['●', '●'],
        '1月指标': ['97%', '0'],
        '2月指标': ['97%', '0'],
        '3月指标': ['97%', '0'],
        '4月指标': ['97%', '0'],
        '5月指标': ['97%', '0'],
        '6月指标': ['97%', '0'],
        '基准值': ['97%', '0'],
        '挑战值': ['97%', '0']
    }
    df = pd.DataFrame(data)
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='契约化攻坚指标数据')
        worksheet = writer.sheets['契约化攻坚指标数据']
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
        headers={"Content-Disposition": f"attachment; filename=contract_indicator_template.xlsx"}
    )

@router.get("/download-kpi-template")
async def download_kpi_template():
    data = {
        '指标项': ['KPI指标示例1', 'KPI指标示例2'],
        '分值': ['6', '扣分项'],
        '全省排名': ['5-21', '1-1'],
        '全年累计得分占比': ['95%', '无扣分'],
        '年度达成评估': ['●', '●'],
        '1月指标': ['97%', '0'],
        '2月指标': ['97%', '0'],
        '3月指标': ['97%', '0'],
        '4月指标': ['97%', '0'],
        '5月指标': ['97%', '0'],
        '6月指标': ['97%', '0'],
        '基准值': ['97%', '0'],
        '挑战值': ['97%', '0']
    }
    df = pd.DataFrame(data)
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='KPI指标数据')
        worksheet = writer.sheets['KPI指标数据']
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
        headers={"Content-Disposition": "attachment; filename=kpi_indicator_template.xlsx"}
    )
