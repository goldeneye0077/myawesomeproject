"""Seed synthetic PUEDrillDownData from template (2025-1 宝城)
Generates data for 2024-01 .. 2025-12 except 2025-01.
"""
import sqlite3
import random
from pathlib import Path

db_path = Path(__file__).with_name('db.sqlite3')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# fetch template rows
template_rows = cur.execute(
    """
    SELECT location, work_type, work_category, sequence_no, work_object, check_item,
           operation_method, benchmark_value, execution_standard, execution_status,
           detailed_situation, quantification_standard, last_month_standard,
           quantification_unit, executor
    FROM pue_drill_down_data
    WHERE year='2025' AND month='1'
    """
).fetchall()

if not template_rows:
    raise SystemExit('No template rows (2025-1) found; abort seeding.')

months = [(str(y), str(m)) for y in (2024, 2025) for m in range(1, 13)]
months.remove(('2025', '1'))
status_choices = ['已巡检', '已完成', '已整改', '无需操作']
inserted = 0
for year, month in months:
    for tpl in template_rows:
        row = list(tpl)
        row[9] = random.choice(status_choices)  # execution_status
        cur.execute(
            """
            INSERT INTO pue_drill_down_data (
                location, work_type, work_category, sequence_no, work_object, check_item,
                operation_method, benchmark_value, execution_standard, execution_status,
                detailed_situation, quantification_standard, last_month_standard,
                quantification_unit, executor, year, month
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (*row, year, month)
        )
        inserted += 1

conn.commit()
print(f"Inserted {inserted} synthetic rows.")
