#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick checker for SQLite indexes on the fault_record table.
- Lists indexes via PRAGMA index_list('fault_record')
- Shows columns for each index via PRAGMA index_info(index_name)
- Shows CREATE INDEX SQL from sqlite_master
- Validates expected indexes exist with expected columns
"""
import sqlite3
import json

DB_PATH = 'db.sqlite3'
TABLE = 'fault_record'

EXPECTED_INDEXES = {
    'ix_fault_record_province_fault_type': ['province_fault_type'],
    'ix_fault_record_cause_category': ['cause_category'],
    'ix_fault_record_notification_level': ['notification_level'],
    'ix_fault_record_fault_duration_hours': ['fault_duration_hours'],
    'ix_fault_record_fault_date': ['fault_date'],
}

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print(f"Checking indexes for table: {TABLE}\n")

    # 1) List indexes
    idx_list = cur.execute(f"PRAGMA index_list('{TABLE}')").fetchall()
    print("PRAGMA index_list results:")
    print(idx_list)
    print()

    # 2) Details per index
    details = {}
    for row in idx_list:
        # row: (seq, name, unique, origin, partial)
        _, name, unique, origin, partial = row
        cols_rows = cur.execute(f"PRAGMA index_info('{name}')").fetchall()
        cols = [r[2] for r in cols_rows]  # (seqno, cid, name)
        sql_row = cur.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
        sql = sql_row[0] if sql_row else None
        details[name] = {
            'unique': bool(unique),
            'origin': origin,
            'partial': bool(partial),
            'columns': cols,
            'sql': sql,
        }

    print("Index details:")
    print(json.dumps(details, ensure_ascii=False, indent=2))
    print()

    # 3) Validate expected indexes
    missing = []
    wrong_columns = []
    for idx_name, exp_cols in EXPECTED_INDEXES.items():
        if idx_name not in details:
            missing.append(idx_name)
        else:
            if details[idx_name]['columns'] != exp_cols:
                wrong_columns.append({
                    'index': idx_name,
                    'expected': exp_cols,
                    'actual': details[idx_name]['columns'],
                })

    print("Validation:")
    print("  Missing indexes:", missing)
    print("  Wrong column definitions:", json.dumps(wrong_columns, ensure_ascii=False))

    if not missing and not wrong_columns:
        print("\nPASS: All expected indexes exist with correct columns.")
    else:
        print("\nNOTE: See lists above to adjust as needed.")

    con.close()


if __name__ == '__main__':
    main()
