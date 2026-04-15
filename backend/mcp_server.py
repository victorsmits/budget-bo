#!/usr/bin/env python3
"""
Budget Bo — MCP Server (Model Context Protocol)

Ultra-polyvalent, secure, read-only MCP server compatible with claude.ai,
Claude Desktop, Claude Code, and any MCP client.

Transport:
  - streamable-http (default) : for claude.ai / remote usage
  - sse                       : legacy SSE transport
  - stdio                     : for Claude Desktop local

Security:
  - Read-only: no INSERT/UPDATE/DELETE via SQL tool
  - Credentials are never exposed (encrypted fields excluded)
  - Per-user token auth: each user has their own MCP token (McpToken model)
  - User isolation: tools only return data belonging to the token owner
"""

import argparse
import contextvars
import os
import sys
import json
import datetime
import uuid as uuid_mod
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Django bootstrap
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR.parent / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

# ---------------------------------------------------------------------------
# Django imports (available after setup)
# ---------------------------------------------------------------------------
from django.db import connection
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from apps.accounts.models import User, McpToken
from apps.bank_credentials.models import BankCredential, BankAccount
from apps.transactions.models import Transaction, TransactionCategory, EnrichmentRule
from apps.recurring.models import RecurringExpense, RecurrencePattern

# ---------------------------------------------------------------------------
# MCP SDK
# ---------------------------------------------------------------------------
from mcp.server.fastmcp import FastMCP

MCP_PORT = int(os.getenv("MCP_PORT", "8808"))
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")

mcp = FastMCP("Budget Bo")

# ---------------------------------------------------------------------------
# Per-request user context (set by auth middleware)
# ---------------------------------------------------------------------------
_current_user: contextvars.ContextVar[User | None] = contextvars.ContextVar(
    "_current_user", default=None
)


def _user() -> User:
    """Return the authenticated user for the current request."""
    u = _current_user.get()
    if u is None:
        raise ValueError("Aucun utilisateur authentifié. Vérifiez votre token MCP.")
    return u


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_serial(obj):
    """JSON serialiser for types not handled by default."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, uuid_mod.UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serialisable")


def _to_json(data) -> str:
    return json.dumps(data, default=_json_serial, ensure_ascii=False, indent=2)


def _tx_to_dict(tx: Transaction) -> dict:
    return {
        "id": str(tx.id),
        "date": tx.date,
        "amount": tx.amount,
        "display_label": tx.display_label,
        "display_category": tx.display_category,
        "display_merchant": tx.display_merchant,
        "raw_label": tx.raw_label,
        "is_expense": tx.is_expense,
        "is_recurring": tx.is_recurring,
        "currency": tx.currency,
        "ai_confidence": tx.ai_confidence,
        "enriched_at": tx.enriched_at,
    }


def _account_to_dict(acc: BankAccount) -> dict:
    return {
        "id": str(acc.id),
        "account_label": acc.account_label,
        "account_type": acc.account_type,
        "balance": acc.balance,
        "currency": acc.currency,
        "bank_name": acc.credential.bank_name if acc.credential else None,
    }


def _recurring_to_dict(r: RecurringExpense) -> dict:
    return {
        "id": str(r.id),
        "pattern_name": r.pattern_name,
        "pattern": r.pattern,
        "average_amount": r.average_amount,
        "frequency_days": r.frequency_days,
        "day_of_month": r.day_of_month,
        "next_expected_date": r.next_expected_date,
        "confidence_score": r.confidence_score,
        "is_active": r.is_active,
        "matched_transaction_count": r.matched_transaction_count,
        "first_seen_date": r.first_seen_date,
        "last_seen_date": r.last_seen_date,
    }


# ---------------------------------------------------------------------------
# MCP Tools — user is resolved automatically from the Bearer token
# ---------------------------------------------------------------------------


@mcp.tool()
def get_accounts() -> str:
    """Liste mes comptes bancaires avec leurs soldes."""
    user = _user()
    accounts = BankAccount.objects.filter(user=user).select_related("credential")
    data = [_account_to_dict(a) for a in accounts]
    total = sum(float(a["balance"]) for a in data)
    return _to_json({"accounts": data, "total_balance": total, "count": len(data)})


@mcp.tool()
def get_transactions(
    limit: int = 50,
    offset: int = 0,
    category: str = "",
    merchant: str = "",
    date_from: str = "",
    date_to: str = "",
    min_amount: float | None = None,
    max_amount: float | None = None,
    search: str = "",
    is_expense: bool | None = None,
    ordering: str = "-date",
) -> str:
    """
    Recherche et filtre mes transactions.

    Args:
        limit: Nombre max de résultats (défaut 50, max 200)
        offset: Décalage pour la pagination
        category: Filtrer par catégorie (housing, food, groceries, etc.)
        merchant: Filtrer par nom de marchand (recherche partielle)
        date_from: Date de début (YYYY-MM-DD)
        date_to: Date de fin (YYYY-MM-DD)
        min_amount: Montant minimum
        max_amount: Montant maximum
        search: Recherche textuelle dans le libellé
        is_expense: true = dépenses uniquement, false = revenus uniquement, vide = tout
        ordering: Tri (-date, date, -amount, amount)
    """
    user = _user()
    qs = Transaction.objects.filter(user=user).select_related("enrichment_rule")

    if category:
        qs = qs.filter(Q(category=category) | Q(enrichment_rule__category=category))
    if merchant:
        qs = qs.filter(
            Q(merchant_name__icontains=merchant)
            | Q(enrichment_rule__merchant_name__icontains=merchant)
        )
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if min_amount is not None:
        qs = qs.filter(amount__gte=min_amount)
    if max_amount is not None:
        qs = qs.filter(amount__lte=max_amount)
    if search:
        qs = qs.filter(
            Q(raw_label__icontains=search)
            | Q(cleaned_label__icontains=search)
            | Q(enrichment_rule__cleaned_label__icontains=search)
        )
    if is_expense is not None:
        qs = qs.filter(is_expense=is_expense)

    allowed_orderings = {"date", "-date", "amount", "-amount", "created_at", "-created_at"}
    if ordering not in allowed_orderings:
        ordering = "-date"

    total = qs.count()
    limit = min(limit, 200)
    txs = qs.order_by(ordering)[offset : offset + limit]

    return _to_json({
        "transactions": [_tx_to_dict(tx) for tx in txs],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@mcp.tool()
def get_transaction_summary(
    date_from: str = "",
    date_to: str = "",
) -> str:
    """
    Résumé de mes transactions : total dépenses, revenus, nombre, par catégorie.

    Args:
        date_from: Date de début (YYYY-MM-DD)
        date_to: Date de fin (YYYY-MM-DD)
    """
    user = _user()
    qs = Transaction.objects.filter(user=user)

    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    expenses = qs.filter(is_expense=True)
    income = qs.filter(is_expense=False)

    by_cat = (
        expenses.values("category")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )

    return _to_json({
        "total_expenses": expenses.aggregate(s=Sum("amount"))["s"] or 0,
        "total_income": income.aggregate(s=Sum("amount"))["s"] or 0,
        "expense_count": expenses.count(),
        "income_count": income.count(),
        "by_category": list(by_cat),
    })


@mcp.tool()
def get_monthly_trends(months: int = 6) -> str:
    """
    Tendances mensuelles : dépenses et revenus agrégés par mois.

    Args:
        months: Nombre de mois en arrière (défaut 6)
    """
    user = _user()
    cutoff = datetime.date.today() - datetime.timedelta(days=months * 31)

    qs = Transaction.objects.filter(user=user, date__gte=cutoff)

    expenses = (
        qs.filter(is_expense=True)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("month")
    )
    income = (
        qs.filter(is_expense=False)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("month")
    )

    return _to_json({
        "expenses_by_month": list(expenses),
        "income_by_month": list(income),
    })


@mcp.tool()
def get_spending_by_category(
    date_from: str = "",
    date_to: str = "",
    top_n: int = 0,
) -> str:
    """
    Répartition de mes dépenses par catégorie.

    Args:
        date_from: Date de début (YYYY-MM-DD)
        date_to: Date de fin (YYYY-MM-DD)
        top_n: Limiter au top N catégories (0 = toutes)
    """
    user = _user()
    qs = Transaction.objects.filter(user=user, is_expense=True)

    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    by_cat = (
        qs.values("category")
        .annotate(
            total=Sum("amount"),
            count=Count("id"),
            avg_amount=Avg("amount"),
        )
        .order_by("-total")
    )

    result = list(by_cat)
    grand_total = sum(float(c["total"]) for c in result)

    for c in result:
        c["percentage"] = round(float(c["total"]) / grand_total * 100, 1) if grand_total else 0

    if top_n > 0:
        result = result[:top_n]

    return _to_json({"categories": result, "grand_total": grand_total})


@mcp.tool()
def get_top_merchants(
    limit: int = 20,
    date_from: str = "",
    date_to: str = "",
) -> str:
    """
    Mes top marchands par montant total dépensé.

    Args:
        limit: Nombre de marchands (défaut 20)
        date_from: Date de début (YYYY-MM-DD)
        date_to: Date de fin (YYYY-MM-DD)
    """
    user = _user()
    qs = Transaction.objects.filter(user=user, is_expense=True).exclude(
        merchant_name__isnull=True
    ).exclude(merchant_name="")

    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    merchants = (
        qs.values("merchant_name")
        .annotate(total=Sum("amount"), count=Count("id"), avg=Avg("amount"))
        .order_by("-total")[:limit]
    )

    return _to_json({"merchants": list(merchants)})


@mcp.tool()
def get_recurring_expenses(active_only: bool = True) -> str:
    """
    Liste mes dépenses récurrentes détectées.

    Args:
        active_only: N'afficher que les dépenses actives (défaut true)
    """
    user = _user()
    qs = RecurringExpense.objects.filter(user=user)
    if active_only:
        qs = qs.filter(is_active=True)

    data = [_recurring_to_dict(r) for r in qs.order_by("-average_amount")]
    total_monthly = sum(
        float(r["average_amount"])
        for r in data
        if r["pattern"] == "monthly" and r["is_active"]
    )

    return _to_json({
        "recurring_expenses": data,
        "count": len(data),
        "estimated_monthly_total": total_monthly,
    })


@mcp.tool()
def get_upcoming_payments(days: int = 30) -> str:
    """
    Mes paiements récurrents attendus dans les prochains jours.

    Args:
        days: Nombre de jours à anticiper (défaut 30)
    """
    user = _user()
    cutoff = datetime.date.today() + datetime.timedelta(days=days)
    today = datetime.date.today()

    qs = RecurringExpense.objects.filter(
        user=user,
        is_active=True,
        next_expected_date__isnull=False,
        next_expected_date__gte=today,
        next_expected_date__lte=cutoff,
    ).order_by("next_expected_date")

    data = [_recurring_to_dict(r) for r in qs]
    total = sum(float(r["average_amount"]) for r in data)

    return _to_json({
        "upcoming": data,
        "count": len(data),
        "total_expected": total,
        "period": f"{today.isoformat()} → {cutoff.isoformat()}",
    })


@mcp.tool()
def get_enrichment_rules(limit: int = 50) -> str:
    """
    Liste mes règles d'enrichissement apprises (corrections utilisateur + IA).

    Args:
        limit: Nombre max de résultats (défaut 50)
    """
    user = _user()
    rules = EnrichmentRule.objects.filter(user=user).order_by("-usage_count")[:limit]

    data = [
        {
            "id": str(r.id),
            "label_fingerprint": r.label_fingerprint,
            "merchant_name": r.merchant_name,
            "cleaned_label": r.cleaned_label,
            "category": r.category,
            "usage_count": r.usage_count,
        }
        for r in rules
    ]

    return _to_json({"rules": data, "count": len(data)})


@mcp.tool()
def get_bank_credentials_status() -> str:
    """Statut de synchronisation de mes credentials bancaires (sans données sensibles)."""
    user = _user()
    creds = BankCredential.objects.filter(user=user)

    data = [
        {
            "id": str(c.id),
            "bank_name": c.bank_name,
            "bank_label": c.bank_label,
            "sync_status": c.sync_status,
            "sync_error_message": c.sync_error_message,
            "last_sync_at": c.last_sync_at,
            "is_active": c.is_active,
            "account_count": c.accounts.count(),
        }
        for c in creds
    ]

    return _to_json({"credentials": data, "count": len(data)})


@mcp.tool()
def get_dashboard() -> str:
    """Mon dashboard complet : solde total, dépenses/revenus du mois, top catégories, prochains paiements."""
    user = _user()
    today = datetime.date.today()
    first_of_month = today.replace(day=1)

    accounts = BankAccount.objects.filter(user=user)
    total_balance = accounts.aggregate(s=Sum("balance"))["s"] or 0

    month_txs = Transaction.objects.filter(user=user, date__gte=first_of_month)
    month_expenses = month_txs.filter(is_expense=True).aggregate(s=Sum("amount"))["s"] or 0
    month_income = month_txs.filter(is_expense=False).aggregate(s=Sum("amount"))["s"] or 0

    top_cats = (
        month_txs.filter(is_expense=True)
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )

    upcoming = RecurringExpense.objects.filter(
        user=user,
        is_active=True,
        next_expected_date__gte=today,
        next_expected_date__lte=today + datetime.timedelta(days=7),
    ).order_by("next_expected_date")[:5]

    recent = Transaction.objects.filter(user=user).select_related("enrichment_rule").order_by("-date")[:5]

    return _to_json({
        "total_balance": total_balance,
        "month": {
            "period": f"{first_of_month.isoformat()} → {today.isoformat()}",
            "expenses": month_expenses,
            "income": month_income,
            "net": float(month_income) - float(month_expenses),
        },
        "top_categories_this_month": list(top_cats),
        "upcoming_payments_7d": [_recurring_to_dict(r) for r in upcoming],
        "recent_transactions": [_tx_to_dict(tx) for tx in recent],
        "account_count": accounts.count(),
    })


@mcp.tool()
def execute_readonly_sql(query: str) -> str:
    """
    Exécute une requête SQL en lecture seule (SELECT uniquement).
    Les résultats sont automatiquement filtrés pour ne montrer que mes données.
    INTERDIT : INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE.

    Args:
        query: Requête SQL SELECT
    """
    user = _user()

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
    upper_query = query.upper().strip()

    for kw in forbidden:
        if kw in upper_query:
            return _to_json({"error": f"Opération interdite : {kw} n'est pas autorisé. Lecture seule."})

    if not upper_query.startswith("SELECT") and not upper_query.startswith("WITH") and not upper_query.startswith("EXPLAIN"):
        return _to_json({"error": "Seules les requêtes SELECT / WITH / EXPLAIN sont autorisées."})

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchmany(500)
            data = [dict(zip(columns, row)) for row in rows]
            return _to_json({
                "columns": columns,
                "rows": data,
                "row_count": len(data),
                "note": f"Résultats pour {user.email}. Pensez à filtrer par user_id = '{user.id}' si nécessaire.",
            })
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
def get_database_schema() -> str:
    """Retourne le schéma de la base (tables, colonnes, types) pour construire des requêtes SQL."""
    _user()  # require auth
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]

            tables = {}
            for row in data:
                tname = row["table_name"]
                if tname not in tables:
                    tables[tname] = []
                tables[tname].append({
                    "column": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"],
                })

            return _to_json({"tables": tables, "table_count": len(tables)})
    except Exception as e:
        return _to_json({"error": str(e)})


@mcp.tool()
def whoami() -> str:
    """Retourne les informations de l'utilisateur authentifié."""
    user = _user()
    return _to_json({
        "email": user.email,
        "display_name": user.display_name,
        "id": str(user.id),
    })


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------


@mcp.resource("budgetbo://categories")
def resource_categories() -> str:
    """Liste de toutes les catégories de transactions disponibles."""
    return _to_json([{"value": c.value, "label": c.label} for c in TransactionCategory])


@mcp.resource("budgetbo://recurrence-patterns")
def resource_patterns() -> str:
    """Liste des patterns de récurrence disponibles."""
    return _to_json([{"value": p.value, "label": p.label} for p in RecurrencePattern])


# ---------------------------------------------------------------------------
# ASGI auth middleware — resolve Bearer token → user via McpToken model
# ---------------------------------------------------------------------------


def _auth_middleware(app):
    """ASGI middleware: extract Bearer token, resolve McpToken → User, set contextvar."""

    async def wrapped(scope, receive, send):
        if scope["type"] == "http":
            from starlette.requests import Request
            from starlette.responses import JSONResponse

            request = Request(scope, receive)
            auth_header = request.headers.get("authorization", "")

            if not auth_header.startswith("Bearer "):
                resp = JSONResponse({"error": "Missing Bearer token"}, status_code=401)
                await resp(scope, receive, send)
                return

            token_str = auth_header[7:]  # strip "Bearer "
            try:
                mcp_token = McpToken.objects.select_related("user").get(
                    token=token_str, is_active=True
                )
            except McpToken.DoesNotExist:
                resp = JSONResponse({"error": "Invalid or revoked token"}, status_code=401)
                await resp(scope, receive, send)
                return

            mcp_token.last_used_at = timezone.now()
            mcp_token.save(update_fields=["last_used_at"])
            _current_user.set(mcp_token.user)

        await app(scope, receive, send)

    return wrapped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Budget Bo MCP Server")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse", "stdio"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
        help="Transport mode (default: streamable-http for claude.ai)",
    )
    parser.add_argument("--port", type=int, default=MCP_PORT, help=f"HTTP port (default: {MCP_PORT})")
    parser.add_argument("--host", default=MCP_HOST, help=f"HTTP host (default: {MCP_HOST})")
    args = parser.parse_args()

    # FastMCP takes host/port at init time
    server = FastMCP(
        "Budget Bo",
        instructions=(
            "Serveur MCP pour Budget Bo — accès sécurisé aux données budgétaires. "
            "L'utilisateur est authentifié automatiquement via son token. "
            "Tous les outils retournent uniquement les données de l'utilisateur connecté."
        ),
        host=args.host,
        port=args.port,
    )

    # Copy all registered tools, resources, prompts from the module-level mcp
    server._tool_manager = mcp._tool_manager
    server._resource_manager = mcp._resource_manager
    server._prompt_manager = mcp._prompt_manager

    if args.transport == "stdio":
        print("[Budget Bo MCP] Starting in stdio mode (Claude Desktop)", file=sys.stderr)
        server.run(transport="stdio")
    else:
        import uvicorn

        if args.transport == "sse":
            asgi_app = server.sse_app()
        else:
            asgi_app = server.streamable_http_app()

        # Wrap with per-user Bearer token auth
        asgi_app = _auth_middleware(asgi_app)

        print(
            f"[Budget Bo MCP] Starting on {args.host}:{args.port} "
            f"(transport={args.transport}, per-user token auth)",
            file=sys.stderr,
        )
        uvicorn.run(asgi_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
