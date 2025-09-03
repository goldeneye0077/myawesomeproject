#!/usr/bin/env python3
"""测试故障数据路由"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, distinct
from db.session import AsyncSessionLocal
from db.models import FaultRecord

async def test_fault_data():
    """测试故障数据查询"""
    async with AsyncSessionLocal() as db:
        try:
            # 测试获取筛选选项
            result = await db.execute(select(distinct(FaultRecord.province_fault_type)).where(
                FaultRecord.province_fault_type.isnot(None),
                FaultRecord.province_fault_type != ''
            ))
            all_fault_types = [item[0] for item in result.all()]
            print(f"故障类型数量: {len(all_fault_types)}")
            print(f"故障类型: {all_fault_types[:5]}")  # 显示前5个
            
            # 测试获取总数
            count_query = select(func.count()).select_from(FaultRecord)
            result = await db.execute(count_query)
            total = result.scalar()
            print(f"故障记录总数: {total}")
            
            # 测试分页查询
            paged_query = select(FaultRecord).order_by(FaultRecord.created_at.desc()).limit(5)
            result = await db.execute(paged_query)
            fault_data_list = result.scalars().all()
            print(f"查询到的记录数: {len(fault_data_list)}")
            
            if fault_data_list:
                first_record = fault_data_list[0]
                print(f"第一条记录: {first_record.fault_name}")
                
            print("✅ 数据库查询测试成功!")
            
        except Exception as e:
            print(f"❌ 数据库查询测试失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fault_data())
