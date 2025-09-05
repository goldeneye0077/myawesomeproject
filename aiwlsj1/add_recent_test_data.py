#!/usr/bin/env python3
"""
为指标管理功能添加最近的测试数据
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import FaultRecord
from datetime import datetime, timedelta
import random

async def add_recent_test_data():
    """添加最近的测试故障数据"""
    
    # 创建数据库连接
    DATABASE_URL = "sqlite+aiosqlite:///db.sqlite3"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as db:
        print("正在添加最近30天的测试数据...")
        
        # 生成最近30天的测试数据
        test_data = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # 故障类型和级别选项
        fault_types = ['网络故障', '设备故障', '系统故障', '应用故障', '电力故障']
        notification_levels = ['一般通报', 'C级', 'B级', 'A级', '重大']
        cause_categories = ['硬件故障', '软件故障', '网络问题', '人为操作', '环境因素']
        discovery_types = ['是', '否']
        
        # 生成15-25条最近的故障记录
        num_records = random.randint(15, 25)
        
        for i in range(num_records):
            # 随机生成故障日期（最近30天内）
            days_ago = random.randint(0, 30)
            fault_date = end_date - timedelta(days=days_ago)
            
            # 随机故障持续时间（0.5-12小时）
            duration = round(random.uniform(0.5, 12.0), 2)
            
            # 创建故障记录
            fault_record = FaultRecord(
                sequence_no=1000 + i,
                fault_date=fault_date,
                fault_name=f'测试故障_{fault_date.strftime("%m%d")}_{i+1:02d}',
                province_cause_analysis=f'故障原因分析：{random.choice(cause_categories)}导致的{random.choice(fault_types)}',
                province_cause_category=random.choice(cause_categories),
                province_fault_type=random.choice(fault_types),
                notification_level=random.choice(notification_levels),
                cause_category=random.choice(cause_categories),
                fault_duration_hours=duration,
                complaint_situation='无' if random.random() > 0.3 else '有用户投诉',
                start_time=fault_date - timedelta(hours=duration),
                end_time=fault_date,
                fault_cause=f'{random.choice(fault_types)}导致服务中断',
                fault_handling=f'通过{random.choice(["重启服务", "更换设备", "修复配置", "清理缓存"])}解决',
                is_proactive_discovery=random.choice(discovery_types),
                remarks=f'测试数据 - {fault_date.strftime("%Y-%m-%d")}'
            )
            
            test_data.append(fault_record)
        
        # 批量添加到数据库
        db.add_all(test_data)
        await db.commit()
        
        print(f"成功添加了 {len(test_data)} 条最近30天的测试数据")
        
        # 显示添加的数据统计
        print("\n添加的数据统计:")
        print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        # 统计各级别故障数量
        level_counts = {}
        for record in test_data:
            level = record.notification_level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print("故障级别分布:")
        for level, count in level_counts.items():
            print(f"  {level}: {count}次")
        
        # 统计主动发现率
        proactive_count = sum(1 for r in test_data if r.is_proactive_discovery == '是')
        proactive_rate = (proactive_count / len(test_data) * 100)
        print(f"\n主动发现率: {proactive_rate:.1f}% ({proactive_count}/{len(test_data)})")
        
        # 统计平均处理时长
        avg_duration = sum(r.fault_duration_hours for r in test_data) / len(test_data)
        print(f"平均处理时长: {avg_duration:.2f}小时")
    
    await engine.dispose()
    print("\n✅ 测试数据添加完成！现在可以在指标管理页面查看最近30天的数据了。")

if __name__ == "__main__":
    asyncio.run(add_recent_test_data())