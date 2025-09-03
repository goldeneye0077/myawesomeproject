#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入所有故障数据
"""

import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, FaultRecord

def parse_datetime(date_str):
    """解析日期时间字符串"""
    if pd.isna(date_str) or date_str == '':
        return None
    
    try:
        if isinstance(date_str, str):
            # 处理常见的日期格式
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', 
                       '%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        elif isinstance(date_str, datetime):
            return date_str
        else:
            # pandas Timestamp
            return date_str.to_pydatetime() if hasattr(date_str, 'to_pydatetime') else date_str
    except Exception as e:
        print(f"日期解析错误: {date_str}, 错误: {e}")
        return None

def main():
    # 读取Excel文件
    df = pd.read_excel('data/故障记录.xlsx')
    print(f"读取到 {len(df)} 条故障记录")
    
    # 创建数据库连接
    engine = create_engine('sqlite:///db/data.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 清空现有数据
        session.query(FaultRecord).delete()
        session.commit()
        
        # 导入所有数据
        imported_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                fault_record = FaultRecord(
                    sequence_no=int(row['序号']) if pd.notna(row['序号']) else None,
                    fault_date=parse_datetime(row['日期']),
                    fault_name=str(row['故障名称']) if pd.notna(row['故障名称']) else None,
                    province_cause_analysis=str(row[' 省-故障原因析']) if pd.notna(row[' 省-故障原因析']) else None,
                    province_cause_category=str(row['省-原因分类']) if pd.notna(row['省-原因分类']) else None,
                    province_fault_type=str(row['省-故障类型']) if pd.notna(row['省-故障类型']) else None,
                    notification_level=str(row['通报级别']) if pd.notna(row['通报级别']) else None,
                    cause_category=str(row['原因分类']) if pd.notna(row['原因分类']) else None,
                    fault_duration_hours=float(row['故障处理时长（小时）']) if pd.notna(row['故障处理时长（小时）']) else None,
                    complaint_situation=str(row['投诉情况']) if pd.notna(row['投诉情况']) else None,
                    start_time=parse_datetime(row['发生时间']),
                    end_time=parse_datetime(row['结束时间']),
                    fault_cause=str(row['故障原因']) if pd.notna(row['故障原因']) else None,
                    fault_handling=str(row['故障处理']) if pd.notna(row['故障处理']) else None,
                    is_proactive_discovery=str(row['是否主动发现']) if pd.notna(row['是否主动发现']) else None,
                    remarks=str(row['备注']) if pd.notna(row['备注']) else None
                )
                
                session.add(fault_record)
                imported_count += 1
                
                if imported_count % 50 == 0:
                    print(f"已导入 {imported_count} 条记录...")
                
            except Exception as e:
                error_count += 1
                print(f"导入第 {index + 1} 行数据时出错: {e}")
                continue
        
        # 提交事务
        session.commit()
        print(f"\n导入完成!")
        print(f"成功导入: {imported_count} 条记录")
        print(f"错误记录: {error_count} 条")
        
        # 验证数据
        total_count = session.query(FaultRecord).count()
        print(f"数据库中总记录数: {total_count}")
        
        # 统计信息
        cause_stats = session.query(FaultRecord.cause_category, 
                                   session.query(FaultRecord).filter(
                                       FaultRecord.cause_category == FaultRecord.cause_category
                                   ).count().label('count')).group_by(FaultRecord.cause_category).all()
        
        print(f"\n按原因分类统计:")
        for cause, count in cause_stats[:10]:  # 显示前10个
            if cause:
                print(f"  {cause}: {count}")
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
