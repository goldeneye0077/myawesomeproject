import os

# SQLAlchemy 数据库连接字符串
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")
