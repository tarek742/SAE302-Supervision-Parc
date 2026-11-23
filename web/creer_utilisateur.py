"""
Crée un compte pour l'interface web (à lancer une fois, en ligne de commande).

    python creer_utilisateur.py

Le mot de passe est demandé sans s'afficher, puis haché avec argon2
avant d'être enregistré : il n'est jamais stocké en clair.
"""
from getpass import getpass

from argon2 import PasswordHasher
from dotenv import load_dotenv

import db

load_dotenv()


def main():
    username = input("Identifiant : ").strip()
    if not username:
        print("L'identifiant ne peut pas être vide.")
        return
    role = input("Rôle (admin / viewer) [admin] : ").strip() or "admin"
    if role not in ("admin", "viewer"):
        print("Rôle invalide.")
        return

    password = getpass("Mot de passe : ")
    if len(password) < 8:
        print("Le mot de passe doit faire au moins 8 caractères.")
        return
    if password != getpass("Confirmez : "):
        print("Les mots de passe ne correspondent pas.")
        return

    db.create_user(username, PasswordHasher().hash(password), role)
    print(f"Utilisateur « {username} » ({role}) créé.")


if __name__ == "__main__":
    main()