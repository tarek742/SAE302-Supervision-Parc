"""Creation d'un compte utilisateur (admin ou viewer)."""
import os
import sys
from getpass import getpass

import psycopg
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security import hash_secret

load_dotenv()


def main():
    username = input("Identifiant : ").strip()
    if not username:
        print("Identifiant vide.")
        return

    role = input("Role (admin/viewer) [admin] : ").strip() or "admin"
    if role not in ("admin", "viewer"):
        print("Role invalide.")
        return

    password = getpass("Mot de passe : ")
    if len(password) < 8:
        print("Mot de passe trop court (8 caracteres minimum).")
        return
    if password != getpass("Confirmez : "):
        print("Les mots de passe ne correspondent pas.")
        return

    with psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "sae_supervision"),
        user=os.getenv("DB_USER", "sae_app"),
        password=os.getenv("DB_PASSWORD", ""),
    ) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, hash_secret(password), role),
        )

    print(f"Utilisateur « {username} » ({role}) cree.")


if __name__ == "__main__":
    main()
