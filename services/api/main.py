from fastapi import FastAPI
import os
import psycopg2
import psycopg2.extras

app = FastAPI(title="Bitcor API")

@app.get("/healthz")
def healthz():
    # pure health, no DB, always OK if the process is running
    return {"ok": True}

def _conn():
    # used only by /db* endpoints; if env vars are missing, only those routes fail
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ.get("DB_NAME", "bitcor"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        connect_timeout=5,
    )

@app.get("/db/ping")
def db_ping():
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1;")
        return {"ok": True, "result": cur.fetchone()[0]}

@app.get("/db/tables")
def db_tables():
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_type='BASE TABLE' ORDER BY 1,2;")
        return {"tables": [{"schema": r[0], "name": r[1]} for r in cur.fetchall()]}
