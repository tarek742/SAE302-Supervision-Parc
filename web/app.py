"""
Interface web de supervision (SAÉ 3.02) — Flask.

  - /login     : connexion (vérification du mot de passe via db/security.py de François)
  - /logout    : déconnexion
  - /dashboard : dernière mesure et état de chaque agent
"""
import os
import sys
from datetime import datetime, timezone
from functools import wraps

import psycopg
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

# On ajoute la racine du dépôt au chemin de Python pour pouvoir importer
# le module de hachage de François (db/security.py) au lieu de le recopier.
RACINE_DEPOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE_DEPOT)
from db.security import verify_secret  # noqa: E402

import requetes  # noqa: E402

load_dotenv()  # lit le fichier .env (cherché dans web/ puis dans les dossiers parents)

app = Flask(__name__)

# Clé qui signe le cookie de session : sans elle, un utilisateur pourrait
# fabriquer un faux cookie et se faire passer pour l'admin.
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY manquant dans le fichier .env")

# Le cookie de session n'est pas lisible en JavaScript (protection XSS)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Intervalle de rafraîchissement automatique du tableau de bord (secondes)
RAFRAICHISSEMENT_S = 10


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


@app.template_filter("il_y_a")
def il_y_a(date):
    """Filtre Jinja : transforme une date en texte lisible (« il y a 12 s »)."""
    if date is None:
        return "jamais"
    secondes = int((datetime.now(timezone.utc) - date).total_seconds())
    if secondes < 60:
        return f"il y a {max(secondes, 0)} s"
    if secondes < 3600:
        return f"il y a {secondes // 60} min"
    if secondes < 86400:
        return f"il y a {secondes // 3600} h"
    return f"il y a {secondes // 86400} j"


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
        user = requetes.get_user(username)
    except psycopg.OperationalError:
        # Base injoignable : on prévient au lieu de planter
        flash("Base de données indisponible, réessayez plus tard.", "error")
        return render_template("login.html"), 503

    # Même message que l'utilisateur existe ou non : on ne révèle pas
    # quels identifiants sont valides.
    if user is None or not verify_secret(user["password_hash"], password):
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
    try:
        agents = requetes.get_tableau_de_bord()
    except psycopg.OperationalError:
        flash("Base de données indisponible, réessayez plus tard.", "error")
        agents = []

    nb_en_ligne = sum(1 for a in agents if not a["hors_ligne"])
    return render_template(
        "dashboard.html",
        agents=agents,
        nb_en_ligne=nb_en_ligne,
        rafraichissement=RAFRAICHISSEMENT_S,
    )


if __name__ == "__main__":
    # debug=True uniquement en développement (rechargement auto + messages d'erreur)
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
