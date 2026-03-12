# ClimBetter

Plateforme de suivi et analyse de performances d'escalade.

## Architecture

```
climbetter/
├── .github/workflows/deploy.yml    # CI/CD GitHub Actions
├── infra/
│   ├── docker-compose.yml          # Stack complète (Traefik, TimescaleDB, Redis, Keycloak)
│   ├── traefik/
│   │   └── traefik.yml             # Configuration statique Traefik
│   ├── initdb/
│   │   └── init-databases.sql      # Création des bases PostgreSQL
│   └── .env.example                # Template des variables d'environnement
├── backend/                        # API backend (à venir)
├── mobile/                         # Application mobile (à venir)
└── README.md
```

## Infrastructure

| Service     | Image                                  | Rôle                          |
|-------------|----------------------------------------|-------------------------------|
| Traefik v3  | traefik:v3.1                           | Reverse proxy, SSL automatique|
| TimescaleDB | timescale/timescaledb:latest-pg16      | Base de données (time-series) |
| Redis 7     | redis:7-alpine                         | Cache et sessions             |
| Keycloak 24 | quay.io/keycloak/keycloak:24.0         | IAM / Authentification        |

## Deploiement

Le CI/CD est geré via GitHub Actions. Tout push sur `main` déclenche un déploiement automatique sur le serveur Hetzner.

### Pré-requis serveur

1. Docker + Docker Compose installés
2. Traefik configuré avec le réseau `climbetter`
3. Fichier `.env` créé dans `/opt/climbetter/infra/.env`

### Secrets GitHub requis

| Secret            | Description                      |
|-------------------|----------------------------------|
| `SSH_PRIVATE_KEY` | Clé SSH pour accès au serveur    |

## Sécurité

- Aucun port base de données exposé sur l'hôte
- Secrets uniquement dans `.env` sur le serveur (jamais committés)
- SSL/TLS automatique via Let's Encrypt
- Zero service cloud managé — 100% auto-hébergé
