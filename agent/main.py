#!/usr/bin/python3
from collecte import recuperer_metrique
from reseau import envoyer_donnees

if __name__ == "__main__":
    try:
            envoyer_donnees(host="127.0.0.1", port=8080, intervalle=10)
    except KeyboardInterrupt:
        print("\n[AGENT] Arrêt demandé par l'utilisateur (Ctrl+C).")