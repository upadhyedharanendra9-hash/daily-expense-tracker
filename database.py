import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "expenses.db"

def hash_password(password: str) -> str:
    """Securely hash passwords using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Create Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        
        # 2. Migration Check: Drop old version of expenses if it lacks user_id
        try:
            cursor.execute("SELECT user_id FROM expenses LIMIT 1")
        except sqlite3.OperationalError:
            # If this column check fails, the old table structure is conflicting. Clear it.
            cursor.execute("DROP TABLE IF EXISTS expenses")
            
        # 3. Create Modern Expenses Table linked to user_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                item TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                category TEXT NOT NULL,
                reasoning TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

def create_user(username, password):
    """Register a new user."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            hashed = hash_password(password)
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False  # Username already exists

def authenticate_user(username, password):
    """Verify login credentials."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed))
        row = cursor.fetchone()
        return row[0] if row else None

def save_expenses(user_id, expenses_list):
    """Save expenses for a specific user."""
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for exp in expenses_list:
            cursor.execute("""
                INSERT INTO expenses (user_id, date, item, amount, currency, category, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, today, exp.item, exp.amount, exp.currency, exp.category, exp.reasoning))
        conn.commit()

def get_daily_summary(user_id, date_str: str):
    """Fetch expenses only for the logged-in user."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE user_id = ? AND date = ?", (user_id, date_str))
        return [dict(row) for row in cursor.fetchall()]
