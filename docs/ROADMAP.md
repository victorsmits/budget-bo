# Roadmap Complète - Budget Bo SaaS

Roadmap exhaustive du projet SaaS Spending Tracker, basée sur l'objectif initial et l'état actuel du développement.

---

## 🎯 Objectif Initial du Projet

**Budget Bo** : Application SaaS de suivi des dépenses avec :
- Synchronisation bancaire automatique (Woob)
- Intelligence artificielle locale (Ollama) pour enrichissement
- Détection automatique des dépenses récurrentes
- Architecture moderne : FastAPI + PostgreSQL + Redis + Celery
- Frontend Next.js (à venir)

---

## ✅ PHASE 1 : Fondations (COMPLÉTÉE)

### Infrastructure & Setup
| Tâche | Description | Statut |
|-------|-------------|--------|
| **Docker Compose** | Orchestration complète (7 services) | ✅ |
| **PostgreSQL** | Database avec SQLModel ORM | ✅ |
| **Redis** | Cache + Celery broker | ✅ |
| **Encryption Service** | AES-256 (Fernet) pour credentials | ✅ |
| **Health Checks** | Endpoints `/health`, `/live`, `/ready` | ✅ |

### Modèles de Données (SQLModel)
| Modèle | Relations | Statut |
|--------|-----------|--------|
| **User** | credentials, transactions, recurring | ✅ |
| **BankCredential** | Chiffré AES-256, sync_status | ✅ |
| **Transaction** | dedup_key, ai_confidence, enriched_at | ✅ |
| **RecurringExpense** | pattern detection, next_expected_date | ✅ |

### Domain Logic
| Tâche | Fichier | Statut |
|-------|---------|--------|
| **Recurrence Detector** | Logique récurrente intégrée côté Django `apps/recurring` | ✅ |
| **Transaction Patterns** | Détection fréquence, amount stability | ✅ |

---

## ✅ PHASE 2 : Services Core (COMPLÉTÉE)

### Intégrations Externes
| Service | Implémentation | Statut |
|---------|----------------|--------|
| **Ollama IA** | `services/ollama.py` - normalize_label(), categorize() | ✅ |
| **Woob Banking** | `worker/tasks/sync_tasks.py` - cragr + mock fallback | ✅ |
| **Celery Workers** | 3 tasks avec retry logic | ✅ |
| **Recurring Service** | Service legacy FastAPI supprimé (migration Django terminée) | ✅ |

### Celery Tasks
| Task | Description | Retry | Statut |
|------|-------------|-------|--------|
| `sync_user_transactions` | Sync bancaire via Woob | 3x backoff | ✅ |
| `enrich_new_transactions` | Enrichissement IA post-sync | 2x | ✅ |
| `sync_all_users_transactions` | Job quotidien 2h00 | - | ✅ |

---

## ✅ PHASE 3 : API Backend (COMPLÉTÉE)

### Authentification
| Endpoint | Méthode | Description | Statut |
|----------|---------|-------------|--------|
| `/auth/login` | GET | Google OAuth redirect | ✅ |
| `/auth/callback` | GET | OAuth callback + session | ✅ |
| `/auth/logout` | POST | Déconnexion | ✅ |
| `/auth/me` | GET | User connecté | ✅ |
| `/auth/test-login` | POST | Dev bypass | ✅ |

### Bank Credentials
| Endpoint | Méthode | Description | Statut |
|----------|---------|-------------|--------|
| `/credentials` | GET | Liste credentials | ✅ |
| `/credentials` | POST | Créer credential (chiffré) | ✅ |
| `/credentials/{id}` | GET | Détails | ✅ |
| `/credentials/{id}` | DELETE | Désactiver | ✅ |
| `/credentials/{id}/sync` | POST | 🔄 Sync manuel | ✅ |

### Transactions
| Endpoint | Méthode | Description | Statut |
|----------|---------|-------------|--------|
| `/transactions` | GET | Liste + filtres | ✅ |
| `/transactions/summary` | GET | Stats globales | ✅ |
| `/transactions/{id}` | GET | Détail | ✅ |
| `/transactions/{id}/category` | PATCH | Modifier catégorie | ✅ |
| `/transactions/{id}/recurring` | PATCH | Marquer récurrente | ✅ |
| `/transactions/{id}` | DELETE | Supprimer | ✅ |

### Recurring Expenses
| Endpoint | Méthode | Description | Statut |
|----------|---------|-------------|--------|
| `/recurring` | GET | Lister patterns | ✅ |
| `/recurring/upcoming` | GET | Prochains paiements | ✅ |
| `/recurring/detect` | POST | 🤖 Détection IA | ✅ |
| `/recurring/stats/summary` | GET | Stats récurrentes | ✅ |
| `/recurring/{id}` | DELETE | Désactiver | ✅ |

### Outils
| Outil | Fichier | Statut |
|-------|---------|--------|
| **Console IPython** | `scripts/console.py` | ✅ |
| **Seed Data** | `scripts/seed.py` | ✅ |
| **README** | Documentation complète | ✅ |
| **Guide OAuth** | `docs/GUIDE_GOOGLE_OAUTH.md` | ✅ |

---

## 🚧 PHASE 4 : Robustesse API (EN COURS)

### API Hardening (Priorité Haute)
| Tâche | Description | Estimation |
|-------|-------------|------------|
| **Rate Limiting** | slowapi + Redis - limiter sync/credentials | 0.5 jour |
| **Pagination Standardisée** | Format uniforme {items, total, page, pages} | 0.5 jour |
| **User Profile API** | `/users/me`, stats, suppression RGPD | 1 jour |
| **Validation Avancée** | Date cohérence, string lengths | 0.5 jour |

**Sous-total** : 2.5 jours

---

## 🔮 PHASE 5 : Features Avancées Backend (À VENIR)

### Budgets API
| Endpoint | Description | Estimation |
|----------|-------------|------------|
| `GET /budgets` | Lister budgets mensuels | 0.5j |
| `POST /budgets` | Créer budget catégorie | 0.5j |
| `GET /budgets/{id}/status` | % consommé | 0.5j |
| `GET /budgets/overview` | Vue d'ensemble | 0.5j |

**Sous-total** : 2 jours

### Notifications API
| Tâche | Description | Estimation |
|-------|-------------|------------|
| Modèle `Notification` | Type, message, read_at | 0.5j |
| `GET /notifications` | Lister | 0.5j |
| `GET /notifications/unread-count` | Badge | 0.25j |
| Celery task notifs | Générer alertes (récurrent, budget) | 1j |
| Email integration | SendGrid/AWS SES | 1j |

**Sous-total** : 3 jours

### Batch & Exports
| Tâche | Description | Estimation |
|-------|-------------|------------|
| `POST /transactions/bulk-delete` | Suppression masse | 0.5j |
| `PATCH /transactions/bulk-category` | Changement catégorie masse | 0.5j |
| `GET /transactions/export?format=csv` | Export CSV | 0.5j |
| `GET /transactions/export?format=pdf` | Rapport PDF | 1j |

**Sous-total** : 2.5 jours

---

## 🎨 PHASE 6 : Frontend Next.js (À VENIR)

### Setup
| Tâche | Description | Estimation |
|-------|-------------|------------|
| Next.js 14 + TypeScript | Create app | 0.5j |
| Tailwind CSS | Configuration | 0.25j |
| Tremor.so | Composants dashboard | 0.5j |
| shadcn/ui | Composants UI | 0.25j |
| React Query | Data fetching | 0.5j |

**Sous-total** : 2 jours

### Pages
| Page | Fonctionnalités | Estimation |
|------|-----------------|------------|
| **Login** | Google OAuth, dev test mode | 0.5j |
| **Dashboard** | Graphiques Tremor, stats rapides | 1.5j |
| **Transactions** | Liste filtrable, pagination, édition | 1.5j |
| **Comptes Bancaires** | CRUD credentials, bouton sync | 1j |
| **Récurrentes** | Liste, détection manuelle | 1j |
| **Profil** | Déconnexion, infos user | 0.5j |

**Sous-total** : 6 jours

---

## 🧪 PHASE 7 : Tests & Qualité (À VENIR)

### Tests Backend
| Type | Couverture | Estimation |
|------|------------|------------|
| **Unit tests** | Services, utils | 1.5j |
| **API tests** | Tous endpoints (pytest-asyncio) | 2j |
| **E2E tests** | Playwright - scénario complet | 1.5j |
| **Coverage** | Objectif 80%+ | 0.5j |

**Sous-total** : 5.5 jours

### CI/CD
| Tâche | Description | Estimation |
|-------|-------------|------------|
| GitHub Actions | Lint + tests + build | 1j |
| Pre-commit hooks | ruff, mypy | 0.5j |

**Sous-total** : 1.5 jours

---

## 🚀 PHASE 8 : Production (À VENIR)

### Déploiement
| Tâche | Description | Estimation |
|-------|-------------|------------|
| Dockerfile optimisé | Multi-stage, sécurisé | 0.5j |
| Docker Compose prod | Nginx, SSL | 1j |
| Let's Encrypt | Certificats SSL | 0.5j |
| Cloud provider | Hetzner/AWS/DO | 1j |

**Sous-total** : 3 jours

### Monitoring & Sécurité
| Tâche | Description | Estimation |
|-------|-------------|------------|
| Sentry | Error tracking | 0.5j |
| Prometheus + Grafana | Métriques | 1j |
| Audit logging | Auth + sync logs | 0.5j |
| Security headers | HSTS, CSP | 0.5j |

**Sous-total** : 2.5 jours

---

## 📅 TIMELINE COMPLÈTE

### Récapitulatif par Phase

| Phase | Description | Durée | Cumul |
|-------|-------------|-------|-------|
| **1. Fondations** | Docker, DB, models | ✅ Complété | - |
| **2. Services** | Ollama, Woob, Celery | ✅ Complété | - |
| **3. API Core** | 19 endpoints | ✅ Complété | - |
| **4. Robustesse** | Rate limiting, validation | 2.5j | 2.5j |
| **5. Features** | Budgets, notifs, exports | 7.5j | 10j |
| **6. Frontend** | Next.js + Tremor | 8j | 18j |
| **7. Tests** | Pytest, Playwright, CI/CD | 7j | 25j |
| **8. Production** | Déploiement, monitoring | 5.5j | **30.5j** |

---

## 🎯 VERSIONS & MILESTONES

### MVP (Minimum Viable Product)
**Délai** : Maintenant (déjà fonctionnel)
**Scope** : Phases 1-3 ✅
**Ce qui marche** :
- Auth Google OAuth
- CRUD credentials bancaires
- Sync transactions (Woob/mock)
- Enrichissement IA (Ollama)
- Détection récurrente
- API complète

### Beta (Feature Complete)
**Délai** : +10 jours
**Scope** : Phases 4-5
**Ajouts** :
- Rate limiting
- Budgets
- Notifications email
- Exports
- Frontend complet

### Production v1.0
**Délai** : +30 jours
**Scope** : Phases 6-8
**Ajouts** :
- Tests automatisés
- CI/CD
- Déploiement cloud
- Monitoring
- SSL + sécurité hardening

---

## 📊 PRIORISATION DYNAMIQUE

### Si temps limité (2 semaines)
1. Phase 4 : Robustesse API (2.5j)
2. Phase 6 : Frontend minimal (4j)
3. Phase 7 : Tests critiques (2j)

### Si temps confortable (1 mois)
1. Phases 4-5 : Backend complet (10j)
2. Phase 6 : Frontend riche (8j)
3. Phase 7 : Tests complets (7j)
4. Phase 8 : Production ready (5j)

---

## 🚀 PROCHAINE ACTION RECOMMANDÉE

Basé sur l'état actuel (Phases 1-3 ✅), les options sont :

**Option A : Sécuriser l'API** (2-3 jours)
- Rate limiting
- User profile endpoints
- Validation avancée
→ API production-ready

**Option B : Frontend** (1-2 semaines)
- Next.js setup
- Dashboard Tremor
- Pages essentielles
→ MVP utilisable avec UI

**Option C : Tests** (1 semaine)
- Suite pytest complète
- Coverage 80%
→ Base solide pour évolutions

Quelle direction priorises-tu ?
