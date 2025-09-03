#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试数据导入脚本
"""

import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, FaultRecord

def main():
    # 读取Excel文件
    df = pd.read_excel('data/故障记录.xlsx')
    print(f"读取到 {len(df)} 条故障记录")
    print("列名:", df.columns.tolist())
    print("\n前3行数据:")
    print(df.head(3))
    
    # 创建数据库连接
    engine = create_engine('sqlite:///db/data.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 清空现有数据
        session.query(FaultRecord).delete()
        session.commit()
        
        # 导入前5条数据进行测试
        imported_count = 0
        for index, row in df.head(5).iterrows():
            try:
                print(f"\n处理第 {index + 1} 行数据:")
                print(f"序号: {row['序号']}")
                print(f"故障名称: {row['故障名称']}")
                
                fault_record = FaultRecord(
                    sequence_no=int(row['序号']) if pd.notna(row['序号']) else None,
                    fault_name=str(row['故障名称']) if pd.notna(row['故障名称']) else None,
                    fault_date=pd.to_datetime(row['日期']) if pd.notna(row['日期']) else None,
                    cause_category=str(row['原因分类']) if pd.notna(row['原因分类']) else None,
                    province_fault_type=str(row['省-故障类型']) if pd.notna(row['省-故障类型']) else None,
                    notification_level=str(row['通报级别']) if pd.notna(row['通报级别']) else None,
                    fault_duration_hours=float(row['故障处理时长（小时）']) if pd.notna(row['故障处理时长（小时）']) else None,
                    is_proactive_discovery=str(row['是否主动发现']) if pd.notna(row['是否主动发现']) else None
                )
                
                session.add(fault_record)
                imported_count += 1
                print(f"成功添加第 {imported_count} 条记录")
                
            except Exception as e:
                print(f"导入第 {index + 1} 行数据时出错: {e}")
                continue
        
        # 提交事务
        session.commit()
        print(f"\n成功导入 {imported_count} 条故障记录")
        
        # 验证数据
        total_count = session.query(FaultRecord).count()
        print(f"数据库中总记录数: {total_count}")
        
        if total_count > 0:
            sample = session.query(FaultRecord).first()
            print(f"示例记录: {sample.fault_name}")
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
