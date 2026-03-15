# Migrations base de données (Django)

Ce projet n'utilise plus Alembic/SQLModel. Les migrations passent par le système natif Django.

## Workflow standard

```bash
# 1) Générer les migrations à partir des changements de models.py
docker compose exec backend python manage.py makemigrations

# 2) Appliquer
docker compose exec backend python manage.py migrate

# 3) Vérifier l'état
docker compose exec backend python manage.py showmigrations
```

## Commandes utiles

```bash
# Créer une migration pour une app spécifique
docker compose exec backend python manage.py makemigrations transactions

# Voir le SQL d'une migration
docker compose exec backend python manage.py sqlmigrate transactions 0002

# Revenir à une migration cible
docker compose exec backend python manage.py migrate transactions 0001
```

## Bonnes pratiques

- Toujours versionner les fichiers dans `backend/apps/*/migrations/`.
- Relire les migrations générées avant commit.
- Éviter de modifier une migration déjà déployée.
- Préférer une migration par changement logique (lisibilité rollback/audit).

## Migration historique FastAPI → Django

La migration applicative historique est finalisée. Le script de support existe toujours:

```bash
docker compose exec backend python manage.py migrate_from_fastapi
```

Commande de nettoyage utile si besoin:

```bash
docker compose exec backend python manage.py cleanup_unused_tables
```
