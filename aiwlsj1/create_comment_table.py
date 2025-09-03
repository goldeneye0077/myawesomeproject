import sqlite3, pathlib, sys

db_path = pathlib.Path(__file__).with_name('db.sqlite3')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS pue_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT,
    month TEXT,
    year TEXT,
    content TEXT,
    creator TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()
print('pue_comment table ensured.')
