"""Requêtes PostgreSQL de l'interface web."""
import os

import psycopg
from psycopg.rows import dict_row

# Mêmes valeurs que les DEFAULT de la table thresholds
SEUILS_PAR_DEFAUT = {
    "cpu_crit": 90,
    "ram_crit": 95,
    "disk_crit": 95,
    "offline_after_s": 60,
}


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "sae_supervision"),
        user=os.getenv("DB_USER", "sae_app"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
        connect_timeout=5,
    )


def get_user(username):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = %s",
            (username,),
        )
        return cur.fetchone()


# Dernière mesure de chaque agent (LATERAL + index agent_id, ts DESC),
# seuils par défaut si l'agent n'a pas de ligne dans thresholds,
# hors ligne si last_seen est plus vieux que offline_after_s.
REQUETE_TABLEAU_DE_BORD = """
SELECT
    a.id, a.agent_name, a.hostname, a.last_seen,
    m.ts AS derniere_mesure, m.cpu_pct, m.ram_pct, m.disk_pct,
    COALESCE(t.cpu_crit,        %(cpu_crit)s)        AS cpu_crit,
    COALESCE(t.ram_crit,        %(ram_crit)s)        AS ram_crit,
    COALESCE(t.disk_crit,       %(disk_crit)s)       AS disk_crit,
    COALESCE(t.offline_after_s, %(offline_after_s)s) AS offline_after_s,
    (a.last_seen IS NULL
     OR a.last_seen < NOW() - make_interval(
            secs => COALESCE(t.offline_after_s, %(offline_after_s)s))
    ) AS hors_ligne
FROM agents a
LEFT JOIN LATERAL (
    SELECT ts, cpu_pct, ram_pct, disk_pct
    FROM measures
    WHERE agent_id = a.id
    ORDER BY ts DESC
    LIMIT 1
) m ON TRUE
LEFT JOIN thresholds t ON t.agent_id = a.id
ORDER BY a.agent_name
"""


def get_tableau_de_bord():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(REQUETE_TABLEAU_DE_BORD, SEUILS_PAR_DEFAUT)
        return cur.fetchall()


def get_agent(agent_id):
    requete = REQUETE_TABLEAU_DE_BORD.replace(
        "ORDER BY a.agent_name", "WHERE a.id = %(agent_id)s"
    )
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(requete, {**SEUILS_PAR_DEFAUT, "agent_id": agent_id})
        return cur.fetchone()


def get_historique(agent_id, limite=100):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT ts, cpu_pct, ram_pct, disk_pct, net_sent_bytes, net_recv_bytes
            FROM measures
            WHERE agent_id = %s
            ORDER BY ts DESC
            LIMIT %s
            """,
            (agent_id, limite),
        )
        return cur.fetchall()
