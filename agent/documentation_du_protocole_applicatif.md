# Documentation du Protocole Applicatif — Supervision de Parc (SAÉ 302)

Ce document spécifie le protocole de communication applicatif utilisé entre les **agents de collecte** (clients) et le **serveur central** (collecteur) dans le cadre du système de supervision de parc informatique.

---

## 1. Couche Transport et Format Général

* **Protocole de transport :** TCP (sockets orientées connexion).
* **Adresse et port par défaut :** `127.0.0.1:8080` (configurable côté agent via CLI).
* **Encodage :** `UTF-8`.
* **Format des messages :** Objets **JSON** sérialisés sur une seule ligne (sans retour à la ligne interne).
* **Délimiteur de fin de trame :** Chaque message JSON doit impérativement se terminer par un caractère saut de ligne `\n` (`0x0A`) afin de permettre le découpage des flux TCP côté serveur.
* **Comportement temporel :**
  * **Période d'envoi :** Une trame de métriques toutes les $10\text{ secondes}$ par défaut.
  * **Tolérance aux pannes :** En cas de perte de connexion ou d'indisponibilité du serveur, l'agent tente une reconnexion automatique toutes les $5\text{ secondes}$.

---

## 2. Cinématique des Échanges

La communication est initiée par l'agent et suit un cycle strict en deux phases (authentification préalable obligatoire avant toute transmission de mesures) :

```text
   AGENT (Client)                                     SERVEUR TCP
         |                                                 |
         |---------------- 1. Connexion TCP -------------->|
         |<--------------- Connexion établie --------------|
         |                                                 |
         |--- 2. Trame AUTH (agent_name + secret) + \n --->|
         |<-- 3. Réponse JSON (status: "ok") + \n ---------|
         |                                                 |
         |   [Boucle toutes les 10 secondes]               |
         |--- 4. Trame METRICS (cpu, ram, ...) + \n ------>|
         |<-- 5. Acquittement JSON (status: "ok") + \n ----|
         |                                                 |
```

> **Règle de sécurité :** Toute trame de métriques envoyée avant la validation de l'étape 3 est systématiquement rejetée par le serveur avec un code d'erreur `401`.

---

## 3. Spécification des Trames (Agent $\rightarrow$ Serveur)

Chaque requête envoyée par l'agent contient une clé obligatoire `"type"` permettant au serveur d'identifier la nature du message.

### 3.1. Trame d'authentification (`"type": "auth"`)

Envoyée une seule fois immédiatement après l'ouverture de la socket TCP.

| Clé | Type JSON | Obligatoire | Description |
| :--- | :--- | :---: | :--- |
| `type` | `string` | Oui | Doit valoir `"auth"`. |
| `agent_name` | `string` | Oui | Identifiant unique de l'agent supervisé (ex. `"agent2"`). |
| `secret` | `string` | Oui | Clé partagée d'authentification de l'agent. |

**Exemple de trame envoyée :**
```json
{"type": "auth", "agent_name": "agent2", "secret": "mon_secret_partage"}
```

---

### 3.2. Trame de métriques système (`"type": "metrics"`)

Envoyée périodiquement une fois la session authentifiée. Les types de données respectent le schéma de la table PostgreSQL `measures` (`REAL` pour les pourcentages, `BIGINT` pour les volumes d'octets).

| Clé | Type JSON | Unité | Contrainte BDD | Description |
| :--- | :--- | :---: | :---: | :--- |
| `type` | `string` | — | — | Doit valoir `"metrics"`. |
| `cpu` | `float` | $\%$ | `REAL` | Taux d'utilisation global du processeur ($0.0$ à $100.0$). |
| `ram` | `float` | $\%$ | `REAL` | Pourcentage de mémoire vive utilisée ($0.0$ à $100.0$). |
| `disque` | `float` | $\%$ | `REAL` | Pourcentage d'occupation de la partition principale ($0.0$ à $100.0$). |
| `octets_envoyes` | `integer` | Octets | `BIGINT` | Volume cumulé d'octets émis sur l'interface réseau (entier strict). |
| `octets_recus` | `integer` | Octets | `BIGINT` | Volume cumulé d'octets reçus sur l'interface réseau (entier strict). |

**Exemple de trame envoyée :**
```json
{"type": "metrics", "cpu": 18.4, "ram": 62.1, "disque": 45.0, "octets_envoyes": 1548920, "octets_recus": 9845120}
```

---

## 4. Réponses et Codes d'Erreur (Serveur $\rightarrow$ Agent)

Pour chaque trame reçue, le serveur renvoie un objet JSON terminé par `\n` indiquant l'état du traitement via la clé `"status"`.

### 4.1. Réponses de succès (`"status": "ok"`)

* **Après authentification réussie :**
  ```json
  {"status": "ok", "msg": "Authentifie"}
  ```
* **Après réception et insertion des métriques en base de données :**
  ```json
  {"status": "ok", "msg": "Metriques enregistrees"}
  ```

### 4.2. Réponses d'erreur (`"status": "error"`)

En cas d'anomalie, le serveur inclut un code numérique (`"code"`) inspiré des standards HTTP ainsi qu'un message explicite (`"msg"`).

| Code | Signification | Cause fréquente | Exemple de réponse serveur |
| :---: | :--- | :--- | :--- |
| **`400`** | Requête invalide | JSON mal formé, clé manquante, valeur de type incompatible ou clé `"type"` inconnue. | `{"status": "error", "code": 400, "msg": "Type de message inconnu"}` |
| **`401`** | Non autorisé | Envoi de métriques sans authentification préalable, `agent_name` inconnu ou `secret` invalide. | `{"status": "error", "code": 401, "msg": "Authentification requise"}` |
| **`500`** | Erreur interne serveur | Échec lors de l'écriture dans la base de données PostgreSQL. | `{"status": "error", "code": 500, "msg": "Erreur base de donnees"}` |