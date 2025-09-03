from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Huijugugan
from fastapi.staticfiles import StaticFiles
from db.session import engine, get_db
from db.models import Base
from bi import router as bi_router
from pue import router as pue_router
from huijugugan import router as huiju_router
from bi_data_manage import router as bi_data_manage_router
from bi_api import router as bi_api_router
from fault_analysis_fastapi import router as fault_router
import os

# 创建FastAPI应用
app = FastAPI(title="指标管理系统")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置Jinja2模板目录 
templates = Jinja2Templates(directory="templates")

# 根路由由 bi_data_manage.py 中处理

# 汇聚骨干多维表分析页

# 注册各业务路由
app.include_router(bi_data_manage_router)
app.include_router(bi_router)
app.include_router(pue_router)
app.include_router(huiju_router)
app.include_router(bi_api_router)
app.include_router(fault_router)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)