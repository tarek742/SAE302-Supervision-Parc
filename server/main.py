import json
import socket
from threading import Thread

HOST = "0.0.0.0"
PORT = 8080


# Gere chaque agent connecte dans un thread separe
class Handler(Thread):
    def __init__(self, sock, client):
        Thread.__init__(self)
        self.sock = sock
        self.client = client
        self.authentifie = False
        self.agent_name = None

    def envoyer_json(self, reponse):
        # On ajoute \n pour marquer la fin du message dans le flux TCP
        message = json.dumps(reponse) + "\n"
        self.sock.sendall(message.encode("utf-8"))

    def traiter_message(self, ligne):
        try:
            data = json.loads(ligne)
        except json.JSONDecodeError:
            # Message mal forme, on repond avec une erreur sans couper le serveur
            self.envoyer_json({"status": "error", "code": 400, "msg": "JSON invalide"})
            return

        if not isinstance(data, dict):
            self.envoyer_json({"status": "error", "code": 400, "msg": "Objet JSON attendu"})
            return

        type_msg = data.get("type")

        if type_msg == "auth":
            agent_name = data.get("agent_name")
            secret = data.get("secret")
            if not agent_name or not secret:
                self.envoyer_json({"status": "error", "code": 400, "msg": "Identifiants manquants"})
                return

            # Authentification validee en memoire (verification BDD a ajouter ensuite)
            self.authentifie = True
            self.agent_name = agent_name
            print(f"[{self.agent_name}] Authentifie depuis {self.client}")
            self.envoyer_json({"status": "ok", "code": 200, "msg": "Authentifie"})
            return

        # On bloque tout autre message tant que l'agent n'est pas authentifie
        if not self.authentifie:
            self.envoyer_json({"status": "error", "code": 401, "msg": "Authentification requise"})
            return

        if type_msg == "metrics":
            # Memes cles que celles envoyees par collecte.py
            cles_requises = ("cpu", "ram", "disque", "octets_envoyes", "octets_recus")
            if not all(cle in data for cle in cles_requises):
                self.envoyer_json({"status": "error", "code": 400, "msg": "Champs de metriques manquants"})
                return

            print(f"[{self.agent_name}] Metriques recues : CPU={data['cpu']}% RAM={data['ram']}%")
            self.envoyer_json({"status": "ok", "code": 201, "msg": "Metriques recues"})
            return

        self.envoyer_json({"status": "error", "code": 400, "msg": "Type de message inconnu"})

    def run(self):
        print(f"Nouvelle connexion de {self.client}")
        # Buffer pour garder les morceaux de messages incomplets
        tampon = ""
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break

                tampon += data.decode("utf-8", errors="replace")

                # On traite des qu'on recoit une ligne complete terminee par \n
                while "\n" in tampon:
                    ligne, tampon = tampon.split("\n", 1)
                    ligne = ligne.strip()
                    if ligne:
                        self.traiter_message(ligne)

        except ConnectionResetError:
            print(f"Connexion coupee brutalement par {self.client}")
        finally:
            self.sock.close()
            nom = self.agent_name if self.agent_name else self.client
            print(f"Deconnexion de {nom}")


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permet de relancer le serveur rapidement sans attendre que le port se libere
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Serveur TCP en ecoute sur le port {PORT}...")

    try:
        while True:
            c, a = s.accept()
            Handler(c, a).start()
    except KeyboardInterrupt:
        print("\nArret du serveur.")
    finally:
        s.close()