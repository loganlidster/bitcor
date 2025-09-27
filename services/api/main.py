from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os
import json
import boto3
import psycopg2
import psycopg2.extras

app = FastAPI(title="Bitcor API")

# -----------------------------
# DB helpers
# -----------------------------
def get_conn():
    host = os.getenv("DB_HOST")
    db   = os.getenv("DB_NAME", "bitcor")
    user = os.getenv("DB_USER", "postgres")
    pwd  = os.getenv("DB_PASS")
    port = int(os.getenv("DB_PORT", "5432"))

    if not (host and pwd):
        raise RuntimeError("DB_* environment variables not set")

    return psycopg2.connect(
        host=host, dbname=db, user=user, password=pwd, port=port,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=5,
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/db/ping")
def db_ping():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 AS result")
        row = cur.fetchone()
        return {"ok": True, "result": row["result"]}

@app.get("/db/tables")
def db_tables():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT table_schema AS schema, table_name AS name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            ORDER BY table_schema, table_name;
        """)
        return {"tables": cur.fetchall()}

# -----------------------------
# Credentials storage (Secrets Manager)
# -----------------------------
class AlpacaCredIn(BaseModel):
    key_id: str
    secret: str
    paper: bool = True

def sm_client():
    # region comes from task role env automatically; fall back to us-west-1
    region = os.getenv("AWS_REGION", "us-west-1")
    return boto3.client("secretsmanager", region_name=region)

def put_json_secret(name: str, payload: dict):
    cli = sm_client()
    data = json.dumps(payload)
    try:
        cli.create_secret(Name=name, SecretString=data)
    except cli.exceptions.ResourceExistsException:
        cli.put_secret_value(SecretId=name, SecretString=data)

def get_json_secret(name: str):
    cli = sm_client()
    resp = cli.get_secret_value(SecretId=name)
    return json.loads(resp["SecretString"])

@app.post("/users/me/credentials/alpaca")
def upsert_alpaca_credentials(body: AlpacaCredIn, x_user_id: str = Header(None, alias="X-User-Id")):
    """
    Store Alpaca API credentials for the current user in AWS Secrets Manager.
    Header: X-User-Id: <your-user-id>
    """
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header is required")

    secret_name = f"bitcor/alpaca/{x_user_id}"
    payload = {"key_id": body.key_id, "secret": body.secret, "paper": body.paper}
    put_json_secret(secret_name, payload)
    return {"ok": True, "name": secret_name}

@app.get("/users/me/credentials/alpaca")
def read_alpaca_credentials(x_user_id: str = Header(None, alias="X-User-Id")):
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header is required")
    secret_name = f"bitcor/alpaca/{x_user_id}"
    try:
        data = get_json_secret(secret_name)
        # don't echo the real secret back; return shape only
        return {"ok": True, "name": secret_name, "has_secret": bool(data.get("secret")), "paper": data.get("paper")}
    except Exception:
        raise HTTPException(status_code=404, detail="No creds found")

# Optional: quick route list to confirm what is running
@app.get("/debug/routes")
def debug_routes():
    return {"routes": [r.path for r in app.router.routes]}
