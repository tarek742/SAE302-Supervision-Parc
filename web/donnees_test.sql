-- Données FICTIVES pour tester l'interface web sans agents ni serveur.
-- À lancer sur une base de développement uniquement (jamais en démo) :
--   psql -U postgres -d supervision -f web/donnees_test.sql
-- Le script peut être relancé : il efface d'abord ses propres agents de test.

DELETE FROM agents WHERE agent_name LIKE 'test-%';

-- secret_hash factice : ces agents ne pourront jamais s'authentifier
INSERT INTO agents (agent_name, secret_hash, hostname, last_seen) VALUES
    ('test-pc-accueil',   'factice', 'PC-ACCUEIL-01', NOW() - INTERVAL '4 seconds'),
    ('test-srv-fichiers', 'factice', 'SRV-FICHIERS',  NOW() - INTERVAL '8 seconds'),
    ('test-pc-compta',    'factice', 'PC-COMPTA-02',  NOW() - INTERVAL '12 minutes'),
    ('test-pc-neuf',      'factice', 'PC-NEUF-03',    NULL);

-- Seuils personnalisés pour le serveur de fichiers (les autres gardent les valeurs par défaut)
INSERT INTO thresholds (agent_id, cpu_crit, ram_crit, disk_crit, offline_after_s)
SELECT id, 80, 90, 85, 60 FROM agents WHERE agent_name = 'test-srv-fichiers';

-- Une heure de mesures toutes les 10 secondes pour chaque agent qui a déjà été vu
INSERT INTO measures (agent_id, ts, cpu_pct, ram_pct, disk_pct, net_sent_bytes, net_recv_bytes)
SELECT
    a.id,
    a.last_seen - (n * INTERVAL '10 seconds'),
    LEAST(100, GREATEST(0, base.cpu  + 15 * sin(n / 20.0) + random() * 8)),
    LEAST(100, GREATEST(0, base.ram  + 5  * sin(n / 50.0) + random() * 3)),
    base.disk + n * 0.001,
    (random() * 50000)::bigint,
    (random() * 200000)::bigint
FROM agents a
JOIN (VALUES
    ('test-pc-accueil',   25.0, 48.0, 61.0),
    ('test-srv-fichiers', 78.0, 83.0, 88.0),
    ('test-pc-compta',    12.0, 35.0, 42.0)
) AS base(nom, cpu, ram, disk) ON base.nom = a.agent_name
CROSS JOIN generate_series(0, 359) AS n;
