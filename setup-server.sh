#!/bin/bash
# =============================================================
# ClimBetter — Setup serveur Hetzner
# Exécuter : ssh root@178.104.37.106 < setup-server.sh
#
# Safe : ne coupe PAS Traefik, ne touche PAS aux volumes existants
# =============================================================
set -euo pipefail

echo "=== 1/5 — Git init dans /opt/climbetter (sans toucher aux fichiers existants) ==="
cd /opt/climbetter

# Initialiser git si pas déjà un repo
if [ ! -d .git ]; then
    git init
    git remote add origin https://github.com/smo-peak/climbetter-demo.git
    # Fetch puis checkout sans écraser les fichiers non-trackés
    git fetch origin master
    git checkout -b master --track origin/master
else
    echo "Git repo déjà initialisé, pull simple"
    git pull origin master
fi

echo "=== 2/5 — Vérification des fichiers récupérés ==="
ls -la infra/docker-compose.yml infra/initdb/init-databases.sh infra/traefik/traefik.yml

echo "=== 3/5 — Génération du .env (si absent) ==="
if [ -f infra/.env ]; then
    echo "ATTENTION : infra/.env existe déjà, on ne l'écrase pas."
    echo "Pour régénérer, supprimez-le d'abord : rm /opt/climbetter/infra/.env"
else
    cat > infra/.env << EOF
# --- TimescaleDB ---
POSTGRES_USER=climbetter
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=climbetter
KEYCLOAK_DB_PASSWORD=$(openssl rand -base64 32)

# --- Redis ---
REDIS_PASSWORD=$(openssl rand -base64 32)

# --- Keycloak ---
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 32)
KC_HOSTNAME=auth.climbetter.com

# --- Traefik ---
ACME_EMAIL=admin@climbetter.com
EOF
    chmod 600 infra/.env
    echo ".env créé avec secrets aléatoires"
fi

echo "=== 4/5 — Démarrage des NOUVEAUX services (Traefik non touché) ==="
# --no-recreate : ne relance PAS Traefik s'il tourne déjà
docker compose -f infra/docker-compose.yml up -d --no-recreate --remove-orphans

echo "=== 5/5 — Vérification ==="
echo ""
echo "--- Containers ---"
docker compose -f infra/docker-compose.yml ps
echo ""
echo "--- Attente healthchecks (30s) ---"
sleep 30
echo ""
echo "--- TimescaleDB ---"
docker compose -f infra/docker-compose.yml exec timescaledb pg_isready -U climbetter && echo "OK" || echo "FAIL"
echo ""
echo "--- Redis ---"
docker compose -f infra/docker-compose.yml exec redis redis-cli -a "$(grep REDIS_PASSWORD infra/.env | cut -d= -f2)" ping && echo "OK" || echo "FAIL"
echo ""
echo "--- Bases PostgreSQL ---"
docker compose -f infra/docker-compose.yml exec timescaledb psql -U climbetter -c "\l" | grep -E "climbetter|keycloak"
echo ""
echo "=== SETUP TERMINÉ ==="
