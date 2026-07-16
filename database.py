import sqlite3
from datetime import datetime

DB_NAME = "expenses.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                item TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                category TEXT NOT NULL,
                reasoning TEXT
            )
        """)
        conn.commit()

def save_expenses(expenses_list):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for exp in expenses_list:
            cursor.execute("""
                INSERT INTO expenses (date, item, amount, currency, category, reasoning)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (today, exp.item, exp.amount, exp.currency, exp.category, exp.reasoning))
        conn.commit()

def get_daily_summary(date_str: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE date = ?", (date_str,))
        return [dict(row) for row in cursor.fetchall()]
