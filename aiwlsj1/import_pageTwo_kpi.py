import os
import openpyxl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import Base, LeftMiddleKPI, CenterMiddleKPI, RightMiddleKPI, LeftBottomKPI, RightBottomKPI, TopKPI
import asyncio

DB_URL = os.getenv('DB_URL', 'sqlite+aiosqlite:///db.sqlite3')
XLSX_PATH = os.path.join('data', 'pageTwo.xlsx')

sheet_model_map = {
    'leftMiddle_kpi': (LeftMiddleKPI, ['month', 'baseline', 'challenge', 'offline_duration', 'year']),
    'centerMiddle_kpi': (CenterMiddleKPI, ['month', 'baseline', 'challenge', 'broadband_rate', 'delivery_rate', 'year']),
    'rightMiddle_kpi': (RightMiddleKPI, ['month', 'baseline', 'challenge', 'r_and_d_completion', 'year']),
    'leftBottom_kpi': (LeftBottomKPI, ['indicator', 'baseline', 'challenge', 'current', 'year']),
    'rightBottom_kpi': (RightBottomKPI, ['month', 'baseline', 'challenge', 'broadband_rate', 'year']),
    'top_kpi': (TopKPI, ['type', 'status', 'year']),
}

async def migrate_and_import():
    engine = create_async_engine(DB_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    wb = openpyxl.load_workbook(XLSX_PATH)
    async with async_session() as session:
        for sheet, (Model, fields) in sheet_model_map.items():
            ws = wb[sheet]
            rows = list(ws.iter_rows(min_row=2, values_only=True))
            for row in rows:
                data = {}
                for i, field in enumerate(fields):
                    if i < len(row):
                        data[field] = row[i]
                obj = Model(**data)
                session.add(obj)
        await session.commit()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_and_import())
