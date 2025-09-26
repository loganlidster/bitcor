import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from jose import jwt

app = FastAPI(title="Bitcor API", version="0.2.0")

DB_HOST = os.getenv("DB_HOST") or os.getenv("AURORA_PG_HOST") or ""
DB_NAME = os.getenv("DB_NAME", "bitcor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "")

def get_db_conn():
  if not DB_HOST:
    return None
  return psycopg2.connect(
    host=DB_HOST, dbname=DB_NAME, user=DB_USER,
    password=DB_PASSWORD, connect_timeout=5
  )

@app.get("/healthz")
def healthz():
  return {"ok": True}

class SettingsIn(BaseModel):
  baseline_method: Optional[str] = "median_prev_day"
  multiple_up: Optional[float] = 1.02
  multiple_down: Optional[float] = 0.98
  enabled: Optional[bool] = False

def get_current_user(request: Request) -> Dict[str, Any]:
  auth = request.headers.get("authorization") or request.headers.get("Authorization")
  if not auth or not auth.lower().startswith("bearer "):
    raise HTTPException(401, "Missing bearer token")
  token = auth.split(" ", 1)[1]
  try:
    claims = jwt.get_unverified_claims(token)
  except Exception:
    raise HTTPException(401, "Invalid token")
  if claims.get("aud") and COGNITO_APP_CLIENT_ID and claims["aud"] != COGNITO_APP_CLIENT_ID:
    raise HTTPException(401, "Invalid audience")
  return {"sub": claims.get("sub"), "email": claims.get("email")}

@app.get("/me")
def me(user=Depends(get_current_user)):
  return {"user_id": user["sub"], "email": user.get("email", "")}

@app.get("/settings")
def get_settings(user=Depends(get_current_user)):
  conn = get_db_conn()
  if not conn:
    return {}
  with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
    cur.execute("SELECT baseline_method, multiple_up, multiple_down, enabled FROM settings WHERE user_id=%s ORDER BY updated_at DESC LIMIT 1", (user["sub"],))
    row = cur.fetchone()
    return row or {}

@app.put("/settings")
def put_settings(payload: SettingsIn, user=Depends(get_current_user)):
  conn = get_db_conn()
  if not conn:
    raise HTTPException(503, "DB not ready")
  with conn, conn.cursor() as cur:
    cur.execute("""
      INSERT INTO settings (tenant_id, user_id, baseline_method, multiple_up, multiple_down, enabled)
      VALUES (%s, %s, %s, %s, %s, %s)
    """, ("default", user["sub"], payload.baseline_method, payload.multiple_up, payload.multiple_down, payload.enabled))
  return {"ok": True}
