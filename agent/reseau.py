#!/usr/bin/python3
import socket
import json
import time
from collecte import recuperer_metrique


def envoyer_donnees(host="127.0.0.1", port=8080, intervalle=10, delai_reconnexion=5):
    """
    Établit une connexion TCP persistante avec le serveur et envoie
    périodiquement les métriques système au format JSON.
    Gère la reconnexion automatique et l'arrêt propre via Ctrl+C.
    """
    s = None
    try:
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)

            try:
                s.connect((host, port))
                print(f"[RESEAU] Connecté au serveur {host}:{port}")
            except (socket.error, OSError) as e:
                print(f"[RESEAU] Échec de connexion ({e}). Nouvelle tentative dans {delai_reconnexion}s...")
                s.close()
                s = None
                time.sleep(delai_reconnexion)
                continue

            while True:
                try:
                    metriques = recuperer_metrique()
                    message = (json.dumps(metriques) + "\n").encode("utf-8")
                    s.sendall(message)

                    reponse = s.recv(1024)
                    if not reponse:
                        print("[RESEAU] Connexion fermée par le serveur.")
                        break
                    print(f"[RESEAU] Réponse du serveur : {reponse.decode('utf-8').strip()}")
                    time.sleep(intervalle)
                    
                except (socket.error, OSError) as e:
                    print(f"[RESEAU] Perte de connexion lors de l'envoi : {e}")
                    break

            if s:
                s.close()
                s = None
            time.sleep(delai_reconnexion)

    except KeyboardInterrupt:
        print("\n[AGENT] Arrêt demandé par l'utilisateur (Ctrl+C).")
    finally:
        if s:
            s.close()
            print("[RESEAU] Socket fermé proprement.")


if __name__ == "__main__":
    envoyer_donnees()