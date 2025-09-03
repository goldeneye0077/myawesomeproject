#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入PUE下钻数据到数据库
"""
import pandas as pd
import sqlite3
from datetime import datetime
import sys
import os

def import_drill_down_data():
    """导入Excel数据到PUE下钻数据表"""
    try:
        # 读取Excel文件
        df = pd.read_excel('_深圳宝安区宝城.xlsx')
        
        # 删除空列
        df_clean = df.drop(columns=[col for col in df.columns if 'Unnamed' in str(col)])
        
        # 连接数据库
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # 创建表（如果不存在）
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS pue_drill_down_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT COMMENT '地点/机房',
            month TEXT COMMENT '月份',
            year TEXT COMMENT '年份',
            work_type TEXT COMMENT '作业形式',
            work_category TEXT COMMENT '作业分类',
            sequence_no INTEGER COMMENT '序号',
            work_object TEXT COMMENT '作业对象',
            check_item TEXT COMMENT '检查项',
            operation_method TEXT COMMENT '操作方法及建议值',
            benchmark_value TEXT COMMENT '标杆值',
            execution_standard TEXT COMMENT '执行标准',
            execution_status TEXT COMMENT '执行情况',
            detailed_situation TEXT COMMENT '详细情况',
            quantification_standard TEXT COMMENT '量化标准',
            last_month_standard TEXT COMMENT '上月量化标准',
            quantification_unit TEXT COMMENT '量化单位',
            executor TEXT COMMENT '执行人',
            created_at DATETIME,
            updated_at DATETIME
        )
        '''
        cursor.execute(create_table_sql)
        
        # 清空现有数据（可选）
        cursor.execute('DELETE FROM pue_drill_down_data WHERE location = ?', ('深圳宝安区宝城',))
        
        # 准备插入数据
        current_time = datetime.now().isoformat()
        
        # 插入数据
        for index, row in df_clean.iterrows():
            insert_sql = '''
            INSERT INTO pue_drill_down_data (
                location, month, year, work_type, work_category, sequence_no,
                work_object, check_item, operation_method, benchmark_value,
                execution_standard, execution_status, detailed_situation,
                quantification_standard, last_month_standard, quantification_unit,
                executor, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # 假设这是2025年1月的数据（可以根据实际情况调整）
            values = (
                '深圳宝安区宝城',  # location
                '1',  # month
                '2025',  # year
                str(row['作业形式']) if pd.notna(row['作业形式']) else '',
                str(row['作业分类']) if pd.notna(row['作业分类']) else '',
                int(row['序号']) if pd.notna(row['序号']) else 0,
                str(row['作业对象']) if pd.notna(row['作业对象']) else '',
                str(row['检查项']) if pd.notna(row['检查项']) else '',
                str(row['操作方法及建议值']) if pd.notna(row['操作方法及建议值']) else '',
                str(row['标杆值']) if pd.notna(row['标杆值']) else '',
                str(row['执行标准']) if pd.notna(row['执行标准']) else '',
                str(row['执行情况']) if pd.notna(row['执行情况']) else '',
                str(row['详细情况']) if pd.notna(row['详细情况']) else '',
                str(row['量化标准']) if pd.notna(row['量化标准']) else '',
                str(row['上月量化标准']) if pd.notna(row['上月量化标准']) else '',
                str(row['量化单位']) if pd.notna(row['量化单位']) else '',
                str(row['执行人']) if pd.notna(row['执行人']) else '',
                current_time,
                current_time
            )
            
            cursor.execute(insert_sql, values)
        
        # 提交事务
        conn.commit()
        
        # 查询插入结果
        cursor.execute('SELECT COUNT(*) FROM pue_drill_down_data WHERE location = ?', ('深圳宝安区宝城',))
        count = cursor.fetchone()[0]
        
        print(f"成功导入 {count} 条下钻数据到数据库")
        
        # 显示前3条数据
        cursor.execute('''
            SELECT work_type, work_category, work_object, check_item, executor 
            FROM pue_drill_down_data 
            WHERE location = ? 
            LIMIT 3
        ''', ('深圳宝安区宝城',))
        
        results = cursor.fetchall()
        print("\n前3条数据预览:")
        for i, row in enumerate(results, 1):
            print(f"{i}. 作业形式: {row[0]}, 作业分类: {row[1]}, 作业对象: {row[2]}")
            print(f"   检查项: {row[3][:50]}...")
            print(f"   执行人: {row[4]}")
            print()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"导入数据时出错: {e}")
        return False

if __name__ == "__main__":
    success = import_drill_down_data()
    if success:
        print("数据导入完成！")
    else:
        print("数据导入失败！")
        sys.exit(1)
