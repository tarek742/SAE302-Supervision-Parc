import socket
from threading import Thread

HOST = "0.0.0.0"
PORT = 8080


class Handler(Thread):
    def __init__(self, sock, client):
        Thread.__init__(self)
        self.sock = sock
        self.client = client

    def run(self):
        print(f"Nouvelle connexion de {self.client}")
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    # Le client a fermé la connexion
                    break

                message = data.decode("utf-8").strip()
                print(f"[{self.client[0]}:{self.client[1]}] {message}")

                # Petit accusé de réception pour confirmer au client
                self.sock.send("OK\n".encode("utf-8"))

        except ConnectionResetError:
            print(f"Connexion coupee brutalement par {self.client}")
        finally:
            self.sock.close()
            print(f"Deconnexion de {self.client}")


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permet de relancer le serveur tout de suite sans erreur
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