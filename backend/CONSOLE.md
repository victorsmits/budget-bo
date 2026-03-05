# Console Interactive Budget Bo

Console IPython pour interagir avec la base de données et tester le backend en temps réel.

## Démarrage

```bash
docker compose exec backend python -m scripts.console
```

## Objets Disponibles

| Nom | Type | Description |
|-----|------|-------------|
| `User` | Model | Modèle utilisateur (SQLModel) |
| `BankCredential` | Model | Credentials bancaires chiffrés |
| `Transaction` | Model | Transactions importées |
| `RecurringExpense` | Model | Dépenses récurrentes détectées |
| `TransactionCategory` | Enum | Catégories: FOOD, HOUSING, etc. |
| `select` | Fonction | SQLAlchemy SELECT |
| `func` | Module | SQLAlchemy func (count, sum, etc.) |
| `settings` | Config | Configuration de l'app |
| `encryption` | Service | Service de chiffrement Fernet |
| `_query()` | Async | Exécuter une requête |
| `_count()` | Async | Compter les enregistrements |
| `AsyncSessionLocal` | Class | Créer une session DB manuellement |
| `asyncio` | Module | Module asyncio |

## Commandes de Base

### Compter les enregistrements

```python
# Compter les utilisateurs
>>> asyncio.run(_count(User))
2

# Compter les transactions
>>> asyncio.run(_count(Transaction))
0

# Compter les credentials
>>> asyncio.run(_count(BankCredential))
2
```

### Requêtes SELECT

```python
# Lister tous les utilisateurs
>>> asyncio.run(_query(select(User)))
[<User 0da68ab3-6454-4728-817a-d3e26417b19f>, <User 58cebff4-dcb8-4e76-9d08-4897263698fc>]

# Lister les credentials avec status
>>> creds = asyncio.run(_query(select(BankCredential)))
>>> for c in creds:
...     print(f"{c.bank_name}: {c.sync_status}")
...
cragr: pending
cragr: pending
```

### Utiliser une session manuellement

```python
# Créer une session
>>> session = asyncio.run(AsyncSessionLocal().__aenter__())

# Exécuter une requête
>>> result = asyncio.run(session.execute(select(User)))
>>> users = result.scalars().all()
>>> users
[<User 0da68ab3-6454-4728-817a-d3e26417b19f>]

# Fermer la session
>>> asyncio.run(session.close())
```

### Décrypter un credential

```python
# Récupérer un credential
>>> creds = asyncio.run(_query(select(BankCredential).where(BankCredential.bank_name == 'cragr')))
>>> cred = creds[0]

# Décrypter le login
>>> encryption.decrypt(cred.encrypted_login)
'test_login'

# Décrypter le password
>>> encryption.decrypt(cred.encrypted_password)
'test_pass'
```

### Vérifier la config

```python
# Voir l'environnement
>>> settings.environment
'development'

# Voir l'URL de la DB
>>> settings.database_url
'postgresql+asyncpg://budgetbo:budgetbo_secret@postgres:5432/budgetbo'

# Vérifier si dev mode
>>> settings.is_development
True
```

### Requêtes complexes

```python
# Transactions par catégorie
>>> from sqlalchemy import func
>>> result = asyncio.run(session.execute(
...     select(Transaction.category, func.count().label('count'))
...     .group_by(Transaction.category)
... ))
>>> result.all()
[(<TransactionCategory.OTHER: 'other'>, 14)]

# Somme des dépenses
>>> result = asyncio.run(session.execute(
...     select(func.sum(Transaction.amount))
...     .where(Transaction.is_expense == True)
... ))
>>> result.scalar()
Decimal('1234.56')
```

## Astuces

### Ré-exécuter la dernière commande
```python
>>> %rerun
```

### Voir l'historique
```python
>>> %history
```

### Quitter
```python
>>> exit()
```

## Dépannage

### "Event loop is closed"
Si tu vois cette erreur, redémarre le container backend :
```bash
docker compose restart backend worker
```

### "Module not found"
Le script doit être exécuté depuis le container :
```bash
# Correct
docker compose exec backend python -m scripts.console

# Incorrect (en dehors du container)
python backend/scripts/console.py
```

## Exemples avancés

### Créer une transaction manuellement

```python
>>> from datetime import date
>>> from uuid import uuid4
>>> session = asyncio.run(AsyncSessionLocal().__aenter__())
>>> tx = Transaction(
...     id=uuid4(),
...     user_id=cred.user_id,
...     credential_id=cred.id,
...     date=date.today(),
...     amount=Decimal('50.00'),
...     raw_label='TEST TRANSACTION',
...     category=TransactionCategory.FOOD,
...     is_expense=True,
...     transaction_key='test123'
... )
>>> session.add(tx)
>>> asyncio.run(session.commit())
>>> asyncio.run(session.close())
```

### Tester le service Ollama

```python
>>> from app.services.ollama import get_ollama_service
>>> ollama = get_ollama_service()
>>> asyncio.run(ollama.normalize_label("PRLVM SEPA NETFLIX.COM"))
{'cleaned_label': 'Netflix', 'merchant_name': 'Netflix', 'category': 'subscriptions', 'confidence': 0.95}
```

### Détecter les récurrents

```python
>>> from app.services.recurring import RecurringExpenseService
>>> session = asyncio.run(AsyncSessionLocal().__aenter__())
>>> service = RecurringExpenseService(session)
>>> asyncio.run(service.analyze_and_save(str(cred.user_id), months_back=3))
>>> asyncio.run(session.close())
```
