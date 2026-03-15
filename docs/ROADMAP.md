# Roadmap Budget Bo

## ✅ Livré

### Plateforme
- Backend Django + DRF en production.
- Frontend Next.js 14 (App Router) connecté à l'API réelle.
- Infra Docker Compose (dev) + compose production.

### Fonctionnel
- Auth Google OAuth + session.
- Gestion des credentials bancaires chiffrés.
- Synchronisation asynchrone (RQ) des transactions.
- Enrichissement IA (catégorie, marchand, confiance) + corrections apprenantes.
- Détection de récurrence + page dédiée.
- Dashboard global avec KPIs, catégories et transactions récentes.

## 🚧 En cours / court terme

- Stabilisation API (uniformisation des routes historiques sans slash).
- Amélioration observabilité jobs (logs métier, métriques par queue).
- Renforcement tests backend (endpoints transactions/credentials/recurring).
- Pagination/filtrage enrichis sur les écrans volumineux.

## 🔜 Prochaines évolutions

- Budgets mensuels par catégorie.
- Notifications (récurrences à venir, dépassements budget).
- Export CSV/PDF.
- Multi-banques étendu au-delà de Crédit Agricole.
- Durcissement sécurité prod (headers CSP/HSTS, audit auth/sync).
