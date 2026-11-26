#!/usr/bin/python3
from collecte import recuperer_metrique
from reseau import envoyer_donnees
import argparse, os, dotenv

dotenv.load_dotenv()  # Charger les variables d'environnement depuis le fichier .env

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="127.0.0.1", help="Adresse IP du serveur")
parser.add_argument("--port", type=int, default=8080, help="Port du serveur")
parser.add_argument("--name", default="Agent1", help="Nom de l'agent")
parser.add_argument("--secret", default=os.getenv("AGENT_SECRET"), help="Secret de l'agent")
parser.add_argument("--simuler", action="store_true", help="Simuler les métriques au lieu de les récupérer réellement")

args = parser.parse_args()

if __name__ == "__main__":
    try:
            envoyer_donnees(simuler=args.simuler, nom=args.name, secret=args.secret)
    except KeyboardInterrupt:
        print("\n[AGENT] Arrêt demandé par l'utilisateur (Ctrl+C).")