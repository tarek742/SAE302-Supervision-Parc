"""Interface web de supervision (Flask)."""
import os
import sys
from datetime import datetime, timezone
from functools import wraps

import psycopg
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
from db.security import verify_secret  # noqa: E402

import requetes  # noqa: E402

load_dotenv(os.path.join(RACINE, ".env"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY manquant dans le .env")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

RAFRAICHISSEMENT_S = 10


def login_required(vue):
    @wraps(vue)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter.", "info")
            return redirect(url_for("login"))
        return vue(*args, **kwargs)
    return wrapper


@app.template_filter("il_y_a")
def il_y_a(date):
    if date is None:
        return "jamais"
    s = int((datetime.now(timezone.utc) - date).total_seconds())
    if s < 60:
        return f"il y a {max(s, 0)} s"
    if s < 3600:
        return f"il y a {s // 60} min"
    if s < 86400:
        return f"il y a {s // 3600} h"
    return f"il y a {s // 86400} j"


@app.template_filter("heure")
def heure(date):
    return date.astimezone().strftime("%d/%m %H:%M:%S")


@app.template_filter("debit")
def debit(octets):
    if octets < 1024 * 1024:
        return f"{octets / 1024:.1f} Ko"
    return f"{octets / (1024 * 1024):.1f} Mo"


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        flash("Identifiant et mot de passe obligatoires.", "error")
        return render_template("login.html"), 400

    try:
        user = requetes.get_user(username)
    except psycopg.OperationalError:
        flash("Base de données indisponible, réessayez plus tard.", "error")
        return render_template("login.html"), 503

    # Même message dans les deux cas pour ne pas révéler les identifiants existants
    if user is None or not verify_secret(user["password_hash"], password):
        flash("Identifiant ou mot de passe incorrect.", "error")
        return render_template("login.html", username=username), 401

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

    return render_template(
        "dashboard.html",
        agents=agents,
        nb_en_ligne=sum(1 for a in agents if not a["hors_ligne"]),
        rafraichissement=RAFRAICHISSEMENT_S,
    )


@app.route("/agent/<int:agent_id>")
@login_required
def historique(agent_id):
    try:
        agent = requetes.get_agent(agent_id)
        if agent is None:
            abort(404)
        mesures = requetes.get_historique(agent_id)
    except psycopg.OperationalError:
        flash("Base de données indisponible, réessayez plus tard.", "error")
        return redirect(url_for("dashboard"))

    return render_template("historique.html", agent=agent, mesures=mesures)


@app.errorhandler(404)
def page_introuvable(erreur):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
