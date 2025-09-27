import logging
import os
from fastapi import FastAPI, HTTPException
import psycopg2
import psycopg2.extras

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("bitcor-api")

app = FastAPI(title="Bitcor API")

@app.get("/healthz")
def healthz():
    return {"ok": True}

def get_env(name: str, default=None, required=True):
    v = os.getenv(name, default)
    if required and (v is None or v == ""):
        raise KeyError(f"Missing env: {name}")
    return v

def _conn():
    try:
        host = get_env("DB_HOST")
        db = get_env("DB_NAME", "bitcor", required=False)
        usr = get_env("DB_USER")
        pwd = get_env("DB_PASS")
        port = int(get_env("DB_PORT", "5432", required=False))
        sslmode = get_env("DB_SSLMODE", "prefer", required=False)

        log.info(f"Connecting to Postgres host={host} db={db} user={usr} port={port} sslmode={sslmode}")
        return psycopg2.connect(
            host=host,
            dbname=db,
            user=usr,
            password=pwd,
            port=port,
            connect_timeout=5,
            sslmode=sslmode,  # 'prefer' works for Aurora defaults
        )
    except Exception as e:
        log.exception("Failed creating DB connection")
        raise

@app.get("/debug/env")
def debug_env():
    # Do NOT show secrets. This is for temporary debugging only.
    try:
        return {
            "DB_HOST": os.getenv("DB_HOST"),
            "DB_NAME": os.getenv("DB_NAME"),
            "DB_USER": os.getenv("DB_USER"),
            "DB_PORT": os.getenv("DB_PORT", "5432"),
            "has_DB_PASS": bool(os.getenv("DB_PASS")),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/db/ping")
def db_ping():
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1;")
            return {"ok": True, "result": cur.fetchone()[0]}
    except KeyError as ke:
        raise HTTPException(status_code=503, detail=str(ke))
    except Exception as e:
        log.exception("db_ping failed")
        raise HTTPException(status_code=500, detail="DB connection failed")

@app.get("/db/tables")
def db_tables():
    try:
        with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type='BASE TABLE'
                ORDER BY 1,2;
            """)
            return {"tables": [{"schema": r[0], "name": r[1]} for r in cur.fetchall()]}
    except KeyError as ke:
        raise HTTPException(status_code=503, detail=str(ke))
    except Exception as e:
        log.exception("db_tables failed")
        raise HTTPException(status_code=500, detail="DB query failed")
