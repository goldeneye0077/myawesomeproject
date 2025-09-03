import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import PUEData, Base
from datetime import datetime
import os

DATA = {
    "龙岗": {
        "2024": [1.05, 1.21, 1.19, 1.05, 1.13, 1.16, 1.18, 1.21, 1.19, 1.14, 1.14, 1.14],
        "2025": [1.23, 1.19, 1.17, 1.23, 1.18, 1.13, 1.18, 1.23, 1.18, 1.25, 1.25, 1.25]
    },
    "坂田": {
        "2024": [1.33, 1.19, 1.14, 1.18, 1.15, 1.18, 1.18, 1.18, 1.19, 1.18, 1.18, 1.18],
        "2025": [1.48, 1.41, 1.37, 1.41, 1.37, 1.35, 1.35, 1.31, 1.31, 1.31, 1.31, 1.31]
    },
    "西丽": {
        "2024": [1.27, 1.46, 1.41, 1.27, 1.25, 1.25, 1.25, 1.25, 1.25, 1.34, 1.34, 1.34],
        "2025": [1.45, 1.41, 1.39, 1.41, 1.41, 1.41, 1.41, 1.41, 1.41, 1.34, 1.34, 1.34]
    },
    "宝城": {
        "2024": [1.25, 1.19, 1.15, 1.25, 1.19, 1.23, 1.23, 1.23, 1.23, 1.18, 1.18, 1.18],
        "2025": [1.39, 1.19, 1.17, 1.19, 1.19, 1.19, 1.19, 1.19, 1.19, 1.18, 1.18, 1.18]
    },
    "南科": {
        "2024": [1.23, 1.19, 1.15, 1.23, 1.19, 1.23, 1.23, 1.23, 1.23, 1.18, 1.18, 1.18],
        "2025": [1.25, 1.19, 1.17, 1.19, 1.19, 1.19, 1.19, 1.19, 1.19, 1.18, 1.18, 1.18]
    },
    "宝观一": {
        "2024": [1.23, 1.21, 1.21, 1.23, 1.23, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27],
        "2025": [1.47, 1.34, 1.32, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47]
    },
    "宝观二": {
        "2024": [1.25, 1.32, 1.34, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27],
        "2025": [1.45, 1.32, 1.28, 1.45, 1.45, 1.45, 1.45, 1.45, 1.45, 1.45, 1.45, 1.45]
    },
    "国通": {
        "2024": [1.42, 1.42, 1.42, 1.42, 1.42, 1.42, 1.42, 1.42, 1.42, 1.22, 1.22, 1.22],
        "2025": [1.39, 1.42, 1.42, 1.39, 1.39, 1.39, 1.39, 1.39, 1.39, 1.22, 1.22, 1.22]
    },
    "罗湖邮政": {
        "2024": [1.29, 1.29, 1.29, 1.29, 1.29, 1.29, 1.29, 1.29, 1.29, 1.27, 1.27, 1.27],
        "2025": [1.17, 1.17, 1.17, 1.17, 1.17, 1.17, 1.17, 1.17, 1.17, 1.27, 1.27, 1.27]
    },
    "宝安邮政": {
        "2024": [1.32, 1.39, 1.39, 1.32, 1.32, 1.32, 1.32, 1.32, 1.32, 1.40, 1.40, 1.40],
        "2025": [1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.47, 1.40, 1.40, 1.40]
    }
}

MONTHS = [str(i) for i in range(1, 13)]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def insert_pue_data(session: AsyncSession):
    for location, years in DATA.items():
        for year, values in years.items():
            for i, pue_value in enumerate(values):
                obj = PUEData(
                    location=location,
                    year=year,
                    month=MONTHS[i],
                    pue_value=pue_value,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(obj)
    await session.commit()

async def run():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await insert_pue_data(session)

if __name__ == '__main__':
    asyncio.run(run())
