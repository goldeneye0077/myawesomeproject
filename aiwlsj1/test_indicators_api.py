#!/usr/bin/env python3
"""
测试指标管理API的响应
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import FaultRecord
from fault_analysis_fastapi import _calculate_fault_kpis, _analyze_indicators_trend, _identify_risk_indicators
from datetime import datetime, timedelta
from sqlalchemy.future import select

async def test_api_responses():
    """测试API响应和时间范围过滤"""
    
    # 创建数据库连接
    DATABASE_URL = "sqlite+aiosqlite:///db.sqlite3"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as db:
        print("测试指标管理API响应...")
        
        # 测试不同时间范围
        time_periods = ['last_7_days', 'last_30_days', 'last_90_days', 'all_data']
        
        for period in time_periods:
            print(f"\n测试时间范围: {period}")
            
            # 计算时间范围
            end_date = datetime.now()
            if period == 'last_7_days':
                start_date = end_date - timedelta(days=7)
            elif period == 'last_30_days':
                start_date = end_date - timedelta(days=30)
            elif period == 'last_90_days':
                start_date = end_date - timedelta(days=90)
            elif period == 'all_data':
                start_date = datetime(2020, 1, 1)
            else:
                start_date = end_date - timedelta(days=30)
            
            # 查询数据
            query = select(FaultRecord).where(
                FaultRecord.fault_date >= start_date,
                FaultRecord.fault_date <= end_date
            )
            result = await db.execute(query)
            fault_records = result.scalars().all()
            
            print(f"   数据量: {len(fault_records)}")
            print(f"   时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            
            if fault_records:
                # 测试KPI计算
                try:
                    kpis = await _calculate_fault_kpis(fault_records, start_date, end_date)
                    print(f"   KPI计算成功: {len(kpis)}个指标")
                    
                    # 显示关键指标
                    for kpi_name, kpi_data in kpis.items():
                        if kpi_name in ['fault_volume', 'high_severity_rate']:
                            print(f"      - {kpi_name}: {kpi_data['value']}{kpi_data['unit']} (状态: {kpi_data['status']})")
                            
                except Exception as e:
                    print(f"   KPI计算失败: {str(e)}")
                
                # 测试趋势分析
                try:
                    trends = await _analyze_indicators_trend(fault_records, start_date, end_date)
                    print(f"   趋势分析成功")
                    if 'fault_volume_trend' in trends:
                        print(f"      - 故障量趋势: {trends['fault_volume_trend']}")
                except Exception as e:
                    print(f"   趋势分析失败: {str(e)}")
                
                # 测试风险识别
                try:
                    risks = await _identify_risk_indicators(fault_records)
                    print(f"   风险识别成功")
                    print(f"      - 高风险指标: {len(risks.get('high_risk_indicators', []))}")
                    print(f"      - 预警指标: {len(risks.get('warning_indicators', []))}")
                except Exception as e:
                    print(f"   风险识别失败: {str(e)}")
                    
            else:
                print(f"   该时间范围内无数据")
        
        # 测试数据库整体状态
        print(f"\n数据库整体状态:")
        total_query = select(FaultRecord)
        total_result = await db.execute(total_query)
        total_records = total_result.scalars().all()
        print(f"   总记录数: {len(total_records)}")
        
        if total_records:
            dates = [r.fault_date for r in total_records if r.fault_date]
            if dates:
                print(f"   数据时间跨度: {min(dates)} 至 {max(dates)}")
                
                # 检查最近的数据
                recent_count = len([d for d in dates if d >= datetime.now() - timedelta(days=30)])
                print(f"   最近30天数据: {recent_count}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_api_responses())