# Budget Bo 💰

Application de suivi des dépenses bancaires avec :
- synchronisation de comptes (Woob / Crédit Agricole),
- enrichissement IA (Gemini + fallback heuristique),
- détection des dépenses récurrentes,
- interface Next.js moderne.

## Stack actuelle

- **Backend**: Django 5 + Django REST Framework
- **Queue**: Django RQ + Redis
- **DB**: PostgreSQL
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- **Auth**: Google OAuth (django-allauth) + session cookies

## Fonctionnalités principales

- Auth Google (`/auth/login`, `/auth/me`, `/auth/logout`) et login de test en dev (`/authtest-login`).
- Gestion des credentials bancaires chiffrés côté backend.
- Synchronisation asynchrone des transactions via jobs RQ.
- Enrichissement des transactions (libellé nettoyé, marchand, catégorie, confiance).
- Corrections utilisateur apprenantes via règles d'enrichissement.
- Détection des dépenses récurrentes + projection des échéances.
- Dashboard global (solde, dépenses/revenus, catégories, transactions récentes).

## Démarrage local

### 1) Prérequis

- Docker + Docker Compose
- Node.js 20+ (pour le frontend en mode dev natif)

### 2) Lancer backend + infra

```bash
docker compose up -d postgres redis backend rq-worker
```

### 3) Appliquer les migrations Django

```bash
docker compose exec backend python manage.py migrate
```

### 4) Lancer le frontend

```bash
cd frontend
npm install
npm run dev
```

Application: `http://localhost:3000`.

API backend: `http://localhost:8000`.

## Variables d'environnement importantes

Backend:
- `SECRET_KEY`
- `ENCRYPTION_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `FRONTEND_URL`
- `GEMINI_API_KEY` (+ `GEMINI_MODEL`, limites)

Frontend:
- `NEXT_PUBLIC_API_URL` (par défaut `/api` via middleware/proxy)

## Endpoints API (résumé)

### Auth
- `GET /auth/login`
- `GET /auth/callback`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /authtest-login`
- `GET /users/me`

### Credentials & comptes
- `GET /credentials`
- `POST /credentials`
- `GET /credentials/{credential_id}`
- `DELETE /credentials/{credential_id}`
- `POST /credentials/{credential_id}/sync`
- `GET /accounts`
- `GET /accounts/summary`
- `GET /accounts/{account_id}`

### Transactions
- `GET /transactions`
- `GET /transactions/summary`
- `GET /transactions/{transaction_id}`
- `DELETE /transactions/{transaction_id}`
- `PATCH /transactions/{transaction_id}/category`
- `PATCH /transactions/{transaction_id}/correction`
- `PATCH /transactions/{transaction_id}/recurring`
- `POST /transactionsenrich` (bulk enqueue)
- `POST /transactions/{transaction_id}/enrich`

### Récurrence
- `GET /recurring`
- `GET /recurring/upcoming`
- `POST /recurring/detect`
- `GET /recurring/stats/summary`
- `DELETE /recurring/{recurring_id}`

### Santé
- `GET /health`
- `GET /live`
- `GET /ready`

## Commandes utiles

```bash
# Logs backend
docker compose logs -f backend

# Logs worker
docker compose logs -f rq-worker

# Shell Django
docker compose exec backend python manage.py shell

# Exécuter les tests backend
docker compose exec backend python manage.py test
```

## Documentation détaillée

- OAuth: `docs/GUIDE_GOOGLE_OAUTH.md`
- IA / enrichissement: `docs/AI_CLASSIFICATION.md`
- Migrations: `docs/MIGRATIONS.md`
- Plan produit: `docs/ROADMAP.md`
