"""
故障指标数据分析辅助函数
包含图表生成、数据统计和AI分析功能
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie, Line
from pyecharts.globals import ThemeType, CurrentConfig

# 使用本地静态资源，避免从外网加载 ECharts（解决慢/失败问题）
CurrentConfig.ONLINE_HOST = "/static/js/"

# 简单的内存缓存
_cache = {}

def _aggregate_pie_data(counts_dict, top_n=10):
    """将类别过多的数据聚合，保留前 top_n，其余合并为“其他”以提升渲染性能"""
    try:
        items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
        if len(items) <= top_n:
            return items
        top_items = items[:top_n]
        other_sum = sum(v for _, v in items[top_n:])
        if other_sum > 0:
            top_items.append(("其他", other_sum))
        return top_items
    except Exception:
        # 兜底，出现异常则直接返回原始数据
        return list(counts_dict.items())

def clear_cache():
    """清理缓存"""
    global _cache
    _cache.clear()

def get_cache_info():
    """获取缓存信息"""
    return {"cache_keys": list(_cache.keys()), "cache_size": len(_cache)}

async def get_distinct_values(db: AsyncSession, column):
    """获取列的去重值（带缓存）"""
    try:
        # 使用列名作为缓存键
        cache_key = f"distinct_{column.name}"
        
        # 检查缓存
        if cache_key in _cache:
            return _cache[cache_key]
        
        # 查询数据库
        result = await db.execute(
            select(func.distinct(column))
            .where(column.isnot(None))
            .where(column != '')
            .limit(100)  # 限制结果数量
        )
        values = [row[0] for row in result.fetchall() if row[0] and str(row[0]).strip()]
        sorted_values = sorted(values)
        
        # 缓存结果
        _cache[cache_key] = sorted_values
        return sorted_values
    except Exception:
        return []

def generate_fault_trend_chart(fault_records):
    """生成故障趋势图表（优化版）"""
    try:
        if not fault_records:
            return "<div style='text-align: center; padding: 40px; color: #666;'>暂无数据</div>"
        
        # 限制处理数据量以提高性能
        if len(fault_records) > 500:
            fault_records = fault_records[:500]
        
        # 按月统计故障数量
        monthly_data = {}
        for record in fault_records:
            if record.fault_date:
                month_key = record.fault_date.strftime('%Y-%m')
                monthly_data[month_key] = monthly_data.get(month_key, 0) + 1
        
        # 排序并取最近12个月
        sorted_months = sorted(monthly_data.keys())[-12:]
        months = [month.split('-')[1] + '月' for month in sorted_months]
        counts = [monthly_data[month] for month in sorted_months]
        
        bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
        bar.add_xaxis(months)
        bar.add_yaxis("故障数量", counts, color="#3b82f6")
        bar.set_global_opts(
            title_opts=opts.TitleOpts(title="故障趋势分析", pos_left="center"),
            xaxis_opts=opts.AxisOpts(name="月份"),
            yaxis_opts=opts.AxisOpts(name="故障数量"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            legend_opts=opts.LegendOpts(pos_left="left", orient="vertical")
        )
        return bar.render_embed()
    except Exception:
        return "<div style='text-align: center; padding: 40px; color: #666;'>图表生成失败</div>"

def generate_fault_type_pie_chart(fault_records):
    """生成故障类型分布饼图"""
    try:
        if not fault_records:
            return "<div style='text-align: center; padding: 40px; color: #666;'>暂无数据</div>"
        
        # 统计故障类型
        type_counts = {}
        for record in fault_records:
            fault_type = record.province_fault_type or '未分类'
            type_counts[fault_type] = type_counts.get(fault_type, 0) + 1
        
        data = _aggregate_pie_data(type_counts, top_n=10)
        
        pie = Pie(init_opts=opts.InitOpts(width="100%", height="700px"))
        pie.add("故障类型", data, radius=["30%", "75%"], center=["50%", "40%"])
        pie.set_global_opts(
            title_opts=opts.TitleOpts(title="故障类型分布", pos_left="center"),
            legend_opts=opts.LegendOpts(pos_left="center", pos_top="90%", orient="horizontal")
        )
        pie.set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        return pie.render_embed()
    except Exception:
        return "<div style='text-align: center; padding: 40px; color: #666;'>图表生成失败</div>"

def generate_cause_category_pie_chart(fault_records):
    """生成原因分类分布饼图"""
    try:
        if not fault_records:
            return "<div style='text-align: center; padding: 40px; color: #666;'>暂无数据</div>"
        
        # 统计原因分类
        cause_counts = {}
        for record in fault_records:
            cause = record.cause_category or '未分类'
            cause_counts[cause] = cause_counts.get(cause, 0) + 1
        
        data = _aggregate_pie_data(cause_counts, top_n=10)
        
        pie = Pie(init_opts=opts.InitOpts(width="100%", height="700px"))
        pie.add("原因分类", data, radius=["30%", "75%"], center=["50%", "40%"])
        pie.set_global_opts(
            title_opts=opts.TitleOpts(title="原因分类分布", pos_left="center"),
            legend_opts=opts.LegendOpts(pos_left="center", pos_top="90%", orient="horizontal")
        )
        pie.set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        return pie.render_embed()
    except Exception:
        return "<div style='text-align: center; padding: 40px; color: #666;'>图表生成失败</div>"

def generate_duration_analysis_chart(fault_records):
    """生成故障处理时长分析图表"""
    try:
        if not fault_records:
            return "<div style='text-align: center; padding: 40px; color: #666;'>暂无数据</div>"
        
        # 按时长区间分组
        duration_ranges = {
            '0-2小时': 0,
            '2-8小时': 0,
            '8-24小时': 0,
            '24小时以上': 0,
            '未知': 0
        }
        
        for record in fault_records:
            duration = record.fault_duration_hours
            if duration is None:
                duration_ranges['未知'] += 1
            elif duration <= 2:
                duration_ranges['0-2小时'] += 1
            elif duration <= 8:
                duration_ranges['2-8小时'] += 1
            elif duration <= 24:
                duration_ranges['8-24小时'] += 1
            else:
                duration_ranges['24小时以上'] += 1
        
        categories = list(duration_ranges.keys())
        values = list(duration_ranges.values())
        
        bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
        bar.add_xaxis(categories)
        bar.add_yaxis("故障数量", values, color="#ff9800")
        bar.set_global_opts(
            title_opts=opts.TitleOpts(title="故障处理时长分布", pos_left="center"),
            xaxis_opts=opts.AxisOpts(name="处理时长"),
            yaxis_opts=opts.AxisOpts(name="故障数量"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            legend_opts=opts.LegendOpts(pos_left="left", orient="vertical")
        )
        return bar.render_embed()
    except Exception:
        return "<div style='text-align: center; padding: 40px; color: #666;'>图表生成失败</div>"

def generate_monthly_trend_chart(fault_records):
    """生成月度趋势小图表"""
    try:
        if not fault_records:
            return None
        
        # 按月统计
        monthly_data = {}
        for record in fault_records:
            if record.fault_date:
                month_key = record.fault_date.strftime('%m月')
                monthly_data[month_key] = monthly_data.get(month_key, 0) + 1
        
        if not monthly_data:
            return None
        
        months = sorted(monthly_data.keys())
        counts = [monthly_data[month] for month in months]
        
        line = Line(init_opts=opts.InitOpts(width="100%", height="200px"))
        line.add_xaxis(months)
        line.add_yaxis("故障数量", counts, is_smooth=True, symbol_size=6)
        line.set_global_opts(
            title_opts=opts.TitleOpts(title="月度趋势", title_textstyle_opts=opts.TextStyleOpts(font_size=14)),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=10)),
            yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(font_size=10)),
            tooltip_opts=opts.TooltipOpts(trigger="axis")
        )
        return line.render_embed()
    except Exception:
        return None

def calculate_avg_duration(fault_records):
    """计算平均处理时长"""
    try:
        durations = [r.fault_duration_hours for r in fault_records if r.fault_duration_hours is not None]
        if not durations:
            return "0"
        return f"{sum(durations) / len(durations):.1f}"
    except Exception:
        return "0"

def calculate_proactive_rate(fault_records):
    """计算主动发现率"""
    try:
        if not fault_records:
            return "0"
        
        proactive_count = sum(1 for r in fault_records 
                            if r.is_proactive_discovery and r.is_proactive_discovery.strip().lower() in ['是', 'yes', 'true', '1'])
        return f"{proactive_count * 100 / len(fault_records):.1f}"
    except Exception:
        return "0"

def calculate_complaint_count(fault_records):
    """计算有投诉故障数"""
    try:
        return sum(1 for r in fault_records 
                  if r.complaint_situation and r.complaint_situation.strip())
    except Exception:
        return 0

def calculate_notification_level_stats(fault_records):
    """计算通报级别统计"""
    try:
        level_counts = {}
        colors = {
            '一级': '#f44336',
            '二级': '#ff9800', 
            '三级': '#2196f3',
            '四级': '#4caf50'
        }
        
        for record in fault_records:
            level = record.notification_level or '未分类'
            level_counts[level] = level_counts.get(level, 0) + 1
        
        stats = []
        for level, count in level_counts.items():
            color = colors.get(level, '#9e9e9e')
            stats.append((level, count, color))
        
        return sorted(stats, key=lambda x: x[1], reverse=True)
    except Exception:
        return []

def generate_ai_analysis(fault_records):
    """生成AI分析报告"""
    try:
        if not fault_records:
            return "暂无数据进行分析。"
        
        total_count = len(fault_records)
        
        # 分析故障类型分布
        type_analysis = analyze_fault_types(fault_records)
        
        # 分析处理时长
        duration_analysis = analyze_durations(fault_records)
        
        # 分析主动发现情况
        proactive_analysis = analyze_proactive_discovery(fault_records)
        
        # 分析投诉情况
        complaint_analysis = analyze_complaints(fault_records)
        
        analysis_text = f"""📊 故障指标智能分析报告

📈 数据概览：
• 分析时间范围内共有 {total_count} 条故障记录

{type_analysis}

{duration_analysis}

{proactive_analysis}

{complaint_analysis}

💡 改进建议：
• 加强主动监控，提高故障发现率
• 优化处理流程，缩短处理时间
• 完善预防措施，减少高级别故障
• 加强用户沟通，降低投诉率"""
        
        return analysis_text
    except Exception as e:
        return f"分析过程中出现错误：{str(e)}"

def analyze_fault_types(fault_records):
    """分析故障类型"""
    type_counts = {}
    for record in fault_records:
        fault_type = record.province_fault_type or '未分类'
        type_counts[fault_type] = type_counts.get(fault_type, 0) + 1
    
    top_type = max(type_counts.items(), key=lambda x: x[1]) if type_counts else ('未知', 0)
    
    return f"""🔍 故障类型分析：
• 最常见故障类型：{top_type[0]} ({top_type[1]} 次)
• 故障类型种类：{len(type_counts)} 种"""

def analyze_durations(fault_records):
    """分析处理时长"""
    durations = [r.fault_duration_hours for r in fault_records if r.fault_duration_hours is not None]
    
    if not durations:
        return "🕰️ 处理时长分析：数据不足"
    
    avg_duration = sum(durations) / len(durations)
    max_duration = max(durations)
    long_duration_count = sum(1 for d in durations if d > 24)
    
    return f"""🕰️ 处理时长分析：
• 平均处理时长：{avg_duration:.1f} 小时
• 最长处理时间：{max_duration:.1f} 小时
• 超长处理故障（>24h）：{long_duration_count} 次"""

def analyze_proactive_discovery(fault_records):
    """分析主动发现情况"""
    proactive_count = sum(1 for r in fault_records 
                        if r.is_proactive_discovery and r.is_proactive_discovery.strip().lower() in ['是', 'yes', 'true', '1'])
    total_count = len(fault_records)
    proactive_rate = (proactive_count * 100 / total_count) if total_count > 0 else 0
    
    return f"""🔍 主动发现分析：
• 主动发现故障：{proactive_count} 次
• 主动发现率：{proactive_rate:.1f}%
• 被动发现故障：{total_count - proactive_count} 次"""

def analyze_complaints(fault_records):
    """分析投诉情况"""
    complaint_count = sum(1 for r in fault_records 
                         if r.complaint_situation and r.complaint_situation.strip())
    total_count = len(fault_records)
    complaint_rate = (complaint_count * 100 / total_count) if total_count > 0 else 0
    
    return f"""📢 投诉情况分析：
• 有投诉故障：{complaint_count} 次
• 投诉率：{complaint_rate:.1f}%
• 无投诉故障：{total_count - complaint_count} 次"""
