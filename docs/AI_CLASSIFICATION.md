# Classification par IA avec Ollama

## Vue d'ensemble

Budget Bo utilise Ollama avec le modèle Phi3 pour classifier automatiquement les transactions bancaires. Cette fonctionnalité permet de :

- **Normaliser les libellés** : `PRLVM SEPA NETFLIX.COM` → `Netflix`
- **Éviter les faux nettoyages** : si aucun meilleur libellé n'est trouvé, `cleaned_label` reste vide (`""`) au lieu de recopier le libellé brut
- **Extraire les marchands** : Identifier automatiquement le nom du commerçant
- **Catégoriser** : Assigner une catégorie (food, transportation, entertainment, etc.)
- **Calculer la confiance** : Score de 0.0 à 1.0 indiquant la fiabilité de la classification
- **Apprendre des corrections utilisateur** : Les corrections sont mémorisées et réutilisées automatiquement

## Configuration

### 1. Vérifier qu'Ollama fonctionne

```bash
docker compose exec ollama ollama list
```

Le modèle `phi3` doit être présent. Si non :

```bash
docker compose exec ollama ollama pull phi3
```

### 2. Variables d'environnement

Dans `.env`, assurez-vous que ces variables sont configurées :

```env
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=phi3
OLLAMA_TIMEOUT=120
```

## Utilisation

### Enrichissement automatique

Les nouvelles transactions sont automatiquement enrichies lors de la synchronisation bancaire.

Le prompt IA force désormais la vérification via recherche web (`web_search`) dès que le marchand est ambigu ou peu connu, afin d'obtenir un nom d'enseigne plus fiable et une meilleure catégorie métier.

Le worker limite aussi le nombre de tours d'outil et n'appelle la seconde étape de catégorisation IA que si nécessaire, pour réduire les timeouts (`/api/chat` 500) et garder un enrichissement robuste même si Ollama est lent.

La catégorie `income` est désormais appliquée uniquement en présence d'indices explicites (salaire, paie, remboursement, allocation, etc.) et non pas simplement parce que le montant est positif.

### Enrichissement manuel

Pour déclencher manuellement l'enrichissement des transactions non traitées :

```bash
# Via l'API
curl -X POST "http://localhost:8000/transactions/enrich?days_back=30" \
  -b cookies.txt

# Via le script (pour tests)
docker compose exec backend python scripts/enrich_transactions.py
```


### Correction utilisateur + apprentissage

Si une classification est incorrecte, l'utilisateur peut corriger la transaction.
Le backend crée/met à jour une règle d'enrichissement pour réutiliser ce choix
la prochaine fois qu'un libellé similaire est rencontré.

```bash
curl -X PATCH "http://localhost:8000/transactions/<transaction_id>/correction" \
  -H "Content-Type: application/json" \
  -d '{"cleaned_label":"Netflix","merchant_name":"Netflix","category":"subscriptions"}' \
  -b cookies.txt
```

### Catégories disponibles

- `housing` - Logement
- `transportation` - Transport
- `food` - Alimentation (générique)
- `groceries` - Courses / supermarché
- `dining` - Restaurant / snack / livraison repas
- `utilities` - Factures (électricité, eau, etc.)
- `healthcare` - Santé
- `entertainment` - Divertissement
- `shopping` - Shopping (fallback)
- `home_improvement` - Maison / bricolage / ameublement
- `subscriptions` - Abonnements
- `income` - Revenus
- `insurance` - Assurance
- `education` - Éducation
- `travel` - Voyage
- `other` - Autre


## Nouveau pipeline d'enrichissement (fiabilité renforcée)

Le pipeline a été refondu pour s'inspirer des pratiques fintech (priorité à la précision et à la traçabilité) :

1. **Mémoire utilisateur d'abord** : si une règle d'apprentissage existe, elle est appliquée directement (confiance maximale).
2. **Passage LLM #1 (normalisation)** : extraction du `cleaned_label`, du `merchant_name` et d'une catégorie initiale.
3. **Garde-fous déterministes** :
   - normalisation du marchand côté consommateur (suppression des suffixes légaux),
   - catégorisation heuristique (mots-clés métier),
   - protection anti-faux-positifs `income` (signal explicite obligatoire).
4. **Passage LLM #2 conditionnel (catégorisation)** : déclenché uniquement quand la catégorie reste ambiguë (`other` / `shopping` / `income` sans signal fort).
5. **Calibration de confiance** : score final calculé à partir du consensus entre heuristiques + LLM, pénalisé en cas d'ambiguïté.
6. **Reasoning structuré** : la transaction conserve une trace de la provenance de la décision (`llm_normalization`, `heuristic`, `merchant_resolution`, `llm_categorization`).
7. **Résolution de nom public** : pour les libellés opaques (ex: préfixes terminal type `X7722`), une passe dédiée tente d'identifier l'enseigne grand public via recherche web enrichie.
8. **Confiance conservatrice** : quand le nom public n'est pas vérifiable (marchand opaque, `cleaned_label` vide), le score est volontairement pénalisé.

Cette approche réduit les hallucinations, améliore la stabilité sur les cas connus et permet d'isoler les cas réellement ambigus.

## Monitoring

### Vérifier l'état des transactions

```python
# Nombre de transactions enrichies/non enrichies
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.models import Transaction
from sqlalchemy import select, func

async def check():
    async with AsyncSessionLocal() as session:
        enriched = await session.scalar(select(func.count()).where(Transaction.enriched_at.isnot(None)))
        not_enriched = await session.scalar(select(func.count()).where(Transaction.enriched_at.is_(None)))
        print(f'Enrichies: {enriched}, Non enrichies: {not_enriched}')

asyncio.run(check())
"
```

### Logs du worker

```bash
docker compose logs worker -f
```

### Interface Flower (monitoring Celery)

Accédez à http://localhost:5555 pour voir l'état des tâches d'enrichissement.

## Personnalisation

### Modifier le modèle IA

Pour utiliser un autre modèle (ex: llama3):

1. Téléchargez le modèle :
   ```bash
   docker compose exec ollama ollama pull llama3:8b
   ```

2. Modifiez `.env` :
   ```env
   OLLAMA_MODEL=llama3:8b
   ```

3. Redémarrez les services :
   ```bash
   docker compose restart backend worker
   ```

### Ajuster les prompts

Le service Ollama utilise des prompts spécifiques dans `app/services/ollama.py`. Vous pouvez les modifier pour améliorer la classification selon vos besoins.

## Dépannage

### Problème : Les transactions ne sont pas enrichies

1. Vérifiez qu'Ollama fonctionne :
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Vérifiez les logs du worker pour les erreurs

3. Testez manuellement :
   ```bash
   docker compose exec backend python -c "
   import asyncio
   from app.services.ollama import get_ollama_service
   
   async def test():
       ollama = get_ollama_service()
       result = await ollama.normalize_label('PRLVM SEPA NETFLIX.COM')
       print(result)
   
   asyncio.run(test())
   "
   ```

### Problème : Mauvaises classifications

Le modèle Phi3 peut parfois faire des erreurs. Pour améliorer :

1. Augmentez la température dans `_generate()` pour plus de créativité
2. Modifiez le prompt pour être plus spécifique
3. Ajoutez des exemples dans le prompt (few-shot learning)

### Problème : Trop de transactions en erreur

Cela peut arriver si le modèle génère du JSON malformé. Le service inclut maintenant un parsing robuste avec regex pour extraire les données même si le JSON est imparfait.
