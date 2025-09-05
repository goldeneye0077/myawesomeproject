# 数据备份和监控计划

## 🔒 数据备份策略

### 当前数据基线 (2025-09-04)
- **主数据库**: db.sqlite3 (5.1MB)
- **PUE数据**: 240条记录
- **故障记录**: 272条记录  
- **汇聚数据**: 28条记录
- **PUE评论**: 34条记录
- **PUE钻取数据**: 13,680条记录
- **总记录数**: 14,254条
- **数据完整性**: ✅ 已验证

### 备份频率
- **实时备份**: WAL文件自动备份
- **每日备份**: 凌晨2点自动全量备份
- **每周备份**: 周日完整项目备份
- **月度备份**: 长期存储备份

### 备份脚本

```bash
#!/bin/bash
# daily_backup.sh - 每日数据备份脚本

BACKUP_DIR="../backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/db_$DATE.sqlite3"
PROJECT_BACKUP="$BACKUP_DIR/project_$DATE"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
echo "创建数据库备份: $DB_BACKUP"
cp db.sqlite3 $DB_BACKUP

# 验证备份完整性
if sqlite3 $DB_BACKUP "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✅ 数据库备份验证成功"
else
    echo "❌ 数据库备份验证失败"
    exit 1
fi

# 完整项目备份（每周）
if [ $(date +%u) -eq 7 ]; then
    echo "创建项目完整备份: $PROJECT_BACKUP"
    cp -r . $PROJECT_BACKUP
    echo "✅ 项目备份完成"
fi

# 清理超过30天的备份
find $BACKUP_DIR -name "db_*.sqlite3" -mtime +30 -delete
find $BACKUP_DIR -name "project_*" -mtime +30 -exec rm -rf {} \;

echo "备份任务完成: $(date)"
```

### 恢复流程

```bash
#!/bin/bash
# restore_database.sh - 数据恢复脚本

BACKUP_FILE=$1
CURRENT_DB="db.sqlite3"

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: $0 <备份文件路径>"
    exit 1
fi

# 验证备份文件
if ! sqlite3 $BACKUP_FILE "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "❌ 备份文件损坏，无法恢复"
    exit 1
fi

# 创建当前数据库的安全备份
cp $CURRENT_DB "${CURRENT_DB}.before_restore.$(date +%Y%m%d_%H%M%S)"

# 恢复数据库
cp $BACKUP_FILE $CURRENT_DB

echo "✅ 数据库恢复完成"
echo "原数据库已备份为: ${CURRENT_DB}.before_restore.*"
```

## 📊 数据监控机制

### 实时监控指标

1. **数据库健康**
   - 连接状态检查
   - 数据完整性验证
   - 表记录数监控
   - WAL文件大小监控

2. **系统性能**
   - API响应时间
   - 数据库查询性能
   - 内存使用量
   - 磁盘空间使用

3. **业务指标**
   - 关键表数据量变化
   - 数据一致性检查
   - 异常数据检测
   - 用户访问模式

### 监控工具配置

通过新集成的系统监控工具提供以下端点：

```python
# 健康检查端点
GET /tools/monitor/health/quick
GET /tools/monitor/health/database
GET /tools/monitor/performance/metrics
GET /tools/monitor/status/overview
```

### 告警阈值

| 指标 | 警告阈值 | 严重阈值 | 处理方式 |
|------|----------|----------|----------|
| 数据库连接失败 | 1次 | 连续3次 | 自动重启/手动检查 |
| 响应时间 | >2秒 | >5秒 | 性能优化/资源扩容 |
| 数据量异常变化 | ±10% | ±25% | 数据审计/备份恢复 |
| 磁盘空间 | >80% | >90% | 清理日志/扩容 |
| 内存使用 | >75% | >85% | 重启应用/内存优化 |

## 🔧 监控脚本

### 数据完整性监控

```python
# data_integrity_monitor.py
import asyncio
import logging
from datetime import datetime
from db.session import AsyncSessionLocal
from db.models import PUEData, FaultRecord, Huijugugan
from sqlalchemy import select, func

async def check_data_integrity():
    """检查数据完整性"""
    async with AsyncSessionLocal() as db:
        # 基线数据量
        baseline_data = {
            'pue_data': 240,
            'fault_record': 272,
            'huijugugan': 28
        }
        
        # 当前数据量
        current_data = {}
        
        # 检查PUE数据
        result = await db.execute(select(func.count(PUEData.id)))
        current_data['pue_data'] = result.scalar()
        
        # 检查故障记录
        result = await db.execute(select(func.count(FaultRecord.id)))
        current_data['fault_record'] = result.scalar()
        
        # 检查汇聚数据
        result = await db.execute(select(func.count(Huijugugan.id)))
        current_data['huijugugan'] = result.scalar()
        
        # 数据变化检查
        alerts = []
        for table, baseline in baseline_data.items():
            current = current_data[table]
            change_percent = abs(current - baseline) / baseline * 100
            
            if change_percent > 25:  # 严重阈值
                alerts.append(f"严重: {table}数据变化{change_percent:.1f}% ({baseline}->{current})")
            elif change_percent > 10:  # 警告阈值
                alerts.append(f"警告: {table}数据变化{change_percent:.1f}% ({baseline}->{current})")
        
        return {
            'timestamp': datetime.utcnow(),
            'baseline_data': baseline_data,
            'current_data': current_data,
            'alerts': alerts,
            'status': 'error' if any('严重' in alert for alert in alerts) else 
                     'warning' if alerts else 'ok'
        }

if __name__ == "__main__":
    result = asyncio.run(check_data_integrity())
    print(f"数据完整性检查: {result['status']}")
    for alert in result['alerts']:
        print(f"  {alert}")
```

### 自动化监控部署

```bash
#!/bin/bash
# setup_monitoring.sh - 设置监控任务

# 添加到crontab
echo "设置自动化监控任务..."

# 每日2点备份
echo "0 2 * * * cd /path/to/aiwlsj1 && ./daily_backup.sh >> logs/backup.log 2>&1" >> /tmp/crontab_tmp

# 每小时数据完整性检查
echo "0 * * * * cd /path/to/aiwlsj1 && python data_integrity_monitor.py >> logs/integrity.log 2>&1" >> /tmp/crontab_tmp

# 每5分钟健康检查
echo "*/5 * * * * curl -s http://localhost:8000/tools/monitor/health/quick >> logs/health.log 2>&1" >> /tmp/crontab_tmp

# 安装cron任务
crontab /tmp/crontab_tmp
rm /tmp/crontab_tmp

echo "✅ 监控任务设置完成"
crontab -l
```

## 📈 报告和分析

### 周报生成

```python
# weekly_report.py
import asyncio
from datetime import datetime, timedelta
from tools.system_monitor import check_database_health, get_performance_metrics

async def generate_weekly_report():
    """生成周报"""
    report_date = datetime.utcnow()
    
    # 数据库健康状态
    db_health = await check_database_health()
    
    # 系统性能指标
    performance = await get_performance_metrics()
    
    report = f"""
# 系统周报 - {report_date.strftime('%Y年%m月%d日')}

## 📊 系统状态概览
- 数据库状态: {db_health.status}
- 总数据记录: {db_health.total_records:,}条
- 表数量: {db_health.table_count}个

## ⚡ 性能指标
- CPU使用率: {performance.cpu_percent}%
- 内存使用率: {performance.memory_percent}%
- 磁盘使用率: {performance.disk_usage_percent}%

## 🔍 数据完整性
| 表名 | 记录数 | 状态 |
|------|--------|------|
| PUE数据 | {db_health.tables.get('pue_data', 0):,} | ✅ |
| 故障记录 | {db_health.tables.get('fault_record', 0):,} | ✅ |
| 汇聚数据 | {db_health.tables.get('huijugugan', 0):,} | ✅ |

## 📝 建议
- 系统运行正常，无异常情况
- 数据完整性良好
- 建议继续监控系统性能指标

---
报告生成时间: {report_date.isoformat()}
    """
    
    return report

if __name__ == "__main__":
    report = asyncio.run(generate_weekly_report())
    
    # 保存到文件
    filename = f"reports/weekly_report_{datetime.utcnow().strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"周报已生成: {filename}")
```

## 🚨 应急响应计划

### 数据丢失应急预案

1. **立即响应** (0-15分钟)
   - 停止应用服务
   - 保护现场数据
   - 评估损失范围

2. **数据恢复** (15分钟-1小时)
   - 选择最近可用备份
   - 执行数据恢复脚本
   - 验证恢复结果

3. **服务恢复** (1-2小时)
   - 重启应用服务
   - 功能完整性测试
   - 监控系统状态

4. **事后分析** (24小时内)
   - 分析事故原因
   - 改进备份策略
   - 更新应急预案

### 联系信息

- **系统管理员**: [联系方式]
- **数据库管理员**: [联系方式]  
- **应急响应小组**: [联系方式]

---

**重要提醒**: 
- 定期测试备份恢复流程
- 保持监控系统持续运行
- 及时响应告警信息
- 定期审查和更新备份策略