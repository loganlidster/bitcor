from fastapi import FastAPI
import psycopg2
import psycopg2.extras
import os

app = FastAPI(title="Bitcor API")

# --- DB connection config ---
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "bitcor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")

def _db_conn():
    """Helper: open a Postgres connection"""
    if not DB_HOST:
        return None
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        connect_timeout=5,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# --- Routes ---
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/db/ping")
def db_ping():
    """Simple connectivity test"""
    cn = _db_conn()
    if not cn:
        return {"ok": False, "error": "DB_HOST not set"}
    try:
        with cn.cursor() as cur:
            cur.execute("SELECT 1 AS one;")
            row = cur.fetchone()
        return {"ok": True, "result": row["one"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        cn.close()

@app.get("/db/tables")
def db_tables():
    """List tables in the connected database"""
    cn = _db_conn()
    if not cn:
        return {"ok": False, "error": "DB_HOST not set"}
    try:
        with cn.cursor() as cur:
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type='BASE TABLE'
                ORDER BY table_schema, table_name;
            """)
            rows = cur.fetchall()
        return {"ok": True, "db": DB_NAME, "host": DB_HOST, "tables": rows}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        cn.close()
