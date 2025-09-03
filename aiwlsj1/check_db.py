#!/usr/bin/env python3
import sqlite3
import pandas as pd

# 连接数据库
conn = sqlite3.connect('db/data.db')
cursor = conn.cursor()

# 检查表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('数据库中的表:', [t[0] for t in tables])

# 检查fault_record表的数据
print('\n=== fault_record表数据 ===')
cursor.execute("SELECT sequence_no, fault_date, fault_name FROM fault_record LIMIT 3")
rows = cursor.fetchall()
for i, row in enumerate(rows):
    print(f'记录{i+1}: sequence_no={row[0]}, fault_date={row[1]}, fault_name={row[2]}')

# 检查临时表是否存在
if ('fault_record_temp',) in tables:
    print('\n=== fault_record_temp表数据 ===')
    cursor.execute("SELECT * FROM fault_record_temp LIMIT 3")
    temp_rows = cursor.fetchall()
    cursor.execute("PRAGMA table_info(fault_record_temp)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print('临时表列名:', column_names)
    
    for i, row in enumerate(temp_rows):
        print(f'临时表记录{i+1}:', dict(zip(column_names, row)))
else:
    print('\n临时表不存在')

conn.close()
