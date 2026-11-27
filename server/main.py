"""Serveur TCP multi-threads de supervision de parc (SAÉ 3.02).

Ce module écoute les connexions entrantes des agents, vérifie leur identité
via PostgreSQL et Argon2, puis enregistre leurs métriques système en base.
"""

import json
import os
import socket
import sys
from threading import Thread

import psycopg
from dotenv import load_dotenv

# Ajout de la racine du projet au path pour importer db/security.py et charger le .env
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
from db.security import verify_secret  # noqa: E402

load_dotenv(os.path.join(RACINE, ".env"))

HOST = "0.0.0.0"
PORT = 8080


def connecter_bdd():
    """Ouvre et retourne une connexion PostgreSQL à partir des variables du .env."""
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "sae_supervision"),
        user=os.getenv("DB_USER", "sae_app"),
        password=os.getenv("DB_PASSWORD", ""),
        connect_timeout=5,
    )


class Handler(Thread):
    """Thread dédié à la gestion d'un agent connecté sur le serveur TCP."""

    def __init__(self, sock, client):
        """Initialise la session réseau d'un agent.

        Args:
            sock (socket.socket): Socket client retournée par accept().
            client (tuple): Couple (adresse_ip, port) de l'agent connecté.
        """
        Thread.__init__(self)
        self.sock = sock
        self.client = client
        self.authentifie = False
        self.agent_id = None
        self.agent_name = None

    def envoyer_json(self, reponse):
        """Sérialise un dictionnaire en JSON terminé par '\\n' et l'envoie à l'agent.

        Args:
            reponse (dict): Réponse contenant au minimum 'status', 'code' et 'msg'.
        """
        # Le saut de ligne sert de délimiteur de fin de trame dans le flux TCP
        message = json.dumps(reponse) + "\n"
        self.sock.sendall(message.encode("utf-8"))

    def traiter_message(self, ligne):
        """Décode une trame JSON et exécute l'action associée ('auth' ou 'metrics').

        Args:
            ligne (str): Ligne JSON brute reçue depuis le tampon TCP.
        """
        try:
            data = json.loads(ligne)
        except json.JSONDecodeError:
            self.envoyer_json({"status": "error", "code": 400, "msg": "JSON invalide"})
            return

        if not isinstance(data, dict):
            self.envoyer_json({"status": "error", "code": 400, "msg": "Objet JSON attendu"})
            return

        type_msg = data.get("type")

        # 1. Phase d'authentification de l'agent auprès de PostgreSQL
        if type_msg == "auth":
            agent_name = data.get("agent_name")
            secret = data.get("secret")
            if not agent_name or not secret:
                self.envoyer_json({"status": "error", "code": 400, "msg": "Identifiants manquants"})
                return

            try:
                with connecter_bdd() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, secret_hash FROM agents WHERE agent_name = %s",
                            (agent_name,),
                        )
                        resultat = cur.fetchone()

                        # Vérification de l'existence de l'agent et du secret haché en Argon2
                        if not resultat or not verify_secret(resultat[1], secret):
                            self.envoyer_json({"status": "error", "code": 401, "msg": "Identifiants invalides"})
                            return

                        self.agent_id = resultat[0]
                        self.authentifie = True
                        self.agent_name = agent_name

                        # Mise à jour de l'horodatage de dernière activité
                        cur.execute(
                            "UPDATE agents SET last_seen = NOW() WHERE id = %s",
                            (self.agent_id,),
                        )

                print(f"[{self.agent_name}] Authentifié depuis {self.client}")
                self.envoyer_json({"status": "ok", "code": 200, "msg": "Authentifie"})
            except psycopg.Error as e:
                print(f"[BDD] Erreur lors de l'authentification : {e}")
                self.envoyer_json({"status": "error", "code": 500, "msg": "Erreur base de donnees"})
            return

        # 2. Refus de toute trame tant que l'agent n'est pas authentifié
        if not self.authentifie:
            self.envoyer_json({"status": "error", "code": 401, "msg": "Authentification requise"})
            return

        # 3. Réception, validation et insertion des métriques système
        if type_msg == "metrics":
            cles_requises = ("cpu", "ram", "disque", "octets_envoyes", "octets_recus")
            if not all(cle in data for cle in cles_requises):
                self.envoyer_json({"status": "error", "code": 400, "msg": "Champs de metriques manquants"})
                return

            try:
                cpu = float(data["cpu"])
                ram = float(data["ram"])
                disque = float(data["disque"])
                # Conversion explicite en int car la colonne PostgreSQL est de type BIGINT
                octets_envoyes = int(data["octets_envoyes"])
                octets_recus = int(data["octets_recus"])
            except (TypeError, ValueError):
                self.envoyer_json({"status": "error", "code": 400, "msg": "Valeurs de metriques invalides"})
                return

            try:
                with connecter_bdd() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO measures (agent_id, cpu_pct, ram_pct, disk_pct, net_sent_bytes, net_recv_bytes)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (self.agent_id, cpu, ram, disque, octets_envoyes, octets_recus),
                        )
                        cur.execute(
                            "UPDATE agents SET last_seen = NOW() WHERE id = %s",
                            (self.agent_id,),
                        )

                print(
                    f"[{self.agent_name}] CPU={cpu}% | RAM={ram}% | Disque={disque}% | "
                    f"Envoi={octets_envoyes}o | Recu={octets_recus}o"
                )
                self.envoyer_json({"status": "ok", "code": 201, "msg": "Metriques enregistrees"})
            except psycopg.Error as e:
                print(f"[BDD] Erreur lors de l'insertion : {e}")
                self.envoyer_json({"status": "error", "code": 500, "msg": "Erreur base de donnees"})
            return

        self.envoyer_json({"status": "error", "code": 400, "msg": "Type de message inconnu"})

    def run(self):
        """Lit le flux TCP en continu et découpe les messages complets sur '\\n'."""
        print(f"Nouvelle connexion de {self.client}")
        # Tampon permettant de reconstituer les messages reçus en plusieurs morceaux
        tampon = ""
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break

                tampon += data.decode("utf-8", errors="replace")

                while "\n" in tampon:
                    ligne, tampon = tampon.split("\n", 1)
                    ligne = ligne.strip()
                    if ligne:
                        self.traiter_message(ligne)

        except ConnectionResetError:
            print(f"Connexion coupée brutalement par {self.client}")
        finally:
            self.sock.close()
            nom = self.agent_name if self.agent_name else self.client
            print(f"Déconnexion de {nom}")


if __name__ == "__main__":
    serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Autorise le redémarrage immédiat du serveur sans attendre la libération du port
    serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serveur.bind((HOST, PORT))
    serveur.listen(5)
    print(f"Serveur TCP en écoute sur le port {PORT}...")

    try:
        while True:
            client_sock, client_addr = serveur.accept()
            Handler(client_sock, client_addr).start()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        serveur.close()