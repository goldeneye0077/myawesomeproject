#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障数据导入脚本
用于将故障记录Excel文件导入到数据库中
"""

import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, FaultRecord
import os

class FaultDataImporter:
    """故障数据导入器"""
    
    def __init__(self, db_path="db/data.db"):
        """初始化数据库连接"""
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def parse_datetime(self, date_str):
        """解析日期时间字符串"""
        if pd.isna(date_str) or date_str == '':
            return None
        
        try:
            # 尝试不同的日期格式
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
    
    def import_from_excel(self, excel_path="data/故障记录.xlsx"):
        """从Excel文件导入故障数据"""
        try:
            # 读取Excel文件
            df = pd.read_excel(excel_path)
            print(f"读取到 {len(df)} 条故障记录")
            
            # 清空现有数据
            self.session.query(FaultRecord).delete()
            
            # 逐行导入数据
            imported_count = 0
            for index, row in df.iterrows():
                try:
                    # 获取列名列表以便调试
                    columns = df.columns.tolist()
                    
                    fault_record = FaultRecord(
                        sequence_no=int(row['序号']) if pd.notna(row['序号']) else None,
                        fault_date=self.parse_datetime(row['日期']),
                        fault_name=str(row['故障名称']) if pd.notna(row['故障名称']) else None,
                        province_cause_analysis=str(row[columns[3]]) if pd.notna(row[columns[3]]) else None,  # 省-故障原因分析
                        province_cause_category=str(row['省-原因分类']) if pd.notna(row['省-原因分类']) else None,
                        province_fault_type=str(row['省-故障类型']) if pd.notna(row['省-故障类型']) else None,
                        notification_level=str(row['通报级别']) if pd.notna(row['通报级别']) else None,
                        cause_category=str(row['原因分类']) if pd.notna(row['原因分类']) else None,
                        fault_duration_hours=float(row['故障处理时长（小时）']) if pd.notna(row['故障处理时长（小时）']) else None,
                        complaint_situation=str(row['投诉情况']) if pd.notna(row['投诉情况']) else None,
                        start_time=self.parse_datetime(row['发生时间']),
                        end_time=self.parse_datetime(row['结束时间']),
                        fault_cause=str(row['故障原因']) if pd.notna(row['故障原因']) else None,
                        fault_handling=str(row['故障处理']) if pd.notna(row['故障处理']) else None,
                        is_proactive_discovery=str(row['是否主动发现']) if pd.notna(row['是否主动发现']) else None,
                        remarks=str(row['备注']) if pd.notna(row['备注']) else None
                    )
                    
                    self.session.add(fault_record)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"导入第 {index + 1} 行数据时出错: {e}")
                    continue
            
            # 提交事务
            self.session.commit()
            print(f"成功导入 {imported_count} 条故障记录")
            
        except Exception as e:
            print(f"导入数据时发生错误: {e}")
            self.session.rollback()
            raise
    
    def get_fault_statistics(self):
        """获取故障统计信息"""
        try:
            total_count = self.session.query(FaultRecord).count()
            
            # 按原因分类统计
            cause_stats = self.session.query(
                FaultRecord.cause_category,
                self.session.query(FaultRecord).filter(
                    FaultRecord.cause_category == FaultRecord.cause_category
                ).count().label('count')
            ).group_by(FaultRecord.cause_category).all()
            
            # 按故障类型统计
            type_stats = self.session.query(
                FaultRecord.province_fault_type,
                self.session.query(FaultRecord).filter(
                    FaultRecord.province_fault_type == FaultRecord.province_fault_type
                ).count().label('count')
            ).group_by(FaultRecord.province_fault_type).all()
            
            print(f"\n=== 故障数据统计 ===")
            print(f"总记录数: {total_count}")
            print(f"\n按原因分类统计:")
            for cause, count in cause_stats:
                if cause:
                    print(f"  {cause}: {count}")
            
            print(f"\n按故障类型统计:")
            for fault_type, count in type_stats:
                if fault_type:
                    print(f"  {fault_type}: {count}")
                    
        except Exception as e:
            print(f"获取统计信息时发生错误: {e}")
    
    def close(self):
        """关闭数据库连接"""
        self.session.close()

def main():
    """主函数"""
    print("开始导入故障数据...")
    
    # 检查Excel文件是否存在
    excel_path = "data/故障记录.xlsx"
    if not os.path.exists(excel_path):
        print(f"错误: 找不到文件 {excel_path}")
        return
    
    # 创建导入器并导入数据
    importer = FaultDataImporter()
    
    try:
        # 导入数据
        importer.import_from_excel(excel_path)
        
        # 显示统计信息
        importer.get_fault_statistics()
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
    finally:
        importer.close()
    
    print("数据导入完成!")

if __name__ == "__main__":
    main()
