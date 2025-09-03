import asyncio
from db.models import Base
from db.session import engine

async def recreate():
    async with engine.begin() as conn:
        print('Dropping all tables...')
        await conn.run_sync(Base.metadata.drop_all)
        print('Creating all tables...')
        await conn.run_sync(Base.metadata.create_all)
        print('All tables recreated.')

if __name__ == "__main__":
    asyncio.run(recreate())
