import os
import sys
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.session import get_db
from db.models import CenterTopTop, CenterTopBottom, LeftTop, LeftMiddle, RightTop, RightMiddle, Bottom
from common import bi_templates, bi_templates_env

router = APIRouter()

root_path = os.getcwd()
sys.path.append(root_path)
current_file = os.path.abspath(sys.argv[0])
current_dir = os.path.dirname(current_file)

async def read_img(item, img):
    img_path = current_dir + '/img/{}/{}'.format(item, img)
    with open(img_path, 'rb') as frb:
        res_body = frb.read()
    return Response(res_body)

@router.get("/bi", response_class=HTMLResponse)
async def bi(request: Request, db: AsyncSession = Depends(get_db)):
    # 查询所有大屏需要的数据
    center_top_top = (await db.execute(select(CenterTopTop))).scalars().all()
    center_top_bottom = (await db.execute(select(CenterTopBottom))).scalars().all()
    left_top = (await db.execute(select(LeftTop))).scalars().all()
    left_middle = (await db.execute(select(LeftMiddle))).scalars().all()
    right_top = (await db.execute(select(RightTop))).scalars().all()
    right_middle = (await db.execute(select(RightMiddle))).scalars().all()
    bottom = (await db.execute(select(Bottom))).scalars().all()

    # 组装模板上下文
    return bi_templates_env.TemplateResponse(
        bi_templates['index1'],
        {
            "request": request,
            "center_top_top": center_top_top,
            "center_top_bottom": center_top_bottom,
            "left_top": left_top,
            "left_middle": left_middle,
            "right_top": right_top,
            "right_middle": right_middle,
            "bottom": bottom,
        }
    )

@router.get("/img/{item}/{img}")
async def send_img(item, img):
    ret = await read_img(item=item, img=img)
    return ret

@router.get("/bi2", response_class=HTMLResponse)
async def bi2(request: Request):
    return bi_templates_env.TemplateResponse(
        bi_templates['index2'],
        {"request": request}
    )
