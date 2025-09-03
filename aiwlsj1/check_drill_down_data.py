#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

def check_drill_down_data():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # 检查下钻数据中的地点
        cursor.execute('SELECT DISTINCT location FROM pue_drill_down_data')
        locations = cursor.fetchall()
        print("下钻数据中的地点:")
        for location in locations:
            print(f"  - {location[0]}")
        
        # 检查1月份的数据
        cursor.execute('SELECT COUNT(*) FROM pue_drill_down_data WHERE month = "1" AND year = "2025"')
        jan_count = cursor.fetchone()[0]
        print(f"\n2025年1月的下钻数据条数: {jan_count}")
        
        # 检查具体的1月数据
        cursor.execute('SELECT location, work_type, work_category, executor FROM pue_drill_down_data WHERE month = "1" AND year = "2025" LIMIT 3')
        jan_data = cursor.fetchall()
        print("\n2025年1月的前3条数据:")
        for data in jan_data:
            print(f"  地点: {data[0]}, 作业类型: {data[1]}, 分类: {data[2]}, 执行人: {data[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"检查数据时出错: {e}")

if __name__ == "__main__":
    check_drill_down_data()
