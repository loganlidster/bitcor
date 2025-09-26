-- Core multi-tenant tables for Bitcor

CREATE TABLE IF NOT EXISTS tenants (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,              -- Cognito sub
  tenant_id TEXT NOT NULL REFERENCES tenants(id),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS settings (
  id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL REFERENCES tenants(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  baseline_method TEXT NOT NULL DEFAULT 'median_prev_day',
  multiple_up DOUBLE PRECISION NOT NULL DEFAULT 1.02,
  multiple_down DOUBLE PRECISION NOT NULL DEFAULT 0.98,
  enabled BOOLEAN NOT NULL DEFAULT false,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trades (
  id BIGSERIAL PRIMARY KEY,
  tenant_id TEXT NOT NULL REFERENCES tenants(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty NUMERIC(36,12) NOT NULL,
  price NUMERIC(36,12) NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  extra JSONB
);

CREATE TABLE IF NOT EXISTS price_ohlcv (
  dt DATE NOT NULL,
  symbol TEXT NOT NULL,
  open NUMERIC(36,12),
  high NUMERIC(36,12),
  low NUMERIC(36,12),
  close NUMERIC(36,12),
  volume NUMERIC(36,2),
  PRIMARY KEY (dt, symbol)
);
