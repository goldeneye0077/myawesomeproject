from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import Huijugugan, Base
from datetime import datetime
import asyncio

# 请根据实际数据库配置修改
DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # 如果是MySQL/Postgres请改为对应格式

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def insert_sample():
    async with AsyncSessionLocal() as session:
        sample = Huijugugan(
            month="2404",
            city="深圳",
            huiju_amount=73,
            over_4h=0,
            important_amount=435,
            over_12h=8,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(sample)
        await session.commit()
        print("插入成功")

if __name__ == "__main__":
    asyncio.run(insert_sample())
