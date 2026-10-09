"""
database.py
Handles SQLite schema creation, seeding, and all DB helper functions
for the Wildlife Conflict Alert System.
"""

import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_NAME = "wildlife.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            date_time TEXT NOT NULL,
            image_name TEXT NOT NULL,
            location TEXT NOT NULL,
            threat_level TEXT NOT NULL DEFAULT 'Low'
        )
    """)

    conn.commit()

    # Seed default admin if not present
    cur.execute("SELECT * FROM users WHERE email = ?", ("admin@wildsense.com",))
    admin = cur.fetchone()
    if not admin:
        cur.execute(
            "INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                "System Admin",
                "admin@wildsense.com",
                generate_password_hash("admin123"),
                "admin",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        print("[DB] Default admin seeded -> admin@wildsense.com / admin123")

    conn.close()


# ---------------- USER HELPERS ----------------

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


def create_user(fullname, email, password_hash, role="user"):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (fullname, email, password_hash, role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


# ---------------- DETECTION HELPERS ----------------

THREAT_MAP = {
    "leopard": "High",
    "tiger": "High",
    "elephant": "High",
    "buffalo": "Medium",
    "monkey": "Medium",
    "deer": "Low",
    "cow": "Low",
    "dog": "Low",
    "cat": "Low",
    "person": "Medium",
}


def classify_threat(animal_name):
    return THREAT_MAP.get(animal_name.lower(), "Low")


def add_detection(animal_name, confidence, image_name, location="Main Gate - Zone A"):
    conn = get_db()
    threat = classify_threat(animal_name)
    conn.execute(
        """INSERT INTO detections (animal_name, confidence, date_time, image_name, location, threat_level)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            animal_name,
            confidence,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            image_name,
            location,
            threat,
        ),
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()
    return new_id


def get_all_detections():
    conn = get_db()
    rows = conn.execute("SELECT * FROM detections ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_latest_detection():
    conn = get_db()
    row = conn.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row


def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) c FROM detections").fetchone()["c"]
    today = conn.execute(
        "SELECT COUNT(*) c FROM detections WHERE date(date_time) = date('now', 'localtime')"
    ).fetchone()["c"]
    high_risk = conn.execute(
        "SELECT COUNT(*) c FROM detections WHERE threat_level = 'High'"
    ).fetchone()["c"]
    unique_animals = conn.execute(
        "SELECT COUNT(DISTINCT animal_name) c FROM detections"
    ).fetchone()["c"]
    conn.close()
    return {
        "total": total,
        "today": today,
        "high_risk": high_risk,
        "unique_animals": unique_animals,
    }


def get_animal_frequency():
    conn = get_db()
    rows = conn.execute(
        "SELECT animal_name, COUNT(*) as count FROM detections GROUP BY animal_name ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return rows


def get_daily_trend(days=7):
    conn = get_db()
    rows = conn.execute(
        """SELECT date(date_time) as day, COUNT(*) as count
           FROM detections
           WHERE date(date_time) >= date('now', ?)
           GROUP BY day ORDER BY day ASC""",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return rows


def get_threat_distribution():
    conn = get_db()
    rows = conn.execute(
        "SELECT threat_level, COUNT(*) as count FROM detections GROUP BY threat_level"
    ).fetchall()
    conn.close()
    return rows


def delete_detection_image(image_name):
    conn = get_db()
    conn.execute("DELETE FROM detections WHERE image_name = ?", (image_name,))
    conn.commit()
    conn.close()
