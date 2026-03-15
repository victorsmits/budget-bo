# Guide : Migrations de Base de Données avec Alembic

Comment créer et appliquer des migrations SQLModel/Alembic dans Budget Bo.

---

## 📌 Migration: suppression du legacy FastAPI (2026-03)

La migration vers Django étant finalisée, les modules FastAPI historiques suivants ont été supprimés :

- `backend/services/recurring.py`
- `backend/domain/recurrence.py`
- `backend/services/enrichment_memory.py`

Impacts :
- Les imports runtime vers ces modules ne sont plus valides.
- La détection de récurrence et l'enrichissement sont désormais gérés via les apps/services Django actifs (`backend/apps/*` et `backend/services/*` restants).
- Le plan de migration applicatif reste disponible via `backend/apps/jobs/management/commands/migrate_from_fastapi.py`.

---

## 🚀 Démarrage Rapide

### 1. Créer une migration (après modification des modèles)

```bash
cd /home/victor-smits/workspace/budget-bo/backend

# Générer automatiquement une migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Exemple concret
docker compose exec backend alembic revision --autogenerate -m "add budget table"
```

### 2. Appliquer les migrations

```bash
# Monter la DB au dernier niveau
docker compose exec backend alembic upgrade head

# Ou niveau spécifique
docker compose exec backend alembic upgrade +1
docker compose exec backend alembic downgrade -1
```

### 3. Voir l'état des migrations

```bash
# Historique
docker compose exec backend alembic history --verbose

# Version actuelle
docker compose exec backend alembic current

# Statut des fichiers
docker compose exec backend alembic show head
```

---

## 📋 Commandes Complètes

### Création

```bash
# Auto-générée (détecte changements dans models.py)
docker compose exec backend alembic revision --autogenerate -m "add user preferences"

# Manuelle (vide, tu écris SQL toi-même)
docker compose exec backend alembic revision -m "custom migration"
```

### Migration

```bash
# Upgrade
alembic upgrade head          # Dernier niveau
alembic upgrade +1            # Un niveau au-dessus
alembic upgrade <revision_id> # Version spécifique

# Downgrade
alembic downgrade -1          # Un niveau en-dessous
alembic downgrade <revision_id>
alembic downgrade base        # Reset complet
```

### Informations

```bash
alembic current               # Version actuelle
alembic history               # Toutes les migrations
alembic history -r head:base  # Ordre inverse
alembic show <revision_id>   # Détails d'une migration
```

---

## 🔄 Workflow Type

### Scénario 1 : Ajouter un nouveau champ

```python
# 1. Modifier app/models/models.py
class User(SQLModel, table=True):
    # ... champs existants ...
    phone_number: Optional[str] = None  # ⬅️ Nouveau
```

```bash
# 2. Créer la migration
docker compose exec backend alembic revision --autogenerate -m "add phone_number to users"

# 3. Vérifier le fichier généré
cat alembic/versions/20240306_1430-abc123_add_phone_number_to_users.py

# 4. Appliquer
docker compose exec backend alembic upgrade head
```

### Scénario 2 : Nouveau modèle

```python
# 1. Créer le modèle dans app/models/models.py
class Budget(SQLModel, table=True):
    __tablename__ = "budgets"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    category: TransactionCategory
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2)))
    month: date
```

```bash
# 2. Migration
docker compose exec backend alembic revision --autogenerate -m "create budgets table"
docker compose exec backend alembic upgrade head
```

### Scénario 3 : Downgrade en cas d'erreur

```bash
# Si une migration casse tout :
docker compose exec backend alembic downgrade -1

# Corriger le modèle, regénérer
docker compose exec backend alembic revision --autogenerate -m "fix broken migration"
docker compose exec backend alembic upgrade head
```

---

## 🐳 En Local (sans Docker)

Si tu veux exécuter Alembic en local (pas dans le container) :

```bash
cd backend

# Activer l'environnement
source .venv/bin/activate

# Installer alembic
poetry add alembic

# Configurer DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://budgetbo:budgetbo_secret@localhost:5432/budgetbo"

# Exécuter
poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "description"
```

---

## 🆘 Dépannage

### "Can't locate revision identified by 'xxx'"

```bash
# La DB est plus avancée que les fichiers
# Option 1 : Reset complet
docker compose down -v
docker compose up -d postgres

# Option 2 : Marquer comme à jour
docker compose exec backend alembic stamp head
```

### "Target database is not up to date"

```bash
# Migrations en attente
alembic upgrade head
```

### Autogenerate ne détecte pas les changements

```bash
# Vérifier que SQLModel.metadata est bien importé dans env.py
# Vérifier que les modèles sont importés dans env.py
```

### Conflit de révisions

```bash
# Voir l'historique
alembic history

# Downgrade jusqu'au point de divergence
alembic downgrade <revision_avant_conflit>

# Supprimer le fichier de migration en conflit
rm alembic/versions/xxx_conflit.py

# Regénérer
alembic revision --autogenerate -m "migration propre"
```

---

## 📝 Bonnes Pratiques

1. **Toujours vérifier la migration générée** avant de l'appliquer
2. **Teste en local** avant de pousser en production
3. **Messages clairs** : "add phone_number to users" pas "update"
4. **Une migration = une feature** (pas 10 changements en une fois)
5. **Ne jamais modifier** une migration déjà poussée en prod
6. **Backup la DB** avant une migration en production

---

## 📁 Structure des Fichiers

```
backend/
├── alembic.ini              # Configuration
├── alembic/
│   ├── env.py               # Setup SQLModel
│   ├── script.py.mako       # Template migration
│   └── versions/            # Fichiers de migration
│       ├── 20240306_1200-abc123_initial.py
│       └── 20240306_1430-def456_add_phone.py
```

---

## 🎯 Récapitulatif

| Action | Commande |
|--------|----------|
| **Créer** migration | `alembic revision --autogenerate -m "desc"` |
| **Appliquer** | `alembic upgrade head` |
| **Annuler** | `alembic downgrade -1` |
| **État** | `alembic current` |
| **Historique** | `alembic history` |

**Prochaine étape** : Après avoir modifié tes modèles, exécute :
```bash
docker compose exec backend alembic revision --autogenerate -m "description"
```
