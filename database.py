import sqlite3
import os
from cryptography.fernet import Fernet

# ── Encryption key (store this in your .env as ENCRYPTION_KEY) ──
# Generate once with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
def get_cipher():
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in .env")
    return Fernet(key.encode())

def encrypt(value: str) -> str:
    return get_cipher().encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return get_cipher().decrypt(value.encode()).decode()


# ── DB setup ──────────────────────────────────────────────────
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_credentials (
            user_id INTEGER PRIMARY KEY,
            jira_url TEXT NOT NULL,
            jira_email TEXT NOT NULL,
            jira_api_token TEXT NOT NULL,  -- encrypted
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


# ── User operations ───────────────────────────────────────────
def create_user(email: str, password_hash: str) -> int | None:
    """Returns new user id, or None if email already exists."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        return None  # email already taken


def get_user_by_email(email: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "email": row[1], "password_hash": row[2]}
    return None


# ── Credentials operations ────────────────────────────────────
def save_credentials(user_id: int, jira_url: str, jira_email: str, jira_api_token: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_credentials (user_id, jira_url, jira_email, jira_api_token)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            jira_url = excluded.jira_url,
            jira_email = excluded.jira_email,
            jira_api_token = excluded.jira_api_token
    """, (user_id, jira_url, jira_email, encrypt(jira_api_token)))
    conn.commit()
    conn.close()


def get_credentials(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT jira_url, jira_email, jira_api_token FROM user_credentials WHERE user_id = ?",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "jira_url": row[0],
            "jira_email": row[1],
            "jira_api_token": decrypt(row[2])
        }
    return None


def has_credentials(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM user_credentials WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None
