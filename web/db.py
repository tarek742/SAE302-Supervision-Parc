"""
Accès à la base PostgreSQL pour l'interface web.

Les identifiants de connexion ne sont JAMAIS écrits dans le code :
ils sont lus dans les variables d'environnement (fichier .env, non versionné).
"""
import os

import psycopg
from psycopg.rows import dict_row


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


def create_user(username, password_hash, role):
    """Ajoute un utilisateur. Le mot de passe doit déjà être haché."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, password_hash, role),
            )
