CREATE TYPE user_role AS ENUM ('admin', 'viewer');

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'viewer',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agents (
    id            SERIAL PRIMARY KEY,
    agent_name    VARCHAR(64) UNIQUE NOT NULL,
    secret_hash   TEXT NOT NULL,
    hostname      VARCHAR(128),
    last_seen     TIMESTAMPTZ,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE measures (
    id             BIGSERIAL PRIMARY KEY,
    agent_id       INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    ts             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cpu_pct        REAL NOT NULL,
    ram_pct        REAL NOT NULL,
    disk_pct       REAL NOT NULL,
    net_sent_bytes BIGINT NOT NULL,
    net_recv_bytes BIGINT NOT NULL
);

CREATE INDEX idx_measures_agent_ts ON measures (agent_id, ts DESC);

CREATE TABLE thresholds (
    agent_id        INTEGER PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    cpu_crit        REAL NOT NULL DEFAULT 90,
    ram_crit        REAL NOT NULL DEFAULT 95,
    disk_crit       REAL NOT NULL DEFAULT 95,
    offline_after_s INTEGER NOT NULL DEFAULT 60
);
