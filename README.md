# Budget Bo 💰

**SaaS Spending Tracker** - Application intelligente de suivi des dépenses avec synchronisation bancaire, IA locale et détection automatique des dépenses récurrentes.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryproject.org/)
[![Ollama](https://img.shields.io/badge/Ollama-000000?style=flat&logo=ollama&logoColor=white)](https://ollama.com/)

---

## 📑 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation rapide](#-installation-rapide)
- [Configuration](#-configuration)
- [Démarrage](#-démarrage)
- [API Endpoints](#-api-endpoints)
- [Services](#-services)
- [Structure du projet](#-structure-du-projet)
- [Développement](#-développement)
- [Dépannage](#-dépannage)

---

## ✨ Fonctionnalités

### 🔗 Synchronisation Bancaire
- **Woob Integration** : Connexion directe aux banques françaises (Crédit Agricole, etc.)
- **Cryptage AES-256** : Tous les identifiants bancaires sont chiffrés
- **Déduplication intelligente** : Pas de doublons de transactions
- **Retry automatique** : Gestion des timeouts bancaires

### 🤖 Intelligence Artificielle (Ollama)
- **Normalisation des libellés** : `PRLVM SEPA NETFLIX.COM` → `Netflix`
- **Catégorisation automatique** : `subscriptions`, `food`, `transportation`...
- **Extraction des marchands** : Identification automatique
- **Local & Privacy-first** : Aucune donnée ne quitte ton serveur

### 🔄 Détection des Dépenses Récurrentes
- **Analyse de pattern** : Fréquence mensuelle/annuelle
- **Similarité Levenshtein** : Détection des transactions similaires
- **Stabilité des montants** : Tolérance ±5%
- **Prévisions** : Alertes sur les prochains paiements

### 🔐 Authentification Sécurisée
- **Google OAuth2** : Connexion via Google
- **Sessions HttpOnly** : Cookies sécurisés
- **JWT optionnel** : Prêt pour l'échelle

---

## 🏗️ Architecture

```mermaid
graph TB
    User[👤 Utilisateur] -->|HTTP| Frontend[🌐 Frontend<br/>Next.js 3000]
    Frontend -->|API| Backend[⚡ Backend<br/>FastAPI 8000]
    Backend -->|SQL| Postgres[(🐘 PostgreSQL<br/>5432)]
    Backend -->|Cache| Redis[(🔴 Redis<br/>6379)]
    Backend -->|Tasks| Celery[🥬 Celery Worker]
    Celery -->|AI| Ollama[🦙 Ollama<br/>11434]
    Celery -->|Bank| Woob[🏦 Woob<br/>Bank Sync]
    
    subgraph Monitoring
        Flower[🌸 Flower<br/>5555]
    end
    
    Celery -.->|Monitoring| Flower
```

### Stack Technique

| Couche | Technologie | Description |
|--------|-------------|-------------|
| **Backend** | FastAPI + Python 3.12 | API REST async |
| **ORM** | SQLModel | SQLAlchemy + Pydantic |
| **Database** | PostgreSQL 15+ | Données persistantes |
| **Cache** | Redis 7+ | Sessions + Celery broker |
| **Queue** | Celery + Redis | Background tasks |
| **AI** | Ollama + Phi3 | Local LLM inference |
| **Bank** | Woob | Web scraping bancaire |
| **Auth** | Google OAuth2 | Authentification |
| **DevOps** | Docker Compose | Orchestration |

---

## 📋 Prérequis

### Minimum
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4 GB RAM
- 10 GB espace disque

### Recommandé
- Docker Engine 24.0+
- 8 GB RAM (pour Ollama)
- CPU multi-cœur

### Optionnel
- GPU NVIDIA (pour accélération Ollama)
- Make (pour commandes simplifiées)

---

## 🚀 Installation rapide

### 1. Cloner le repository

```bash
git clone https://github.com/victorsmits/budget-bo.git
cd budget-bo
```

### 2. Configuration environnement

```bash
# Copier le template
cp .env.example .env

# Éditer avec tes valeurs
nano .env
```

### 3. Lancer l'application

```bash
docker compose up -d
```

### 4. Vérifier l'installation

```bash
# Health check
curl http://localhost:8000/health

# Documentation API
open http://localhost:8000/docs
```

---

## ⚙️ Configuration

### Variables d'environnement

Crée un fichier `.env` à la racine :

```env
# ============================================
# Budget Bo - Configuration
# ============================================

# --------------------------------------------
# Google OAuth (OBLIGATOIRE pour auth Google)
# --------------------------------------------
# 1. Va sur https://console.cloud.google.com/apis/credentials
# 2. Crée un projet → Active "Google+ API"
# 3. Crée "OAuth client ID" → Type "Web application"
# 4. Ajoute redirect URI: http://localhost:8000/auth/callback
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret

# --------------------------------------------
# Sécurité (CHANGE EN PRODUCTION!)
# --------------------------------------------
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# --------------------------------------------
# Base de données (défaut = Docker)
# --------------------------------------------
POSTGRES_USER=budgetbo
POSTGRES_PASSWORD=budgetbo_secret
POSTGRES_DB=budgetbo
DATABASE_URL=postgresql+asyncpg://budgetbo:budgetbo_secret@postgres:5432/budgetbo

# --------------------------------------------
# Redis & Celery
# --------------------------------------------
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# --------------------------------------------
# Ollama (IA locale)
# --------------------------------------------
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=phi3
OLLAMA_TIMEOUT=120

# --------------------------------------------
# Application
# --------------------------------------------
ENVIRONMENT=development
DEBUG=true
FRONTEND_URL=http://localhost:3000
```

### Configuration Google OAuth

Voir le guide détaillé : [`docs/GUIDE_GOOGLE_OAUTH.md`](docs/GUIDE_GOOGLE_OAUTH.md)

**Résumé rapide :**

1. **Google Cloud Console** → APIs & Services → Credentials
2. **Create Credentials** → OAuth client ID → Web application
3. **Authorized redirect URIs** : `http://localhost:8000/auth/callback`
4. **Copier Client ID + Secret** dans `.env`

---

## 🎬 Démarrage

### Mode développement (hot-reload)

```bash
docker compose up -d

# Voir les logs
docker compose logs -f backend

# Arrêter
docker compose down
```

### Mode production

```bash
# Modifier .env
ENVIRONMENT=production
DEBUG=false

# Relancer
docker compose up -d
```

### Accès aux services

| Service | URL | Description |
|---------|-----|-------------|
| **API** | http://localhost:8000 | Backend FastAPI |
| **Docs** | http://localhost:8000/docs | Swagger UI |
| **ReDoc** | http://localhost:8000/redoc | Documentation alternative |
| **Flower** | http://localhost:5555 | Monitoring Celery |
| **PostgreSQL** | localhost:5432 | Database |
| **Redis** | localhost:6379 | Cache |

---

## 🔌 API Endpoints

### Authentification

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/auth/login` | Redirection Google OAuth |
| `GET` | `/auth/callback` | Callback OAuth (Google → redirect) |
| `POST` | `/auth/logout` | Déconnexion |
| `GET` | `/auth/me` | Infos utilisateur connecté |
| `POST` | `/auth/test-login` | ⚠️ Dev only - Bypass OAuth |

**Exemples :**

```bash
# Login via Google (navigateur)
curl http://localhost:8000/auth/login

# Vérifier connexion
curl http://localhost:8000/auth/me \
  --cookie "session=xxx"

# Dev login (sans Google)
curl -X POST http://localhost:8000/auth/test-login \
  -c cookies.txt
```

### Credentials Bancaires

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/credentials` | Lister mes credentials |
| `POST` | `/credentials` | Ajouter un compte bancaire |
| `GET` | `/credentials/{id}` | Détails d'un credential |
| `DELETE` | `/credentials/{id}` | Désactiver un credential |
| `POST` | `/credentials/{id}/sync` | **Lancer sync manuel** |

**Exemples :**

```bash
# Liste des comptes
curl http://localhost:8000/credentials \
  --cookie "session=xxx"

# Ajouter Crédit Agricole
curl -X POST http://localhost:8000/credentials \
  --cookie "session=xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_name": "cragr",
    "bank_label": "Crédit Agricole",
    "login": "mon_login",
    "password": "mon_pass"
  }'

# Sync manuel
curl -X POST http://localhost:8000/credentials/{id}/sync \
  --cookie "session=xxx"
```

### Transactions

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/transactions` | Lister (avec filtres) |
| `GET` | `/transactions/summary` | Statistiques |
| `GET` | `/transactions/{id}` | Détail transaction |
| `PATCH` | `/transactions/{id}/category` | Modifier catégorie |
| `PATCH` | `/transactions/{id}/recurring` | Marquer récurrente |
| `DELETE` | `/transactions/{id}` | Supprimer |

**Query Parameters :**

```bash
# Filtres disponibles
?category=food           # Filtrer par catégorie
?is_expense=true         # Dépenses uniquement
?is_recurring=true       # Récurrentes uniquement
?start_date=2024-01-01   # Date début
?end_date=2024-12-31     # Date fin
?skip=0&limit=100        # Pagination
```

**Exemples :**

```bash
# Dernières transactions
curl "http://localhost:8000/transactions?limit=20" \
  --cookie "session=xxx"

# Dépenses nourriture mars 2024
curl "http://localhost:8000/transactions?category=food&start_date=2024-03-01&end_date=2024-03-31" \
  --cookie "session=xxx"

# Stats mensuelles
curl "http://localhost:8000/transactions/summary" \
  --cookie "session=xxx"
```

### Dépenses Récurrentes

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/recurring` | Lister patterns détectés |
| `GET` | `/recurring/upcoming` | Prochains paiements attendus |
| `GET` | `/recurring/{id}` | Détails |
| `POST` | `/recurring/detect` | **Lancer détection IA** |
| `DELETE` | `/recurring/{id}` | Désactiver |
| `GET` | `/recurring/stats/summary` | Stats récurrentes |

**Exemples :**

```bash
# Détecter automatiquement
curl -X POST "http://localhost:8000/recurring/detect?months_back=6" \
  --cookie "session=xxx"

# Prochains paiements
curl "http://localhost:8000/recurring/upcoming?days_ahead=30" \
  --cookie "session=xxx"
```

### Santé

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | État complet des services |
| `GET` | `/live` | Liveness probe (Kubernetes) |
| `GET` | `/ready` | Readiness probe (Kubernetes) |

---

## 🛠️ Services

### Backend (FastAPI)

- **Port** : 8000
- **Hot-reload** : Activé en dev
- **Docs auto** : Swagger + ReDoc

### PostgreSQL

- **Port** : 5432
- **User** : budgetbo
- **Database** : budgetbo
- **Persistence** : Volume Docker

### Redis

- **Port** : 6379
- **Utilisation** : Sessions + Celery broker + Cache
- **Persistence** : AOF activé

### Ollama (IA)

- **Port** : 11434
- **Modèle** : phi3 (par défaut)
- **GPU** : Optionnel (CPU fonctionne)

**Télécharger un modèle :**

```bash
docker compose exec ollama ollama pull phi3
docker compose exec ollama ollama pull llama3:8b  # Alternative
```

### Celery Worker

- **Traite** : Sync bancaire, enrichissement IA
- **Retries** : 3 tentatives avec backoff
- **Monitoring** : Flower sur port 5555

### Flower (Monitoring)

- **Port** : 5555
- **Visualise** : Tasks, workers, queues
- **Actions** : Retry, revoke, inspect

---

## 📁 Structure du projet

```
budget-bo/
├── 📁 backend/                 # Application FastAPI
│   ├── 📁 app/
│   │   ├── 📁 api/            # Endpoints REST
│   │   │   ├── auth.py       # OAuth & sessions
│   │   │   ├── credentials.py # Gestion banques
│   │   │   ├── health.py     # Health checks
│   │   │   ├── recurring.py  # Dépenses récurrentes
│   │   │   └── transactions.py # CRUD transactions
│   │   ├── 📁 core/          # Configuration
│   │   │   ├── config.py     # Settings Pydantic
│   │   │   ├── database.py   # SQLModel setup
│   │   │   └── security.py   # Chiffrement AES-256
│   │   ├── 📁 domain/        # Logique métier
│   │   │   └── recurrence.py # Détection patterns
│   │   ├── 📁 models/        # SQLModel models
│   │   │   └── models.py     # User, Transaction, etc.
│   │   ├── 📁 services/      # Services métier
│   │   │   ├── ollama.py     # Client IA local
│   │   │   └── recurring.py  # Service récurrentes
│   │   └── main.py           # Point d'entrée FastAPI
│   ├── 📁 worker/            # Celery workers
│   │   ├── celery_app.py     # Configuration Celery
│   │   └── 📁 tasks/
│   │       └── sync_tasks.py # Sync bancaire + IA
│   ├── 📁 scripts/           # Utilitaires
│   │   ├── console.py        # Console IPython debug
│   │   └── seed.py           # Données de test
│   ├── Dockerfile            # Image backend
│   └── pyproject.toml        # Dépendances Poetry
├── 📁 docs/                    # Documentation
│   └── GUIDE_GOOGLE_OAUTH.md
├── .env.example              # Template configuration
├── .env                      # ⚠️ NON TRACKÉ (gitignore)
├── docker-compose.yml        # Orchestration complète
├── LICENSE
└── README.md                 # Ce fichier
```

---

## 💻 Développement

### Console de debug

```bash
# Rails-style console avec modèles pré-chargés
docker compose exec backend python scripts/console.py

>>> user = await session.execute(select(User))
>>> await Transaction.count()
```

### Tests

```bash
# Lancer les tests
docker compose exec backend pytest

# Avec coverage
docker compose exec backend pytest --cov=app
```

### Lint & Format

```bash
# Backend
docker compose exec backend ruff check .
docker compose exec backend ruff format .
docker compose exec backend mypy .
```

### Database migrations

```bash
# Créer une migration
docker compose exec backend alembic revision --autogenerate -m "add table"

# Appliquer
docker compose exec backend alembic upgrade head
```

---

## 🔧 Dépannage

### "redirect_uri_mismatch" sur Google OAuth

**Cause** : L'URI dans Google Cloud ≠ l'URI utilisée par l'app

**Solution** :
1. Va sur https://console.cloud.google.com/apis/credentials
2. Trouve ton OAuth client → Edit
3. **Authorized redirect URIs** : Ajoute `http://localhost:8000/auth/callback`
4. Sauvegarde et réessaie

### Worker ne démarre pas

```bash
# Voir les logs
docker compose logs worker

# Redémarrer
docker compose restart worker
```

### Ollama modèle non trouvé

```bash
# Télécharger le modèle
docker compose exec ollama ollama pull phi3

# Vérifier
docker compose exec ollama ollama list
```

### Erreur de connexion PostgreSQL

```bash
# Vérifier que postgres est healthy
docker compose ps

# Reset database (⚠️ perd les données)
docker compose down -v
docker compose up -d postgres
```

### Sync bancaire échoue

- Vérifie tes credentials (login/pass)
- La banque peut bloquer les connexions automatisées
- Utilise le mode **mock** pour tester sans compte réel

---

## 🚀 Roadmap

- [ ] Frontend Next.js avec Tremor.so
- [ ] Notifications email (dépenses récurrentes à venir)
- [ ] Export CSV/PDF des rapports
- [ ] Support multi-banques (BNP, Société Générale...)
- [ ] Mode hors-ligne (PWA)
- [ ] Analyses prédictives avancées

---

## 🤝 Contribution

1. Fork le projet
2. Crée une branche (`git checkout -b feature/AmazingFeature`)
3. Commit tes changements (`git commit -m 'Add some feature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvre une Pull Request

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web moderne
- [SQLModel](https://sqlmodel.tiangolo.com/) - ORM intuitif
- [Ollama](https://ollama.com/) - IA locale accessible
- [Woob](https://woob.tech/) - Web Outside of Browsers
- [Tremor.so](https://www.tremor.so/) - Composants React pour dashboards

---

<p align="center">
  Fait avec ❤️ par <a href="https://github.com/victorsmits">@victorsmits</a>
</p>
