import sqlite3
from datetime import datetime
from config import DB_PATH

def add_user(user_id: int, username: str, first_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))
        conn.commit()

def add_expense(user_id: int, amount: float, category: str, comment: str = "", date_str: str = None, source: str = "manual"):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (user_id, amount, category, comment, date, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, category, comment, date_str, source))
        conn.commit()
        return cursor.lastrowid

def add_expenses_bulk(user_id: int, records: list):
    """
    records: list of tuples (amount, category, comment, date_str, source)
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO expenses (user_id, amount, category, comment, date, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(user_id, r[0], r[1], r[2], r[3], r[4]) for r in records])
        conn.commit()

def get_expenses_by_period(user_id: int, start_date: str, end_date: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, SUM(amount), COUNT(*)
            FROM expenses
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """, (user_id, start_date, end_date))
        return cursor.fetchall()

def get_total_spent(user_id: int, start_date: str, end_date: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(amount)
            FROM expenses
            WHERE user_id = ? AND date >= ? AND date <= ?
        """, (user_id, start_date, end_date))
        res = cursor.fetchone()
        return res[0] if res and res[0] else 0.0

def set_limit(user_id: int, category: str, monthly_limit: float):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO category_limits (user_id, category, monthly_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """, (user_id, category, monthly_limit))
        conn.commit()

def get_limits(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, monthly_limit FROM category_limits WHERE user_id = ?
        """, (user_id,))
        return dict(cursor.fetchall())

def get_monthly_dynamics(user_id: int):
    """
    Возвращает помесячную сумму расходов и разбивку по категориям за последние месяцы.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT substr(date, 1, 7) as month, category, SUM(amount)
            FROM expenses
            WHERE user_id = ?
            GROUP BY month, category
            ORDER BY month ASC
        """, (user_id,))
        rows = cursor.fetchall()
        
        dynamics = {}
        for month, cat, amt in rows:
            if month not in dynamics:
                dynamics[month] = {"total": 0.0, "categories": {}}
            dynamics[month]["total"] += amt
            dynamics[month]["categories"][cat] = amt
        return dynamics
