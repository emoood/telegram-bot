import sqlite3

DB_PATH = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            job TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def set_job(user_id, job):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO user_profiles (user_id, job) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET job=excluded.job",
        (user_id, job)
    )
    conn.commit()
    conn.close()

def get_job(user_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT job FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None

#saves one message to a user's history, as user or assistant(agent)
def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversation_history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()

#gets the last N messages for a user, oldest first
def get_history(user_id, limit=6):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT role, content FROM conversation_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return list(reversed(rows))