"""
Interface web de supervision (SAÉ 3.02) — Flask.

Étape 1 : connexion de l'administrateur.
  - /login     : formulaire de connexion
  - /logout    : déconnexion
  - /dashboard : page protégée (contenu ajouté à l'étape 2)
"""
import os
from functools import wraps

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

import db

load_dotenv()  # lit le fichier .env et remplit les variables d'environnement

app = Flask(__name__)

# Clé qui signe le cookie de session : sans elle, un utilisateur pourrait
# fabriquer un faux cookie et se faire passer pour l'admin.
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY manquant dans le fichier .env")

# Le cookie de session n'est pas lisible en JavaScript (protection XSS)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

ph = PasswordHasher()  # argon2 : hachage salé, le sel est stocké dans le hash


def login_required(vue):
    """Décorateur : redirige vers /login si personne n'est connecté.

    On le place au-dessus de chaque route à protéger : @login_required
    """
    @wraps(vue)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter.", "info")
            return redirect(url_for("login"))
        return vue(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    # GET : on affiche simplement le formulaire
    if request.method == "GET":
        return render_template("login.html")

    # POST : le formulaire a été envoyé
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Identifiant et mot de passe obligatoires.", "error")
        return render_template("login.html"), 400

    try:
        user = db.get_user(username)
    except psycopg.OperationalError:
        # Base injoignable : on prévient au lieu de planter
        flash("Base de données indisponible, réessayez plus tard.", "error")
        return render_template("login.html"), 503

    # Même message que l'utilisateur existe ou non : on ne révèle pas
    # quels identifiants sont valides.
    try:
        if user is None:
            raise VerifyMismatchError
        ph.verify(user["password_hash"], password)
    except (VerifyMismatchError, InvalidHashError):
        flash("Identifiant ou mot de passe incorrect.", "error")
        return render_template("login.html", username=username), 401

    # Connexion réussie : on repart d'une session vide puis on y range l'utilisateur
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    # Étape 2 : on affichera ici la dernière mesure de chaque agent
    return render_template("dashboard.html")


if __name__ == "__main__":
    # debug=True uniquement en développement (rechargement auto + messages d'erreur)
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
