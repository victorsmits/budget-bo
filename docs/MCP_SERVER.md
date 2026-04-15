# Budget Bo — Serveur MCP

Serveur MCP (Model Context Protocol) intégré au backend, compatible avec **claude.ai**, **Claude Desktop**, **Claude Code** et tout client MCP.

Accès direct en lecture seule à toutes les données budgétaires via le Django ORM.

## Fichier

`backend/mcp_server.py` — point d'entrée unique, aucune dépendance externe hors `mcp` (ajouté dans `backend/requirements.txt`).

Le service Docker `mcp-server` est défini dans `docker-compose.yml` et `docker-compose.prod.yml`. Il démarre automatiquement avec le reste de l'application.

## Outils disponibles (14)

| Outil | Description |
|---|---|
| `list_users` | Liste les utilisateurs (email, display_name) |
| `get_accounts` | Comptes bancaires + soldes |
| `get_transactions` | Recherche/filtre (catégorie, marchand, date, montant, texte) |
| `get_transaction_summary` | Total dépenses/revenus, répartition par catégorie |
| `get_monthly_trends` | Tendances mensuelles sur N mois |
| `get_spending_by_category` | Répartition par catégorie avec pourcentages |
| `get_top_merchants` | Top marchands par montant dépensé |
| `get_recurring_expenses` | Dépenses récurrentes détectées |
| `get_upcoming_payments` | Paiements récurrents à venir (N jours) |
| `get_enrichment_rules` | Règles d'enrichissement apprises |
| `get_bank_credentials_status` | Statut de synchronisation (sans données sensibles) |
| `get_dashboard` | Dashboard complet (solde, mois, catégories, prochains paiements) |
| `execute_readonly_sql` | Requêtes SQL SELECT personnalisées |
| `get_database_schema` | Schéma complet de la base (tables, colonnes, types) |

## Sécurité

- **Lecture seule** — aucune mutation possible
- **Credentials protégés** — login/password bancaires chiffrés jamais exposés
- **SQL filtré** — INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE bloqués
- **Token par utilisateur** — chaque user a son propre token (`McpToken` en DB), isolation complète des données

## Transports

| Transport | Usage |
|---|---|
| `streamable-http` | **claude.ai** (défaut) |
| `sse` | Clients SSE legacy |
| `stdio` | Claude Desktop local |

---

## Démarrage (Docker)

Le serveur MCP démarre automatiquement avec `docker compose up` :

```bash
docker compose up -d
```

Il est accessible sur `http://localhost:8808/mcp`.

Pour voir les logs :

```bash
docker compose logs -f mcp-server
```

---

## Utilisation avec claude.ai (en ligne)

### 1) Lancer l'app

```bash
docker compose up -d
```

Le serveur MCP démarre automatiquement sur le port 8808.

### 2) Exposer sur internet

claude.ai se connecte depuis les serveurs d'Anthropic → le serveur doit être accessible sur internet.

```bash
ngrok http 8808
```

Copier l'URL publique affichée (ex. `https://xxxx-xxx.ngrok-free.app`).

### 3) Ajouter le connecteur sur claude.ai

1. [claude.ai/customize/connectors](https://claude.ai/customize/connectors)
2. **"+"** → **"Add custom connector"**
3. URL : `https://xxxx-xxx.ngrok-free.app/mcp`
4. **"Add"**

### 4) Activer dans une conversation

Dans un chat, **"+"** en bas à gauche → **"Connectors"** → activer **Budget Bo**.

---

## Utilisation avec Claude Desktop (local)

Le serveur MCP tourne déjà dans Docker. Configurer Claude Desktop pour s'y connecter en HTTP :

Config (`~/.config/Claude/claude_desktop_config.json` ou `~/Library/Application Support/Claude/claude_desktop_config.json`) :

```json
{
  "mcpServers": {
    "budget-bo": {
      "url": "http://localhost:8808/mcp"
    }
  }
}
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `MCP_TRANSPORT` | `streamable-http` | Transport |
| `MCP_HOST` | `0.0.0.0` | Host d'écoute |
| `MCP_PORT` | `8808` | Port d'écoute |

## Tokens par utilisateur

Chaque utilisateur a son propre token MCP. Les outils ne retournent que les données du propriétaire du token.

### Créer un token

```bash
docker compose exec mcp-server python manage.py mcp_tokens create user@example.com --label "claude.ai"
```

Le token s'affiche une seule fois — le copier immédiatement.

### Lister les tokens actifs

```bash
docker compose exec mcp-server python manage.py mcp_tokens list
```

### Révoquer un token

```bash
docker compose exec mcp-server python manage.py mcp_tokens revoke <token>
```

---

## Exemples de prompts claude.ai

- *"Montre-moi mon dashboard financier"*
- *"Quelles sont mes 5 plus grosses dépenses ce mois ?"*
- *"Répartition de mes dépenses par catégorie sur les 3 derniers mois"*
- *"Quels abonnements arrivent la semaine prochaine ?"*
- *"Tendance de mes dépenses mois par mois sur 6 mois"*
- *"Exécute : SELECT category, SUM(amount) FROM transactions_transaction GROUP BY category"*
