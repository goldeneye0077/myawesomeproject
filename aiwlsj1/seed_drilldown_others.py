"""Seed synthetic PUEDrillDownData for other locations using 宝城 template"""
import sqlite3, random
from pathlib import Path

db = Path(__file__).with_name('db.sqlite3')
conn = sqlite3.connect(db)
cur = conn.cursor()

# template rows from 宝城 2025-1
template_rows = cur.execute("""
SELECT work_type, work_category, sequence_no, work_object, check_item,
       operation_method, benchmark_value, execution_standard, execution_status,
       detailed_situation, quantification_standard, last_month_standard,
       quantification_unit, executor
FROM pue_drill_down_data
WHERE location='宝城' AND year='2025' AND month='1'
""").fetchall()
if not template_rows:
    raise SystemExit('Template rows not found; ensure 宝城 2025-1 exists')

# get other locations from pue_data
locations = [row[0] for row in cur.execute("SELECT DISTINCT location FROM pue_data").fetchall()]
locations = [loc for loc in locations if loc != '宝城']

months = [(str(y), str(m)) for y in (2024, 2025) for m in range(1, 13)]
status_choices = ['已巡检', '已完成', '已整改', '无需操作']
inserted = 0
for location in locations:
    for year, month in months:
        # skip if already exists
        exists = cur.execute("SELECT 1 FROM pue_drill_down_data WHERE location=? AND year=? AND month=? LIMIT 1", (location, year, month)).fetchone()
        if exists:
            continue
        for tpl in template_rows:
            (work_type, work_category, sequence_no, work_object, check_item,
             operation_method, benchmark_value, execution_standard, execution_status,
             detailed_situation, quantification_standard, last_month_standard,
             quantification_unit, executor) = tpl
            execution_status = random.choice(status_choices)
            cur.execute(
                """INSERT INTO pue_drill_down_data (
                    location, work_type, work_category, sequence_no, work_object, check_item,
                    operation_method, benchmark_value, execution_standard, execution_status,
                    detailed_situation, quantification_standard, last_month_standard,
                    quantification_unit, executor, year, month
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (location, work_type, work_category, sequence_no, work_object, check_item,
                 operation_method, benchmark_value, execution_standard, execution_status,
                 detailed_situation, quantification_standard, last_month_standard,
                 quantification_unit, executor, year, month)
            )
            inserted += 1

conn.commit()
print(f'Inserted {inserted} rows for other locations: {", ".join(locations)}')
