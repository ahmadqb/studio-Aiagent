import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "studio_data.db")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price_eur INTEGER NOT NULL,
        duration_min INTEGER NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE studio_info (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
""")

cursor.executemany(
    "INSERT INTO services (name, price_eur, duration_min) VALUES (?, ?, ?)",
    [
        ("Underarm waxing", 25, 20),
        ("Leg waxing", 45, 40),
        ("Lash lifting", 60, 60),
    ],
)

cursor.executemany(
    "INSERT INTO studio_info (key, value) VALUES (?, ?)",
    [
        ("opening_hours", "Monday to Friday, from 10 a.m. to 6 p.m."),
        ("cancellation_policy", "Appointments can be cancelled up to 24 hours beforehand."),
        ("referral_policy", "Medical questions and complaints must be referred to the studio team."),
    ],
)

conn.commit()
conn.close()
print("Database created successfully!")