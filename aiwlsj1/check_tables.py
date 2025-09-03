from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import inspect
from config import DATABASE_URL
import asyncio

async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        def get_tables(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_table_names()
        tables = await conn.run_sync(get_tables)
        print("数据库中的所有表：", tables)

if __name__ == "__main__":
    asyncio.run(main())
