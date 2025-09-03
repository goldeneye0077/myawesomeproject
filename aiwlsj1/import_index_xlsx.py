import asyncio
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from db.models import CenterTopTop, CenterTopBottom, LeftTop, LeftMiddle, RightTop, RightMiddle, Bottom
from db.session import engine
from config import DATABASE_URL

sheet_model_map = {
    'centerTopTop': (CenterTopTop, {
        '类型': 'type',
        '是否达标': 'status',
    }),
    'centerTopBottom': (CenterTopBottom, {
        '区域': 'region',
        '数据': 'value',
        '比例': 'ratio',
    }),
    'leftTop': (LeftTop, {
        '月份': 'month',
        '基准值': 'baseline',
        '挑战值': 'challenge',
        '指标': 'indicator',
    }),
    'leftMiddle': (LeftMiddle, {
        '月份': 'month',
        '基准值': 'baseline',
        '挑战值': 'challenge',
        '指标': 'indicator',
    }),
    'rightTop': (RightTop, {
        '月份': 'month',
        '基准值': 'baseline',
        '挑战值': 'challenge',
        '指标': 'indicator',
    }),
    'rightMiddle': (RightMiddle, {
        '月份': 'month',
        '基准值': 'baseline',
        '挑战值': 'challenge',
        '指标': 'indicator',
    }),
    'bottom': (Bottom, {
        '月份': 'month',
        '基准值': 'baseline',
        '挑战值': 'challenge',
        '蓄电池组总电压采集率': 'battery_voltage_ratio',
        '开关电源负载电流采集率': 'mains_load_ratio',
        'UPS负载电流采集率': 'ups_load_ratio',
        '动环关键信号采集完整率': 'env_signal_ratio',
    }),
}

async def import_sheet(session, df, model, col_map):
    await session.execute(text(f"DELETE FROM {model.__tablename__}"))  # 清空表
    for _, row in df.iterrows():
        data = {col_map[k]: row[k] for k in col_map if k in row and pd.notnull(row[k])}
        obj = model(**data)
        session.add(obj)
    await session.commit()

async def main():
    xls = pd.ExcelFile('data/index.xlsx')
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        for sheet, (model, col_map) in sheet_model_map.items():
            print(f"Importing {sheet} ...")
            df = pd.read_excel(xls, sheet)
            await import_sheet(session, df, model, col_map)
            print(f"{sheet} imported: {len(df)} rows.")
    print("All sheets imported.")

if __name__ == "__main__":
    asyncio.run(main())
