import logging
import os
import sqlite3

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("studio_api")

app = FastAPI(title="Studio Info API (fictional test data)")

# Database lives next to this file (works locally and in Docker)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "studio_data.db")


def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def service_to_dict(row):
    return {"name": row[0], "price_eur": row[1], "duration_min": row[2]}


@app.get("/api/services")
def list_services():
    """All services with price and duration."""
    rows = query("SELECT name, price_eur, duration_min FROM services ORDER BY name")
    return [service_to_dict(r) for r in rows]


@app.get("/api/service")
def find_service(name: str):
    """Services whose name contains the search text. [] if nothing matches."""
    rows = query(
        "SELECT name, price_eur, duration_min FROM services WHERE LOWER(name) LIKE ?",
        (f"%{name.strip().lower()}%",),
    )
    logger.info("service search '%s' -> %d rows", name, len(rows))
    return [service_to_dict(r) for r in rows]


@app.get("/api/studio_info")
def get_studio_info():
    """Opening hours, cancellation policy and referral policy."""
    rows = query("SELECT key, value FROM studio_info")
    return {key: value for key, value in rows}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)