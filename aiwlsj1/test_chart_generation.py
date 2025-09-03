#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyecharts.charts import Bar
from pyecharts import options as opts

def test_simple_chart():
    # 创建简单的测试图表
    bar = (
        Bar(init_opts=opts.InitOpts(width="800px", height="400px"))
        .add_xaxis(["1月", "2月", "3月", "4月", "5月", "6月"])
        .add_yaxis("2024年", [1.2, 1.3, 1.1, 1.4, 1.2, 1.3])
        .add_yaxis("2025年", [1.3, 1.2, 1.2, 1.3, 1.1, 1.2])
        .set_global_opts(
            title_opts=opts.TitleOpts(title="测试柱状图"),
            tooltip_opts=opts.TooltipOpts(trigger="axis")
        )
    )
    
    # 生成HTML
    chart_html = bar.render_embed()
    print("图表HTML长度:", len(chart_html))
    print("HTML前200字符:", chart_html[:200])
    
    # 保存到文件
    with open('test_chart.html', 'w', encoding='utf-8') as f:
        f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <title>测试图表</title>
</head>
<body>
    <h1>测试pyecharts图表生成</h1>
    {chart_html}
</body>
</html>
        """)
    
    print("测试图表已保存到 test_chart.html")

if __name__ == "__main__":
    test_simple_chart()
