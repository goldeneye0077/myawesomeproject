from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.models import CenterTopTop, CenterTopBottom, LeftTop, LeftMiddle, RightTop, RightMiddle, Bottom, LeftMiddleKPI, CenterMiddleKPI, RightMiddleKPI, LeftBottomKPI, RightBottomKPI, TopKPI
from db.session import get_db

router = APIRouter()

@router.get('/api/bi_data')
async def get_bi_data(session: AsyncSession = Depends(get_db)):
    def to_list(result, fields):
        return [[getattr(row, f) for f in fields] for row in result.scalars().all()]

    center_top_top = await session.execute(select(CenterTopTop))
    center_top_bottom = await session.execute(select(CenterTopBottom))
    left_top = await session.execute(select(LeftTop))
    left_middle = await session.execute(select(LeftMiddle))
    right_top = await session.execute(select(RightTop))
    right_middle = await session.execute(select(RightMiddle))
    bottom = await session.execute(select(Bottom))
    left_middle_kpi = await session.execute(select(LeftMiddleKPI))
    center_middle_kpi = await session.execute(select(CenterMiddleKPI))
    right_middle_kpi = await session.execute(select(RightMiddleKPI))
    left_bottom_kpi = await session.execute(select(LeftBottomKPI))
    right_bottom_kpi = await session.execute(select(RightBottomKPI))
    top_kpi = await session.execute(select(TopKPI))

    return {
        "centerTopTopData": to_list(center_top_top, ["type", "status"]),
        "centerTopBottomData": to_list(center_top_bottom, ["region", "value", "ratio"]),
        "leftTopData": to_list(left_top, ["month", "baseline", "challenge", "indicator"]),
        "leftMiddleData": to_list(left_middle, ["month", "baseline", "challenge", "indicator"]),
        "centerMiddleData": to_list(center_middle_kpi, ["month", "baseline", "challenge", "broadband_rate", "delivery_rate", "year"]),
        "rightMiddleData": to_list(right_middle, ["month", "baseline", "challenge", "indicator"]),
        "rightMiddleKPIData": to_list(right_middle_kpi, ["month", "baseline", "challenge", "r_and_d_completion", "year"]),
        "rightTopData": to_list(right_top, ["month", "baseline", "challenge", "indicator"]),
        "leftBottomData": to_list(left_bottom_kpi, ["indicator", "baseline", "challenge", "current", "year"]),
        "rightBottomData": to_list(right_bottom_kpi, ["month", "baseline", "challenge", "broadband_rate", "year"]),
        "bottomData": to_list(bottom, ["month", "baseline", "challenge", "battery_voltage_ratio", "mains_load_ratio", "ups_load_ratio", "env_signal_ratio"]),
        "topData": to_list(top_kpi, ["type", "status", "year"]),
    }
