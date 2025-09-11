# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个企业级指标管理与分析系统，主要用于监控、分析和管理各类运营指标。系统采用现代化的FastAPI架构，提供丰富的数据可视化和智能分析功能。

## 开发环境设置

### 环境要求
- Python 3.9+
- SQLite 3.35+
- Node.js (用于前端资源管理)

### 快速启动
```bash
# 1. 激活虚拟环境
cd aiwlsj1
.\venv\Scripts\activate  # Windows
# source venv1/bin/activate  # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python -m alembic upgrade head

# 4. 启动开发服务器
python main.py
# 或者
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 访问地址
- 主应用: http://127.0.0.1:8000
- API文档: http://127.0.0.1:8000/docs
- ReDoc文档: http://127.0.0.1:8000/redoc

## 常用开发命令

### 数据库管理
```bash
# 创建新的数据库迁移
alembic revision --autogenerate -m "describe your changes"

# 执行数据库迁移
alembic upgrade head

# 回滚数据库迁移
alembic downgrade -1

# 查看数据库状态
python check_db.py
```

### 数据导入导出
```bash
# 导入示例数据
python import_all_data.py

# 导入PUE数据
python insert_pue_data.py

# 导入故障数据
python fault_data_import.py

# 检查数据完整性
python check_tables.py
```

### 测试相关
```bash
# 运行故障分析测试
python test_fault_route.py

# 测试图表生成
python test_chart_generation.py

# 数据验证脚本
python check_fault_indexes.py
python check_pue_data.py
```

## 项目架构

### 核心模块结构
```
aiwlsj1/
├── db/                 # 数据库相关
│   ├── models.py       # SQLAlchemy数据模型
│   └── session.py      # 数据库会话管理
├── templates/          # Jinja2模板文件
├── static/             # 静态资源
│   ├── css/           # 样式文件
│   ├── js/            # JavaScript文件
│   └── images/        # 图片资源
├── alembic/           # 数据库迁移脚本
├── main.py            # 应用入口
├── config.py          # 配置管理
└── requirements.txt   # 依赖列表
```

### 业务模块
- **bi.py / bi_api.py**: 商业智能大屏模块
- **pue.py**: PUE指标分析模块
- **fault_analysis_fastapi.py**: 故障分析模块
- **huijugugan.py**: 汇聚骨干网络指标模块
- **bi_data_manage.py**: 指标数据管理模块

### 数据模型架构
- **基础指标模型**: Zbk (指标库)
- **PUE相关**: PUEData, PUEComment, PUEDrillDownData
- **故障相关**: FaultRecord
- **汇聚网络**: Huijugugan
- **大屏展示**: CenterTopTop, LeftTop, RightTop, Bottom等

## 开发规范

### API路由规范
- 使用FastAPI的APIRouter进行模块化路由管理
- 统一使用异步函数 (async/await)
- API路径命名采用REST风格
- 数据接口统一返回JSON格式

### 数据库操作规范
```python
# 标准数据库查询模式
async def get_data_example(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model).where(Model.field == value))
    return result.scalars().all()
```

### 模板渲染规范
```python
# 使用common.py中的模板环境
from common import bi_templates_env
return bi_templates_env.TemplateResponse(
    "template_name.html",
    {"request": request, "data": data}
)
```

### 图表生成规范
- 使用pyecharts进行服务端图表生成
- 图表配置统一管理，支持主题切换
- 交互式图表集成JavaScript事件处理

## 新指标开发流程

### 1. 数据模型创建
```python
# 在 db/models.py 中添加新模型
class NewIndicator(Base):
    __tablename__ = "new_indicator"
    id = Column(Integer, primary_key=True)
    # ... 其他字段
```

### 2. 数据库迁移
```bash
alembic revision --autogenerate -m "add new indicator model"
alembic upgrade head
```

### 3. API路由开发
```python
# 创建新的路由文件 new_indicator.py
router = APIRouter(prefix="/new_indicator", tags=["新指标"])

@router.get("/data")
async def get_new_indicator_data(db: AsyncSession = Depends(get_db)):
    # 实现数据查询逻辑
    pass
```

### 4. 前端模板创建
```html
<!-- 在 templates/ 目录下创建相应模板 -->
<!-- 使用统一的CSS样式和JavaScript库 -->
```

### 5. 主应用注册
```python
# 在 main.py 中注册新路由
from new_indicator import router as new_indicator_router
app.include_router(new_indicator_router)
```

## 数据可视化指南

### 图表类型选择
- **趋势分析**: 线图、面积图
- **分布对比**: 柱状图、饼图
- **多维分析**: 散点图、热力图
- **钻取分析**: 支持点击事件的交互式图表

### 常用图表配置
```python
# pyecharts基础配置
chart = (
    Line()
    .add_xaxis(x_data)
    .add_yaxis("系列名", y_data)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="图表标题"),
        toolbox_opts=opts.ToolboxOpts(is_show=True),
        datazoom_opts=opts.DataZoomOpts(is_show=True)
    )
)
```

### 颜色主题
- 支持多套颜色主题: modern_theme, color_harmony
- 图表颜色与页面样式保持一致
- 支持暗黑/明亮主题切换

## 安全注意事项

### API安全
- 所有外部API调用需要进行错误处理
- 敏感信息不得硬编码在代码中
- 使用环境变量管理配置信息

### 数据安全
- SQL查询使用参数化查询防止注入
- 文件上传需要格式和大小限制
- 用户输入数据需要验证和清理

## 性能优化

### 数据库优化
- 适当使用数据库索引
- 大数据量查询使用分页
- 考虑使用数据库连接池

### 前端优化
- 静态资源使用CDN加速
- 图表数据按需加载
- 实现数据缓存机制

## 故障排查

### 常见问题
1. **数据库连接错误**: 检查SQLite文件权限和路径
2. **模板加载失败**: 确认templates目录和文件存在
3. **静态文件404**: 检查static目录挂载配置
4. **API调用失败**: 查看uvicorn日志定位具体错误

### 日志查看
```bash
# 启动时开启详细日志
uvicorn main:app --reload --log-level debug
```

### 数据库检查
```bash
# 使用提供的检查脚本
python check_db.py
python check_tables.py
```

## 扩展开发

### 添加新的数据源
1. 在models.py中定义数据模型
2. 创建对应的API路由
3. 实现数据导入导出功能
4. 添加数据可视化页面

### 集成外部API
- 统一使用异步HTTP客户端
- 实现重试和错误处理机制
- 考虑API调用频率限制

### 国际化支持
- 准备多语言模板结构
- 使用Flask-Babel进行文本国际化
- 数据格式的本地化处理

此文档将持续更新，反映项目的最新开发状态和最佳实践。