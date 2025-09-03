from fastapi import APIRouter, Request, Form, HTTPException, Depends, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi import status
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from db.models import Huijugugan
from common import bi_templates_env
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import distinct, func, and_
from db.session import get_db
import pandas as pd
from io import BytesIO
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import calendar

from fastapi.templating import Jinja2Templates
import requests
router = APIRouter(prefix="/huiju", tags=["汇聚骨干指标管理"])
templates = Jinja2Templates(directory="templates")

def analyze_and_predict_with_deepseek(df, city=None, max_rounds=3):
    api_url = "https://DeepSeek-R1-wzrba.eastus2.models.ai.azure.com/chat/completions"
    api_key = "HyYc4J6EcwlktQLXMcXQJNAtkRgioiqi"
    prompt = f"请对如下{('城市：'+city) if city else '全部城市'}的汇聚骨干指标数据进行简要分析、总结规律，并预测未来几个月的趋势：\n{df.to_string(index=False)}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = [{"role": "user", "content": prompt}]
    all_content = ""
    for i in range(max_rounds):
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7
        }
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            all_content += content
            # 若本轮返回内容已很短或出现结束标志，则停止
            if len(content) < 900 or "已完成" in content or "END" in content:
                break
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "请继续输出剩余内容"})
        except Exception as e:
            all_content += f"\n[AI分析补全失败：{e}]"
            break
    import re
    # 去除<think>...</think>标签及其内容
    cleaned_content = re.sub(r'<think>[\s\S]*?</think>', '', all_content)
    # 去除多余的markdown符号（#、*、-、>等行首符号）
    cleaned_content = re.sub(r'^[#>*\-\s]+', '', cleaned_content, flags=re.MULTILINE)
    # 去除所有*字符
    cleaned_content = cleaned_content.replace('*', '')
    return cleaned_content.strip()

from fastapi.responses import JSONResponse

@router.get("/ai_analysis")
async def get_ai_analysis(city: str = None, db: AsyncSession = Depends(get_db)):
    # 查询所有城市和数据
    result = await db.execute(select(Huijugugan))
    data = result.scalars().all()
    if not data:
        return JSONResponse(content={"ai_analysis": "暂无数据"})
    df_data = []
    for item in data:
        df_data.append({
            "month": item.month,
            "city": item.city,
            "huiju_amount": item.huiju_amount,
            "over_4h": item.over_4h,
            "over_4h_ratio": item.over_4h / item.huiju_amount if item.huiju_amount > 0 else 0,
            "important_amount": item.important_amount,
            "over_12h": item.over_12h,
            "over_12h_ratio": item.over_12h / item.important_amount if item.important_amount > 0 else 0
        })
    import pandas as pd
    df = pd.DataFrame(df_data)
    ai_analysis = analyze_and_predict_with_deepseek(df if not city else df[df['city'] == city], city)
    return JSONResponse(content={"ai_analysis": ai_analysis})

@router.get("/analyze")
async def huiju_analyze(request: Request, city: str = None, db: AsyncSession = Depends(get_db)):
    # 查询所有城市和数据
    result = await db.execute(select(Huijugugan))
    data = result.scalars().all()
    all_cities = sorted(set(item.city for item in data))
    if not data:
        return bi_templates_env.TemplateResponse(
            "huiju_analyze.html",
            {
                "request": request,
                "all_cities": all_cities,
                "current_city": city,
                "no_data": True
            }
        )
    # 准备DataFrame
    df_data = []
    for item in data:
        df_data.append({
            "month": item.month,
            "city": item.city,
            "huiju_amount": item.huiju_amount,
            "over_4h": item.over_4h,
            "over_4h_ratio": item.over_4h / item.huiju_amount if item.huiju_amount > 0 else 0,
            "important_amount": item.important_amount,
            "over_12h": item.over_12h,
            "over_12h_ratio": item.over_12h / item.important_amount if item.important_amount > 0 else 0
        })
    import pandas as pd
    df = pd.DataFrame(df_data)
    from pyecharts.charts import Bar, Line, Grid
    from pyecharts import options as opts
    from pyecharts.globals import ThemeType
    from pyecharts.commons.utils import JsCode
    from pyecharts.render import make_snapshot
    # 柱状图
    # 保证 months 和 cities 在所有分支都可用，并固定城市顺序
    months = sorted(df['month'].unique())
    # 固定城市顺序：深圳、广州、东莞、佛山
    city_order = ['深圳', '广州', '东莞', '佛山']
    cities = [city for city in city_order if city in df['city'].unique()]  # 只保留数据中存在的城市
    # 生成pivot_data和table_cities
    pivot_data = {}
    if city:
        table_cities = [city]
    else:
        table_cities = cities
    for m in months:
        pivot_data[m] = {}
        if city:
            for field in ["huiju_amount", "over_4h", "important_amount", "over_12h"]:
                key = f"{field}|{city}"
                value = float(df[(df['month'] == m) & (df['city'] == city)][field].values[0]) if not df[(df['month'] == m) & (df['city'] == city)].empty else 0
                pivot_data[m][key] = value
        else:
            for city_name in cities:
                for field in ["huiju_amount", "over_4h", "important_amount", "over_12h"]:
                    key = f"{field}|{city_name}"
                    value = float(df[(df['month'] == m) & (df['city'] == city_name)][field].values[0]) if not df[(df['month'] == m) & (df['city'] == city_name)].empty else 0
                    pivot_data[m][key] = value
    # AI分析（已移至异步接口，不在主内容渲染时调用）
    # ai_analysis = analyze_and_predict_with_deepseek(df if not city else df[df['city'] == city], city)
    # ↓↓↓ 下面保持原有流程 ↓↓↓
    if city:
        # 单城市分组柱状图 - 增大图表尺寸
        bar = Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="546px"))
        bar.add_xaxis(months)
        colors = ["#3498db", "#2ecc71", "#e74c3c", "#9b59b6"]
        for field, name, color in zip(
            ["huiju_amount", "over_4h", "important_amount", "over_12h"],
            ["汇聚总量", "超4小时", "重要紧急", "超12小时"],
            colors
        ):
            y = [float(df[(df['month'] == m) & (df['city'] == city)][field].values[0]) if not df[(df['month'] == m) & (df['city'] == city)].empty else 0 for m in months]
            bar.add_yaxis(name, y, stack=None, itemstyle_opts=opts.ItemStyleOpts(color=color))
        bar.set_series_opts(label_opts=opts.LabelOpts(is_show=False))
        bar.set_global_opts(
            title_opts=opts.TitleOpts(title=f"{city} - 多系列对比柱状图", pos_top="1%"),
            xaxis_opts=opts.AxisOpts(type_="category", name="月份", axislabel_opts=opts.LabelOpts(rotate=45)),
            yaxis_opts=opts.AxisOpts(name="数量"),
            legend_opts=opts.LegendOpts(pos_top="5%")
        )
        # 设置图表网格布局（如无缩放条可适当减小底部间距）
        bar.options["grid"] = {"top": "15%", "bottom": "12%"}
        bar_chart = bar.render_embed()
        # 折线图
        line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="320px"))
        line.add_xaxis(months)
        line.add_yaxis("超4小时比例", [float(df[df['month'] == m]['over_4h_ratio'].values[0]) if not df[df['month'] == m].empty else 0 for m in months], is_smooth=True)
        line.set_global_opts(title_opts=opts.TitleOpts(title=f"{city} - 超4小时比例"), yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(formatter="{value}%")))
        line_chart = line.render_embed()
        line2 = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="320px"))
        line2.add_xaxis(months)
        line2.add_yaxis("超12小时比例", [float(df[df['month'] == m]['over_12h_ratio'].values[0]) if not df[df['month'] == m].empty else 0 for m in months], is_smooth=True)
        line2.set_global_opts(title_opts=opts.TitleOpts(title=f"{city} - 重要环超12小时比例"), yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(formatter="{value}%")))
        important_chart = line2.render_embed()
    else:
        # 全部城市：同一坐标轴下4个城市并列对比分组柱状图 - 增大图表尺寸
        bar = Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="546px"))
        bar.add_xaxis(months)
        colors = ["#3498db", "#2ecc71", "#e74c3c", "#9b59b6"]
        for field, name, color in zip(
            ["huiju_amount", "over_4h", "important_amount", "over_12h"],
            ["汇聚总量", "超4小时", "重要紧急", "超12小时"],
            colors
        ):
            for city_name in cities:
                y = [float(df[(df['month'] == m) & (df['city'] == city_name)][field].values[0]) if not df[(df['month'] == m) & (df['city'] == city_name)].empty else 0 for m in months]
                bar.add_yaxis(f"{city_name}-{name}", y, stack=None, itemstyle_opts=opts.ItemStyleOpts(color=color))
        bar.set_series_opts(label_opts=opts.LabelOpts(is_show=False))
        bar.set_global_opts(
            title_opts=opts.TitleOpts(title="多城市对比", pos_top="1%"),
            xaxis_opts=opts.AxisOpts(
                type_="category", 
                name="月份", 
                axislabel_opts=opts.LabelOpts(rotate=45, interval=0),
                axisline_opts=opts.AxisLineOpts(is_show=True),
                splitline_opts=opts.SplitLineOpts(is_show=True)
            ),
            yaxis_opts=opts.AxisOpts(
                name="数量",
                axisline_opts=opts.AxisLineOpts(is_show=True),
                splitline_opts=opts.SplitLineOpts(is_show=True)
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_top="5%",
                pos_bottom="5%",
                orient="horizontal",
                align="left"
            ),

        )
        # 设置图表网格布局，增加底部和顶部间距
        bar.options["grid"] = {
            "top": "15%",
            "bottom": "30%",
            "left": "2%",
            "right": "0%",
            "containLabel": True
        }
        bar_chart = bar.render_embed()
        # 多城市折线图
        line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1200px", height="400px"))
        line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="320px"))
        line.add_xaxis(months)
        for city_name in cities:
            city_df = df[df['city'] == city_name]
            y = [float(city_df[city_df['month'] == m]['over_4h_ratio'].values[0]) if not city_df[city_df['month'] == m].empty else 0 for m in months]
            line.add_yaxis(city_name, y, is_smooth=True)
        line.set_global_opts(title_opts=opts.TitleOpts(title="全部城市 - 超4小时比例"), yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(formatter="{value}%")))
        line_chart = line.render_embed()
        line2 = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="320px"))
        line2.add_xaxis(months)
        for city_name in cities:
            city_df = df[df['city'] == city_name]
            y = [float(city_df[city_df['month'] == m]['over_12h_ratio'].values[0]) if not city_df[city_df['month'] == m].empty else 0 for m in months]
            line2.add_yaxis(city_name, y, is_smooth=True)
        line2.set_global_opts(title_opts=opts.TitleOpts(title="全部城市 - 重要环超12小时比例"), yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(formatter="{value}%")))
        important_chart = line2.render_embed()


    # 新预警逻辑：深圳任一指标大于广州则该月预警（红）
    red_months = []
    yellow_months = []
    green_months = []
    if '深圳' in cities and '广州' in cities:
        for m in months:
            sz_row = df[(df['city'] == '深圳') & (df['month'] == m)]
            gz_row = df[(df['city'] == '广州') & (df['month'] == m)]
            if not sz_row.empty and not gz_row.empty:
                sz = sz_row.iloc[0]
                gz = gz_row.iloc[0]
                for col in ['huiju_amount', 'over_4h', 'important_amount', 'over_12h']:
                    if float(sz[col]) > float(gz[col]):
                        red_months.append(m)
                        break
    # 只显示红色预警，其他不显示
    yellow_months = []
    green_months = []
    # 多维表数据
    pivot_df = df.pivot_table(
        index='month',
        columns='city',
        values=['huiju_amount', 'over_4h', 'over_4h_ratio', 'important_amount', 'over_12h', 'over_12h_ratio'],
        aggfunc='first'
    )
    months = sorted(df['month'].unique())
    cities = sorted(df['city'].unique())
    # 修正：pivot_data的key转为字符串，避免前端序列化报错
    pivot_data_raw = pivot_df.to_dict(orient='index') if not pivot_df.empty else {}
    pivot_data = {}
    for month, row in pivot_data_raw.items():
        pivot_data[month] = {}
        for k, v in row.items():
            if isinstance(k, tuple):
                key_str = '|'.join(map(str, k))
            else:
                key_str = str(k)
            pivot_data[month][key_str] = v
    # 深圳折线图（右侧专用）
    shenzhen_line_chart = ""
    if '深圳' in cities:
        shenzhen_df = df[df['city'] == '深圳']
        if not shenzhen_df.empty:
            from pyecharts.charts import Line
            from pyecharts import options as opts
            shenzhen_line = Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="330px"))
            shenzhen_line.add_xaxis(months)
            # 四条数据线：汇聚总量、超4小时、重要紧急、超12小时
            fields = [
                ("huiju_amount", "汇聚总量"),
                ("over_4h", "超4小时"),
                ("important_amount", "重要紧急"),
                ("over_12h", "超12小时")
            ]
            for field, name in fields:
                y = [float(shenzhen_df[shenzhen_df['month'] == m][field].values[0]) if not shenzhen_df[shenzhen_df['month'] == m].empty else 0 for m in months]
                shenzhen_line.add_yaxis(name, y, is_smooth=True)
            shenzhen_line.set_global_opts(title_opts=opts.TitleOpts(title="深圳汇聚数据趋势", pos_top="2%", pos_left="center", title_textstyle_opts=opts.TextStyleOpts(font_size=13)),
                                          xaxis_opts=opts.AxisOpts(type_="category", name="月份", axislabel_opts=opts.LabelOpts(rotate=0)),
                                          yaxis_opts=opts.AxisOpts(name="数量"),
                                          legend_opts=opts.LegendOpts(pos_top="10%"))
            shenzhen_line.options["grid"] = {"top": "20%", "bottom": "18%", "left": "8%", "right": "4%", "containLabel": True}
            shenzhen_line_chart = shenzhen_line.render_embed()

    return bi_templates_env.TemplateResponse(
        "huiju_analyze.html",
        {
            "request": request,
            "all_cities": all_cities,
            "current_city": city,
            "bar_chart": bar_chart,
            "line_chart": line_chart,
            "important_chart": important_chart,
            "red_months": red_months,
            "yellow_months": yellow_months,
            "green_months": green_months,
            "months": months,
            "cities": table_cities,
            "shenzhen_line_chart": shenzhen_line_chart,
            "pivot_data": pivot_data,
            "no_data": False,
        }
    )

@router.delete("/data/delete/{id}")
async def delete_huiju_data(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Huijugugan).where(Huijugugan.id == id))
    item = result.scalar_one_or_none()
    if not item:
        return {"success": False, "message": "数据不存在"}
    await db.delete(item)
    await db.commit()
    return {"success": True}

class HuijuguganCreate(BaseModel):
    month: str
    city: str
    huiju_amount: int
    over_4h: int
    important_amount: int
    over_12h: int

class HuijuguganUpdate(BaseModel):
    month: Optional[str] = None
    city: Optional[str] = None
    huiju_amount: Optional[int] = None
    over_4h: Optional[int] = None
    important_amount: Optional[int] = None
    over_12h: Optional[int] = None


@router.get("/data", response_class=HTMLResponse)
async def huiju_data_page(request: Request, page: int = 1, city: str = None, month: str = None, db: AsyncSession = Depends(get_db)):
    """汇聚骨干指标数据管理页面"""
    PAGE_SIZE = 10
    # 查询所有城市
    result = await db.execute(select(distinct(Huijugugan.city)))
    all_cities = [row[0] for row in result.all()]
    # 查询所有月份
    result = await db.execute(select(distinct(Huijugugan.month)))
    all_months = [row[0] for row in result.all()]
    # 构建查询
    query = select(Huijugugan)
    if city:
        query = query.where(Huijugugan.city == city)
    if month:
        query = query.where(Huijugugan.month == month)
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else 1
    if page < 1:
        page = 1
    if pages > 0 and page > pages:
        page = pages
    elif pages == 0:
        page = 1
    paged_query = query.order_by(Huijugugan.created_at.desc()).offset((page-1)*PAGE_SIZE).limit(PAGE_SIZE)
    result = await db.execute(paged_query)
    huijugugan_list = result.scalars().all()
    return bi_templates_env.TemplateResponse(
        "huiju_data.html",
        {
            "request": request,
            "items": huijugugan_list,
            "page": page,
            "pages": pages,
            "total": total,
            "all_cities": all_cities,
            "all_months": all_months,
            "current_city": city,
            "current_month": month,
            "pagination": {
                "page": page,
                "pages": pages,
                "has_prev": page > 1,
                "has_next": page < pages,
                "prev_num": page - 1 if page > 1 else None,
                "next_num": page + 1 if page < pages else None,
                "iter_pages": range(1, pages + 1)
            }
        }
    )

@router.get("/data/add", response_class=HTMLResponse)
async def add_huiju_form(request: Request):
    """添加汇聚骨干数据表单"""
    return bi_templates_env.TemplateResponse("add_huiju.html", {"request": request})

@router.post("/data/add")
async def add_huijugugan(
    month: str = Form(...),
    city: str = Form(...),
    huiju_amount: int = Form(...),
    over_4h: int = Form(...),
    important_amount: int = Form(...),
    over_12h: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    new_data = Huijugugan(
        month=month,
        city=city,
        huiju_amount=huiju_amount,
        over_4h=over_4h,
        important_amount=important_amount,
        over_12h=over_12h
    )
    db.add(new_data)
    await db.commit()
    return RedirectResponse(url="/huijugugan", status_code=303)

@router.get("/data/edit/{id}", response_class=HTMLResponse)
async def edit_huiju_form(request: Request, id: int, db: AsyncSession = Depends(get_db)):
    """编辑汇聚骨干数据表单"""
    result = await db.execute(select(Huijugugan).where(Huijugugan.id == id))
    huijugugan = result.scalar_one_or_none()
    if not huijugugan:
        raise HTTPException(status_code=404, detail="数据不存在")
    return bi_templates_env.TemplateResponse("edit_huiju.html", {"request": request, "item": huijugugan})

@router.post("/data/edit/{id}")
async def update_huiju_data(
    id: int,
    month: str = Form(...),
    city: str = Form(...),
    huiju_amount: int = Form(...),
    over_4h: int = Form(...),
    important_amount: int = Form(...),
    over_12h: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """更新汇聚骨干数据"""
    result = await db.execute(select(Huijugugan).where(Huijugugan.id == id))
    huijugugan = result.scalar_one_or_none()
    if not huijugugan:
        raise HTTPException(status_code=404, detail="数据不存在")
    
    # 更新数据
    huijugugan.month = month
    huijugugan.city = city
    huijugugan.huiju_amount = huiju_amount
    huijugugan.over_4h = over_4h
    huijugugan.important_amount = important_amount
    huijugugan.over_12h = over_12h
    
    await db.commit()
    return RedirectResponse(url="/huiju/data", status_code=303)
@router.get("/analyze", response_class=HTMLResponse)
async def huiju_analyze(
    request: Request, 
    city: str = None, 
    db: AsyncSession = Depends(get_db)
):
    """汇聚骨干指标数据分析页面"""
    # 获取所有城市
    result = await db.execute(select(distinct(Huijugugan.city)))
    all_cities = [row[0] for row in result.all() if row[0]]
    
    # 构建查询
    query = select(Huijugugan)
    if city:
        query = query.where(Huijugugan.city == city)
    
    # 获取数据
    result = await db.execute(query.order_by(Huijugugan.month, Huijugugan.city))
    data = result.scalars().all()
    
    if not data:
        return bi_templates_env.TemplateResponse(
            "huiju_analyze.html",
            {
                "request": request,
                "all_cities": all_cities,
                "current_city": city,
                "no_data": True
            }
        )
    
    # 准备数据
    df_data = []
    for item in data:
        df_data.append({
            "month": item.month,
            "city": item.city,
            "huiju_amount": item.huiju_amount,
            "over_4h": item.over_4h,
            "over_4h_ratio": item.over_4h / item.huiju_amount if item.huiju_amount > 0 else 0,
            "important_amount": item.important_amount,
            "over_12h": item.over_12h,
            "over_12h_ratio": item.over_12h / item.important_amount if item.important_amount > 0 else 0
        })
    
    df = pd.DataFrame(df_data)
    
    # 创建图表
    # 1. 多系列对比柱状图
    # melt数据，得到每个城市、月份、指标的值
    df_melted = df.melt(id_vars=["month", "city"], value_vars=["huiju_amount", "over_4h", "important_amount", "over_12h"], 
                        var_name="指标", value_name="数值")
    fig = px.bar(
        df_melted,
        x="month",
        y="数值",
        color="指标",
        barmode="group",
        facet_col="city",
        category_orders={"指标": ["huiju_amount", "over_4h", "important_amount", "over_12h"]},
        labels={"month": "月份", "数值": "数量", "city": "城市", "指标": "指标"},
        title=f"{city if city else '全部城市'} - 多系列对比柱状图"
    )
    bar_chart = fig.to_html(full_html=False)
    
    # 2. 超4小时比例折线图
    fig_line = px.line(
        df,
        x="month",
        y="over_4h_ratio",
        color="city",
        title=f"{city if city else '全部城市'} - 超4小时比例",
        labels={"month": "月份", "over_4h_ratio": "超4小时比例", "city": "城市"}
    )
    line_chart = fig_line.to_html(full_html=False)
    
    # 3. 重要环超12小时比例折线图
    fig_important = px.line(
        df,
        x="month",
        y="over_12h_ratio",
        color="city",
        title=f"{city if city else '全部城市'} - 重要环超12小时比例",
        labels={"month": "月份", "over_12h_ratio": "超12小时比例", "city": "城市"}
    )
    important_chart = fig_important.to_html(full_html=False)
    
    # 4. 红绿灯预警
    red_months = []
    yellow_months = []
    green_months = []
    
    # 这里可以根据业务逻辑设置红绿灯规则
    # 示例：超4小时比例>10%为红灯，>5%为黄灯，其他为绿灯
    for _, row in df.iterrows():
        if row['over_4h_ratio'] > 0.1:  # 10%
            red_months.append(row['month'])
        elif row['over_4h_ratio'] > 0.05:  # 5%
            yellow_months.append(row['month'])
        else:
            green_months.append(row['month'])
    
    # 5. 创建多维数据表
    # 按城市和月份透视数据
    pivot_df = df.pivot_table(
        index='month',
        columns='city',
        values=['huiju_amount', 'over_4h', 'over_4h_ratio', 'important_amount', 'over_12h', 'over_12h_ratio'],
        aggfunc='first'
    )
    
    # 准备多维表数据
    months = sorted(df['month'].unique())
    cities = sorted(df['city'].unique())
    
    # 确保城市顺序一致
    city_order = ['深圳', '广州', '东莞', '佛山']
    # 重新排序all_cities
    all_cities = [city for city in city_order if city in set(all_cities)]
    # 重新排序cities
    cities = [city for city in city_order if city in set(cities)]
    # 重新排序透视表数据
    if not pivot_df.empty:
        pivot_df = pivot_df.reindex(columns=city_order, level=1)
    
    # 渲染模板（不传递任何AI分析相关变量，主内容“秒开”）
    return bi_templates_env.TemplateResponse(
        "huiju_analyze.html",
        {
            "request": request,
            "all_cities": all_cities,
            "current_city": city,
            "bar_chart": bar_chart,
            "line_chart": line_chart,
            "important_chart": important_chart,
            "red_months": red_months,
            "yellow_months": yellow_months,
            "green_months": green_months,
            "months": months,
            "cities": cities,
            "pivot_data": pivot_df.to_dict(orient='index') if not pivot_df.empty else {},
            "no_data": False
        }
    )
