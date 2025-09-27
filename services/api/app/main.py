import os, json
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import psycopg2
import psycopg2.extras
import boto3

app = FastAPI(title="Bitcor API")

# ---------------- DB config ----------------
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "bitcor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

def _conn():
    if not DB_HOST or not DB_USER or DB_PASS is None:
        raise HTTPException(503, "DB env vars missing")
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS,
        port=DB_PORT, connect_timeout=5, cursor_factory=psycopg2.extras.RealDictCursor
    )

# ---------------- Secrets ----------------
REGION = os.getenv("AWS_REGION", "us-west-1")
sm = boto3.client("secretsmanager", region_name=REGION)

def put_user_secret(user_id: str, provider: str, payload: dict) -> str:
    """
    Stores secret JSON at /bitcor/{provider}/{user_id}.
    Reuses the same path to update (idempotent upsert).
    """
    name = f"/bitcor/{provider}/{user_id}"
    body = json.dumps(payload)
    try:
        sm.create_secret(Name=name, SecretString=body, Description=f"{provider} creds for {user_id}")
    except sm.exceptions.ResourceExistsException:
        sm.put_secret_value(SecretId=name, SecretString=body)
    return name

# ---------------- Models ----------------
class AlpacaCreds(BaseModel):
    key_id: str
    secret: str
    paper: bool = True

class PolygonCreds(BaseModel):
    api_key: str

class StrategyIn(BaseModel):
    name: str
    baseline_method: str = Field(description="e.g., prev_day_median, vwap, etc.")
    is_paper: bool = True
    budget_usd: float = Field(ge=0)
    buy_multiple: float = 1.0
    sell_multiple: float = 1.0
    trading_hours: dict = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)

# ---------------- Helper: very simple user identity ----------------
# For now, pass X-User-Id with any stable string (later we’ll switch to Cognito JWT)
def ensure_user(conn, user_id: str, email: Optional[str] = None) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE cognito_sub=%s", (user_id,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            "INSERT INTO users (email, cognito_sub) VALUES (%s,%s) RETURNING id",
            (email, user_id)
        )
        return cur.fetchone()["id"]

# ---------------- Health & DB diagnostics ----------------
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/db/ping")
def db_ping():
    with _conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 AS one")
        return {"ok": True, "result": cur.fetchone()["one"]}

@app.get("/db/tables")
def db_tables():
    with _conn() as cn, cn.cursor() as cur:
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            ORDER BY 1,2
        """)
        return {"tables": cur.fetchall()}

# ---------------- New: credentials & strategies ----------------
@app.post("/users/me/credentials/alpaca")
def set_alpaca(
    creds: AlpacaCreds,
    x_user_id: str = Header(..., alias="X-User-Id")
):
    # store secret, upsert pointer in api_credentials
    with _conn() as cn:
        user_uuid = ensure_user(cn, x_user_id)
        arn = put_user_secret(user_uuid, "alpaca", creds.dict())
        with cn.cursor() as cur:
            cur.execute("""
              INSERT INTO api_credentials (user_id, provider, secret_arn)
              VALUES (%s, 'alpaca', %s)
              ON CONFLICT (user_id, provider)
                DO UPDATE SET secret_arn = EXCLUDED.secret_arn
            """, (user_uuid, arn))
            cn.commit()
    return {"ok": True}

@app.post("/users/me/credentials/polygon")
def set_polygon(
    creds: PolygonCreds,
    x_user_id: str = Header(..., alias="X-User-Id")
):
    with _conn() as cn:
        user_uuid = ensure_user(cn, x_user_id)
        arn = put_user_secret(user_uuid, "polygon", creds.dict())
        with cn.cursor() as cur:
            cur.execute("""
              INSERT INTO api_credentials (user_id, provider, secret_arn)
              VALUES (%s, 'polygon', %s)
              ON CONFLICT (user_id, provider)
                DO UPDATE SET secret_arn = EXCLUDED.secret_arn
            """, (user_uuid, arn))
            cn.commit()
    return {"ok": True}

@app.post("/users/me/strategies")
def create_strategy(
    s: StrategyIn,
    x_user_id: str = Header(..., alias="X-User-Id")
):
    with _conn() as cn, cn.cursor() as cur:
        user_uuid = ensure_user(cn, x_user_id)
        cur.execute("""
          INSERT INTO strategies
            (user_id, name, status, is_paper, baseline_method, budget_usd,
             buy_multiple, sell_multiple, trading_hours, params)
          VALUES
            (%s,%s,'active',%s,%s,%s,%s,%s,%s,%s)
          RETURNING id
        """, (user_uuid, s.name, s.is_paper, s.baseline_method, s.budget_usd,
              s.buy_multiple, s.sell_multiple, json.dumps(s.trading_hours), json.dumps(s.params)))
        sid = cur.fetchone()["id"]
        cn.commit()
    return {"ok": True, "strategy_id": sid}
