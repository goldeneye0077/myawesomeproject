# 新指标开发模板使用指南

本目录包含了创建新指标模块的标准模板和指南，帮助您快速、规范地开发新的指标功能。

## 📁 目录结构

```
templates/indicators/
├── README.md                    # 本指南文件
├── new_indicator_template.py    # Python后端模块模板
├── html_templates/              # HTML模板文件
│   ├── indicator_index.html     # 指标列表页面模板
│   ├── add_indicator.html       # 添加指标表单模板
│   ├── edit_indicator.html      # 编辑指标表单模板
│   └── analyze_indicator.html   # 数据分析页面模板
└── database_model_template.py   # 数据模型模板
```

## 🚀 快速开始

### 第一步：复制模板文件

1. 复制 `new_indicator_template.py` 到项目根目录
2. 重命名为您的指标名称，例如 `network_performance.py`
3. 复制相关HTML模板到 `templates/` 目录

### 第二步：创建数据模型

在 `db/models.py` 中添加您的数据模型：

```python
class NetworkPerformance(Base):
    """网络性能指标模型"""
    __tablename__ = "network_performance"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String(255), comment="地点")
    bandwidth = Column(Float, comment="带宽利用率")
    latency = Column(Float, comment="延迟")
    packet_loss = Column(Float, comment="丢包率")
    availability = Column(Float, comment="可用性")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 第三步：生成数据库迁移

```bash
alembic revision --autogenerate -m "add network performance model"
alembic upgrade head
```

### 第四步：修改模板代码

1. 替换所有 `YourIndicator` 为您的实际指标名称
2. 替换 `YourModel` 为您的数据模型类名
3. 修改路由前缀和标签
4. 根据业务需求调整字段和逻辑

### 第五步：创建HTML模板

复制HTML模板文件并修改：

1. `your_indicator_index.html` - 指标列表页
2. `add_your_indicator.html` - 添加表单页
3. `edit_your_indicator.html` - 编辑表单页
4. `your_indicator_analyze.html` - 数据分析页

### 第六步：注册路由

在 `main.py` 中注册您的路由：

```python
from network_performance import router as network_performance_router
app.include_router(network_performance_router)
```

## 📋 开发规范

### 命名约定

- **模块文件名**: 使用下划线分隔的小写字母，如 `network_performance.py`
- **类名**: 使用驼峰命名法，如 `NetworkPerformance`
- **API路由**: 使用REST风格，如 `/api/network-performance/data`
- **数据库表名**: 使用下划线分隔的小写字母，如 `network_performance`

### 目录结构规范

```python
your_indicator_module.py
├── 导入部分
│   ├── FastAPI相关
│   ├── 数据库相关
│   ├── 工具模块
│   └── 配置模块
├── 路由器创建
├── Pydantic模型定义
├── 页面路由 (HTML响应)
├── API接口 (JSON响应)
│   ├── 基础CRUD操作
│   ├── 批量操作
│   ├── 统计查询
│   └── 图表数据
└── 辅助函数
```

### 错误处理规范

使用项目提供的统一异常处理：

```python
from utils.exceptions import DatabaseException, ValidationException
from utils.response import handle_success, handle_error

# 数据库操作异常
try:
    # 数据库操作
    pass
except Exception as e:
    logger.error(f"操作失败: {str(e)}", exc_info=True)
    raise DatabaseException("操作失败")

# 数据验证异常
if not data.is_valid():
    raise ValidationException("数据验证失败")
```

### 日志记录规范

```python
import logging
logger = logging.getLogger(__name__)

# 信息日志
logger.info("操作成功完成")

# 警告日志
logger.warning("数据存在异常")

# 错误日志
logger.error("操作失败", exc_info=True)
```

## 🎯 功能模块清单

### 必需功能

- [ ] 数据模型定义
- [ ] 基础CRUD操作 (创建、读取、更新、删除)
- [ ] 数据列表页面（支持分页、搜索、筛选）
- [ ] 添加/编辑表单页面
- [ ] 数据验证和错误处理
- [ ] 日志记录

### 可选功能

- [ ] 批量数据导入/导出
- [ ] 数据分析页面
- [ ] 图表可视化
- [ ] 统计信息
- [ ] 数据下钻功能
- [ ] 智能分析（集成AI）

## 📊 HTML模板规范

### 页面结构

所有页面都应该继承基础模板：

```html
{% extends "base.html" %}

{% block title %}您的指标名称{% endblock %}

{% block content %}
<!-- 页面内容 -->
{% endblock %}

{% block scripts %}
<!-- 页面特定的JavaScript -->
{% endblock %}
```

### CSS类名规范

使用Bootstrap和项目自定义样式：

```html
<!-- 表格容器 -->
<div class="table-responsive">

<!-- 按钮组 -->
<div class="btn-group" role="group">

<!-- 表单组 -->
<div class="form-group">

<!-- 卡片容器 -->
<div class="card">
```

### JavaScript规范

使用项目提供的公共函数：

```javascript
// AJAX请求
fetchData('/api/your-indicator/data')
    .then(data => {
        // 处理数据
    })
    .catch(error => {
        showAlert('error', '加载失败');
    });

// 表单提交
submitForm(formData, '/api/your-indicator/create')
    .then(result => {
        showAlert('success', '保存成功');
    });
```

## 🔧 测试指南

### 单元测试

为每个API端点创建测试：

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_indicator():
    response = client.post("/api/your-indicator/create", json={
        "name": "测试指标",
        "value": 85.5
    })
    assert response.status_code == 200
    assert response.json()["success"] == True
```

### 集成测试

测试完整的业务流程：

```python
def test_indicator_workflow():
    # 创建指标
    create_response = client.post("/api/your-indicator/create", json=test_data)
    indicator_id = create_response.json()["data"]["id"]
    
    # 查询指标
    get_response = client.get(f"/api/your-indicator/data")
    assert len(get_response.json()["data"]) > 0
    
    # 更新指标
    update_response = client.put(f"/api/your-indicator/update/{indicator_id}", json=update_data)
    assert update_response.json()["success"] == True
    
    # 删除指标
    delete_response = client.delete(f"/api/your-indicator/delete/{indicator_id}")
    assert delete_response.json()["success"] == True
```

## 🚀 部署清单

开发完成后，确保完成以下步骤：

- [ ] 代码审查和测试
- [ ] 文档更新（包括API文档）
- [ ] 数据库迁移脚本
- [ ] 配置文件更新
- [ ] 日志和监控配置
- [ ] 性能测试
- [ ] 安全检查

## 📝 示例项目

参考现有的指标模块：

- `pue.py` - PUE指标管理
- `fault_analysis_fastapi.py` - 故障分析
- `huijugugan.py` - 汇聚骨干指标

## 🆘 常见问题

### Q: 如何处理大量数据的导入？
A: 使用批量处理和事务管理，并提供进度反馈。

### Q: 如何实现实时数据更新？
A: 使用WebSocket或Server-Sent Events，结合前端定时刷新。

### Q: 如何优化查询性能？
A: 添加数据库索引，使用分页查询，实现查询缓存。

### Q: 如何集成第三方数据源？
A: 创建数据适配器，使用异步HTTP客户端，实现错误重试机制。

## 📞 技术支持

如有问题，请：

1. 查看项目文档和现有代码示例
2. 检查日志文件获取错误信息
3. 参考类似功能的实现方式
4. 联系项目维护者获取帮助

---

祝您开发愉快！🎉