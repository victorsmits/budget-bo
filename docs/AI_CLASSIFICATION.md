# Enrichissement IA des transactions

## Vue d'ensemble

Le pipeline d'enrichissement complète automatiquement chaque transaction avec :
- `cleaned_label` (libellé lisible),
- `merchant_name`,
- `category`,
- `is_expense`,
- `confidence`,
- `reasoning`.

Le système combine:
1. **Règles déterministes** (mots-clés métiers, signaux explicites de revenu),
2. **Gemini** (batch enrich + recherche web native),
3. **Fallback robuste** en cas d'échec partiel.

Selon la configuration, certains flux internes peuvent aussi exploiter **Ollama**.

## Variables d'environnement

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash
GEMINI_MAX_BATCH_SIZE=50
GEMINI_DAILY_LIMIT=18
GEMINI_MIN_DELAY_SECONDS=12

# optionnel selon les services utilisés
OLLAMA_BASE_URL=http://ollama:11434
```

## Déclenchement

### 1) Enrichir un lot de transactions utilisateur

```bash
curl -X POST http://localhost:8000/transactionsenrich \
  -H "Content-Type: application/json" \
  -d '{"max_transactions":100,"worker_count":4,"enrich_all":false}' \
  -b cookies.txt
```

### 2) Enrichir une transaction unitaire

```bash
curl -X POST http://localhost:8000/transactions/<transaction_id>/enrich \
  -b cookies.txt
```

### 3) Corriger une transaction (apprentissage)

```bash
curl -X PATCH http://localhost:8000/transactions/<transaction_id>/correction \
  -H "Content-Type: application/json" \
  -d '{"cleaned_label":"Netflix","merchant_name":"Netflix","category":"subscriptions"}' \
  -b cookies.txt
```

## Points importants

- La catégorie `income` n'est retenue qu'avec **indices explicites** (salaire, allocation, remboursement, etc.).
- Les corrections utilisateur créent/actualisent des règles persistées.
- Les jobs sont exécutés sur la queue RQ `enrich`.

## Monitoring rapide

```bash
# Workers / jobs RQ
docker compose logs -f rq-worker

# Dashboard RQ
# http://localhost:8000/admin/rq/
```

## Catégories gérées

`housing`, `transportation`, `food`, `groceries`, `dining`, `utilities`, `healthcare`, `entertainment`, `shopping`, `home_improvement`, `subscriptions`, `income`, `insurance`, `education`, `travel`, `other`.
