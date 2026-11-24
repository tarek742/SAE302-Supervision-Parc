"""
Requêtes PostgreSQL utilisées par l'interface web.

Les identifiants de connexion ne sont JAMAIS écrits dans le code :
ils sont lus dans les variables d'environnement (fichier .env, non versionné).

(Ce fichier s'appelait db.py : il a été renommé pour ne pas entrer en
conflit avec le dossier db/ de François, qu'on importe pour le hachage.)
"""
import os

import psycopg
from psycopg.rows import dict_row

# Valeurs utilisées quand un agent n'a pas encore de ligne dans "thresholds".
# Ce sont les mêmes que les DEFAULT du schéma de François.
SEUILS_PAR_DEFAUT = {
    "cpu_crit": 90,
    "ram_crit": 95,
    "disk_crit": 95,
    "offline_after_s": 60,
}


def get_connection():
    """Ouvre une connexion à PostgreSQL.

    dict_row permet de récupérer chaque ligne sous forme de dictionnaire
    (ligne["username"]) au lieu d'un tuple (ligne[1]) : plus lisible.
    """
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "supervision"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        row_factory=dict_row,
        connect_timeout=5,
    )


def get_user(username):
    """Renvoie l'utilisateur (id, username, password_hash, role) ou None s'il n'existe pas.

    La requête est paramétrée (%s) : psycopg échappe la valeur lui-même,
    ce qui protège contre les injections SQL.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()


# Une ligne par agent avec :
#   - sa dernière mesure (sous-requête LATERAL : pour chaque agent, on prend
#     la mesure la plus récente ; l'index (agent_id, ts DESC) de François
#     rend cette recherche instantanée même avec des millions de mesures)
#   - ses seuils (LEFT JOIN + COALESCE : valeurs par défaut s'il n'en a pas)
#   - son état : hors ligne si aucune nouvelle depuis offline_after_s secondes
REQUETE_TABLEAU_DE_BORD = """
SELECT
    a.id,
    a.agent_name,
    a.hostname,
    a.last_seen,
    m.ts       AS derniere_mesure,
    m.cpu_pct,
    m.ram_pct,
    m.disk_pct,
    COALESCE(t.cpu_crit,        %(cpu_crit)s)        AS cpu_crit,
    COALESCE(t.ram_crit,        %(ram_crit)s)        AS ram_crit,
    COALESCE(t.disk_crit,       %(disk_crit)s)       AS disk_crit,
    COALESCE(t.offline_after_s, %(offline_after_s)s) AS offline_after_s,
    (
        a.last_seen IS NULL
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
    """Renvoie la liste des agents avec leur dernière mesure, leurs seuils et leur état."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(REQUETE_TABLEAU_DE_BORD, SEUILS_PAR_DEFAUT)
            return cur.fetchall()
