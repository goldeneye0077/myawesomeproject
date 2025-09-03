#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

def check_pue_data():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # 检查PUE数据表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pue_data'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✓ pue_data表存在")
            
            # 检查数据条数
            cursor.execute('SELECT COUNT(*) FROM pue_data')
            count = cursor.fetchone()[0]
            print(f"PUE数据条数: {count}")
            
            if count > 0:
                # 查看前3条数据
                cursor.execute('SELECT * FROM pue_data LIMIT 3')
                print("\n前3条数据:")
                for row in cursor.fetchall():
                    print(f"ID: {row[0]}, 地点: {row[1]}, 月份: {row[2]}, 年份: {row[3]}, PUE值: {row[4]}")
                
                # 检查2024和2025年的数据
                cursor.execute('SELECT year, COUNT(*) FROM pue_data GROUP BY year')
                year_data = cursor.fetchall()
                print(f"\n按年份统计:")
                for year, count in year_data:
                    print(f"{year}年: {count}条")
            else:
                print("❌ pue_data表中没有数据！")
        else:
            print("❌ pue_data表不存在！")
        
        conn.close()
        
    except Exception as e:
        print(f"检查数据时出错: {e}")

if __name__ == "__main__":
    check_pue_data()
