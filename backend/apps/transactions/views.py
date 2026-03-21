import re
from datetime import datetime

from django.db.models import Q, Sum, Count, Value
from django.db.models import Avg, Min, Max, TextField
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_rq import get_queue
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.jobs.enrich import enrich_single_transaction, enqueue_user_enrichment_jobs

from .models import EnrichmentRule, Transaction
from .pagination import UniformPagination
from .serializers import RecurringFlagSerializer, TransactionBulkEnrichSerializer, TransactionCategoryPatchSerializer, TransactionCorrectionSerializer, TransactionSerializer


NOISE_TOKENS = {
    "carte", "cb", "prlv", "prlvm", "prelevement", "prelev", "sepa",
    "vir", "virement", "paiement", "achat",
}


def build_label_fingerprint(raw_label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_label.lower())
    cleaned = re.sub(r"\b\d+[a-z]*\b", " ", cleaned)
    tokens = [token for token in cleaned.split() if token not in NOISE_TOKENS and len(token) > 2]
    if not tokens:
        return "unknown"
    return " ".join(tokens[:8])


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    if value.lower() in {"true", "1", "yes"}:
        return True
    if value.lower() in {"false", "0", "no"}:
        return False
    return None


def _base_tx_queryset(request):
    return Transaction.objects.filter(user=request.user).select_related("enrichment_rule")


def _apply_common_filters(qs, request):
    if cat := request.query_params.get("category"):
        qs = qs.filter(Q(enrichment_rule__category=cat) | Q(enrichment_rule__isnull=True, category=cat))

    is_expense_raw = request.query_params.get("is_expense")
    is_expense = _parse_bool(is_expense_raw)
    if is_expense_raw is not None and is_expense is None:
        return None, Response({"detail": "Invalid is_expense; expected true/false"}, status=400)
    if is_expense is not None:
        qs = qs.filter(is_expense=is_expense)

    if date_from := request.query_params.get("date_from"):
        qs = qs.filter(date__gte=date_from)
    if date_to := request.query_params.get("date_to"):
        qs = qs.filter(date__lte=date_to)

    return qs, None


def _effective_category_expr():
    return Coalesce("enrichment_rule__category", "category", Value("other"))


def _effective_merchant_expr():
    return Coalesce("enrichment_rule__merchant_name", "merchant_name", Value(""))


def _money_to_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def _mad(values: list[float], med: float) -> float:
    deviations = [abs(v - med) for v in values]
    return _median(deviations)


def _bucket_to_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    # Trunc* can return datetime.date on some backends
    return value.isoformat()


@api_view(["GET"])
def transaction_list(request):
    qs = Transaction.objects.filter(user=request.user).select_related("enrichment_rule").order_by("-date", "-created_at")
    if cat := request.query_params.get("category"):
        qs = qs.filter(Q(enrichment_rule__category=cat) | Q(enrichment_rule__isnull=True, category=cat))
    if is_expense := request.query_params.get("is_expense"):
        qs = qs.filter(is_expense=is_expense.lower() == "true")
    if date_from := request.query_params.get("date_from"):
        qs = qs.filter(date__gte=date_from)
    if date_to := request.query_params.get("date_to"):
        qs = qs.filter(date__lte=date_to)

    paginator = UniformPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(TransactionSerializer(page, many=True).data)


@api_view(["GET"])
def transaction_summary(request):
    qs = Transaction.objects.filter(user=request.user)
    expenses = qs.filter(is_expense=True).aggregate(total=Sum("amount"))["total"] or 0
    income = qs.filter(is_expense=False).aggregate(total=Sum("amount"))["total"] or 0
    by_category = list(
        qs.annotate(effective_category=Coalesce("enrichment_rule__category", "category", Value("other")))
        .values("effective_category")
        .annotate(total=Sum("amount"))
        .annotate(count=Count("id"))
        .order_by("effective_category")
    )
    for item in by_category:
        item["category"] = item.pop("effective_category")
    return Response({"total_expenses": expenses, "total_income": income, "by_category": by_category})


@api_view(["GET"])
def transaction_analytics_timeseries(request):
    """Timeseries aggregation.

    Query params:
      - granularity: day|month|year (default: month)
      - date_from, date_to, category, is_expense: common filters
    """
    granularity = (request.query_params.get("granularity") or "month").lower()
    trunc_map = {"day": TruncDay("date"), "month": TruncMonth("date"), "year": TruncYear("date")}
    if granularity not in trunc_map:
        return Response({"detail": "Invalid granularity; expected day/month/year"}, status=400)

    qs, err = _apply_common_filters(_base_tx_queryset(request), request)
    if err:
        return err

    qs = qs.annotate(bucket=trunc_map[granularity])
    rows = list(
        qs.values("bucket")
        .annotate(
            expenses=Sum("amount", filter=Q(is_expense=True)),
            income=Sum("amount", filter=Q(is_expense=False)),
            count=Count("id"),
        )
        .order_by("bucket")
    )
    for r in rows:
        exp = r.get("expenses") or 0
        inc = r.get("income") or 0
        r["net"] = inc - exp
        r["date"] = _bucket_to_iso(r.pop("bucket") if "bucket" in r else None)
        r["expenses"] = _money_to_float(exp)
        r["income"] = _money_to_float(inc)
        r["net"] = _money_to_float(r["net"])

    totals = qs.aggregate(
        total_expenses=Sum("amount", filter=Q(is_expense=True)),
        total_income=Sum("amount", filter=Q(is_expense=False)),
        count=Count("id"),
    )
    total_expenses = totals.get("total_expenses") or 0
    total_income = totals.get("total_income") or 0

    return Response(
        {
            "granularity": granularity,
            "items": rows,
            "totals": {
                "total_expenses": _money_to_float(total_expenses),
                "total_income": _money_to_float(total_income),
                "net": _money_to_float(total_income - total_expenses),
                "count": totals.get("count") or 0,
            },
        }
    )


@api_view(["GET"])
def transaction_analytics_grouped(request):
    """Grouped aggregation.

    Query params:
      - group_by: category|merchant (default: category)
      - limit: int (default: 30)
      - date_from, date_to, category, is_expense: common filters
    """
    group_by = (request.query_params.get("group_by") or "category").lower()
    limit = int(request.query_params.get("limit") or 30)
    limit = max(1, min(limit, 200))

    qs, err = _apply_common_filters(_base_tx_queryset(request), request)
    if err:
        return err

    if group_by == "category":
        qs = qs.annotate(key=_effective_category_expr())
    elif group_by == "merchant":
        qs = qs.annotate(key=_effective_merchant_expr())
    else:
        return Response({"detail": "Invalid group_by; expected category/merchant"}, status=400)

    rows = list(
        qs.values("key")
        .annotate(total=Sum("amount"), expenses=Sum("amount", filter=Q(is_expense=True)), income=Sum("amount", filter=Q(is_expense=False)), count=Count("id"))
        .order_by("-expenses", "-total")
    )[:limit]

    for r in rows:
        r["group"] = r.pop("key")
        r["total"] = _money_to_float(r.get("total") or 0)
        r["expenses"] = _money_to_float(r.get("expenses") or 0)
        r["income"] = _money_to_float(r.get("income") or 0)

    return Response({"group_by": group_by, "items": rows})


@api_view(["GET"])
def transaction_analytics_compare(request):
    """Compare two periods.

    Required query params:
      - a_from, a_to, b_from, b_to (YYYY-MM-DD)
    Optional:
      - category, is_expense
    """
    a_from = request.query_params.get("a_from")
    a_to = request.query_params.get("a_to")
    b_from = request.query_params.get("b_from")
    b_to = request.query_params.get("b_to")
    if not all([a_from, a_to, b_from, b_to]):
        return Response({"detail": "Missing required params: a_from,a_to,b_from,b_to"}, status=400)

    base_qs, err = _apply_common_filters(_base_tx_queryset(request), request)
    if err:
        return err

    def period_agg(qs, dfrom, dto):
        p = qs.filter(date__gte=dfrom, date__lte=dto)
        totals = p.aggregate(
            expenses=Sum("amount", filter=Q(is_expense=True)),
            income=Sum("amount", filter=Q(is_expense=False)),
            count=Count("id"),
        )
        exp = totals.get("expenses") or 0
        inc = totals.get("income") or 0
        return {
            "from": dfrom,
            "to": dto,
            "expenses": _money_to_float(exp),
            "income": _money_to_float(inc),
            "net": _money_to_float(inc - exp),
            "count": totals.get("count") or 0,
        }

    a = period_agg(base_qs, a_from, a_to)
    b = period_agg(base_qs, b_from, b_to)

    def pct(delta, base):
        if base == 0:
            return None
        return (delta / base) * 100.0

    deltas = {
        "expenses": a["expenses"] - b["expenses"],
        "income": a["income"] - b["income"],
        "net": a["net"] - b["net"],
        "count": a["count"] - b["count"],
    }
    deltas_pct = {
        "expenses": pct(deltas["expenses"], b["expenses"]),
        "income": pct(deltas["income"], b["income"]),
        "net": pct(deltas["net"], b["net"]),
        "count": pct(deltas["count"], float(b["count"]) if b["count"] else 0.0),
    }

    return Response({"period_a": a, "period_b": b, "delta": deltas, "delta_pct": deltas_pct})


@api_view(["GET"])
def transaction_analytics_top(request):
    """Top transactions.

    Query params:
      - kind: expenses|income|all (default: expenses)
      - limit: int (default: 20)
      - date_from, date_to, category: common filters (category applies to effective category)
    """
    kind = (request.query_params.get("kind") or "expenses").lower()
    limit = int(request.query_params.get("limit") or 20)
    limit = max(1, min(limit, 200))

    qs, err = _apply_common_filters(_base_tx_queryset(request), request)
    if err:
        return err

    if kind == "expenses":
        qs = qs.filter(is_expense=True).order_by("-amount", "-date")
    elif kind == "income":
        qs = qs.filter(is_expense=False).order_by("-amount", "-date")
    elif kind == "all":
        qs = qs.order_by("-amount", "-date")
    else:
        return Response({"detail": "Invalid kind; expected expenses/income/all"}, status=400)

    items = TransactionSerializer(qs[:limit], many=True).data
    return Response({"kind": kind, "limit": limit, "items": items})


@api_view(["GET"])
def transaction_analytics_anomalies(request):
    """Detect anomalies among expenses using robust z-score on amounts.

    Query params:
      - scope: global|category|merchant (default: global)
      - threshold: float (default: 3.5)
      - min_group_size: int (default: 8)
      - limit: int (default: 50)
      - date_from, date_to, category: common filters
    """
    scope = (request.query_params.get("scope") or "global").lower()
    threshold = float(request.query_params.get("threshold") or 3.5)
    min_group_size = int(request.query_params.get("min_group_size") or 8)
    limit = int(request.query_params.get("limit") or 50)
    limit = max(1, min(limit, 200))
    min_group_size = max(3, min(min_group_size, 200))

    qs, err = _apply_common_filters(_base_tx_queryset(request), request)
    if err:
        return err
    qs = qs.filter(is_expense=True)

    if scope == "global":
        sample = list(qs.values_list("amount", flat=True))
        amounts = [_money_to_float(v) for v in sample]
        med = _median(amounts)
        mad = _mad(amounts, med)
        denom = mad * 1.4826
        denom = denom if denom > 0 else None

        suspects = []
        for tx in qs.order_by("-amount", "-date")[: 2000]:
            amt = _money_to_float(tx.amount)
            if denom is None:
                score = None
            else:
                score = 0.6745 * (amt - med) / denom
            if score is not None and abs(score) >= threshold:
                suspects.append({"id": str(tx.id), "score": float(score), "amount": amt, "date": tx.date.isoformat()})

        suspect_ids = [s["id"] for s in sorted(suspects, key=lambda x: abs(x["score"]), reverse=True)[:limit]]
        txs = list(Transaction.objects.filter(user=request.user, id__in=suspect_ids).select_related("enrichment_rule"))
        by_id = {str(t.id): t for t in txs}
        items = []
        for sid in suspect_ids:
            t = by_id.get(sid)
            if not t:
                continue
            data = TransactionSerializer(t).data
            data["anomaly_score"] = next((s["score"] for s in suspects if s["id"] == sid), None)
            items.append(data)

        return Response({"scope": scope, "threshold": threshold, "items": items, "stats": {"median": med, "mad": mad}})

    if scope not in {"category", "merchant"}:
        return Response({"detail": "Invalid scope; expected global/category/merchant"}, status=400)

    key_expr = _effective_category_expr() if scope == "category" else _effective_merchant_expr()
    candidates = qs.annotate(scope_key=key_expr).values("id", "amount", "date", "scope_key")

    groups: dict[str, list[dict]] = {}
    for row in candidates:
        key = row.get("scope_key") or ""
        groups.setdefault(key, []).append(row)

    suspects: list[tuple[str, float]] = []
    for key, rows in groups.items():
        if len(rows) < min_group_size:
            continue
        amounts = [_money_to_float(r["amount"]) for r in rows]
        med = _median(amounts)
        mad = _mad(amounts, med)
        denom = mad * 1.4826
        if denom <= 0:
            continue
        for r in rows:
            amt = _money_to_float(r["amount"])
            score = 0.6745 * (amt - med) / denom
            if abs(score) >= threshold:
                suspects.append((str(r["id"]), float(score)))

    suspects.sort(key=lambda x: abs(x[1]), reverse=True)
    suspect_ids = [sid for sid, _ in suspects[:limit]]

    txs = list(Transaction.objects.filter(user=request.user, id__in=suspect_ids).select_related("enrichment_rule"))
    by_id = {str(t.id): t for t in txs}
    score_by_id = {sid: score for sid, score in suspects}
    items = []
    for sid in suspect_ids:
        t = by_id.get(sid)
        if not t:
            continue
        data = TransactionSerializer(t).data
        data["anomaly_score"] = score_by_id.get(sid)
        items.append(data)
    return Response({"scope": scope, "threshold": threshold, "min_group_size": min_group_size, "items": items})


@api_view(["GET"])
def transaction_analytics_query(request):
    """Custom analytics query builder.

    Supports filtering by date range + label/merchant/category and returns aggregates.

    Query params:
      - date_from, date_to: optional
      - is_expense: optional true/false
      - category: optional (effective category)

      - label: optional string (matches effective label)
      - label_match: exact|contains|icontains (default: icontains)

      - merchant: optional string (matches effective merchant)
      - merchant_match: exact|contains|icontains (default: icontains)

      - group_by: none|day|month|year|category|merchant|label (default: none)
      - limit: int (default: 200)
    """
    qs, err = _apply_common_filters(_base_tx_queryset(request), request)
    if err:
        return err

    qs = qs.annotate(
        effective_category=_effective_category_expr(),
        effective_merchant=_effective_merchant_expr(),
        effective_label=Coalesce("enrichment_rule__cleaned_label", "cleaned_label", "raw_label", output_field=TextField()),
    )

    label = request.query_params.get("label")
    label_match = (request.query_params.get("label_match") or "icontains").lower()
    if label:
        if label_match == "exact":
            qs = qs.filter(effective_label=label)
        elif label_match in {"contains", "icontains"}:
            lookup = "effective_label__icontains" if label_match == "icontains" else "effective_label__contains"
            qs = qs.filter(**{lookup: label})
        else:
            return Response({"detail": "Invalid label_match; expected exact/contains/icontains"}, status=400)

    merchant = request.query_params.get("merchant")
    merchant_match = (request.query_params.get("merchant_match") or "icontains").lower()
    if merchant:
        if merchant_match == "exact":
            qs = qs.filter(effective_merchant=merchant)
        elif merchant_match in {"contains", "icontains"}:
            lookup = "effective_merchant__icontains" if merchant_match == "icontains" else "effective_merchant__contains"
            qs = qs.filter(**{lookup: merchant})
        else:
            return Response({"detail": "Invalid merchant_match; expected exact/contains/icontains"}, status=400)

    group_by = (request.query_params.get("group_by") or "none").lower()
    limit = int(request.query_params.get("limit") or 200)
    limit = max(1, min(limit, 2000))

    aggregates = {
        "total": Sum("amount"),
        "count": Count("id"),
        "avg": Avg("amount"),
        "min": Min("amount"),
        "max": Max("amount"),
    }

    if group_by == "none":
        res = qs.aggregate(**aggregates)
        return Response(
            {
                "group_by": "none",
                "filters": {
                    "date_from": request.query_params.get("date_from"),
                    "date_to": request.query_params.get("date_to"),
                    "is_expense": request.query_params.get("is_expense"),
                    "category": request.query_params.get("category"),
                    "label": label,
                    "label_match": label_match,
                    "merchant": merchant,
                    "merchant_match": merchant_match,
                },
                "result": {
                    "total": _money_to_float(res.get("total") or 0),
                    "count": res.get("count") or 0,
                    "avg": _money_to_float(res.get("avg") or 0),
                    "min": _money_to_float(res.get("min") or 0),
                    "max": _money_to_float(res.get("max") or 0),
                },
            }
        )

    if group_by in {"day", "month", "year"}:
        trunc = {"day": TruncDay("date"), "month": TruncMonth("date"), "year": TruncYear("date")}[group_by]
        rows = list(qs.annotate(bucket=trunc).values("bucket").annotate(**aggregates).order_by("bucket"))
        items = []
        for r in rows[:limit]:
            items.append(
                {
                    "group": _bucket_to_iso(r.get("bucket")),
                    "total": _money_to_float(r.get("total") or 0),
                    "count": r.get("count") or 0,
                    "avg": _money_to_float(r.get("avg") or 0),
                    "min": _money_to_float(r.get("min") or 0),
                    "max": _money_to_float(r.get("max") or 0),
                }
            )
        return Response({"group_by": group_by, "items": items})

    if group_by in {"category", "merchant", "label"}:
        if group_by == "category":
            key = "effective_category"
        elif group_by == "merchant":
            key = "effective_merchant"
        else:
            key = "effective_label"

        rows = list(qs.values(key).annotate(**aggregates).order_by("-total"))
        items = []
        for r in rows[:limit]:
            items.append(
                {
                    "group": r.get(key) or "",
                    "total": _money_to_float(r.get("total") or 0),
                    "count": r.get("count") or 0,
                    "avg": _money_to_float(r.get("avg") or 0),
                    "min": _money_to_float(r.get("min") or 0),
                    "max": _money_to_float(r.get("max") or 0),
                }
            )
        return Response({"group_by": group_by, "items": items})

    return Response({"detail": "Invalid group_by"}, status=400)


@api_view(["GET", "DELETE"])
def transaction_detail_or_delete(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == "DELETE":
        tx.delete()
        return Response(status=204)
    return Response(TransactionSerializer(tx).data)


@api_view(["PATCH"])
def transaction_category_patch(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    s = TransactionCategoryPatchSerializer(data=request.data)
    s.is_valid(raise_exception=True)

    tx.category = s.validated_data["category"]
    tx.save(update_fields=["category", "updated_at"])

    rule, _ = EnrichmentRule.objects.update_or_create(
        user=request.user,
        label_fingerprint=build_label_fingerprint(tx.raw_label),
        defaults={
            "merchant_name": tx.merchant_name,
            "cleaned_label": tx.cleaned_label or tx.raw_label,
            "category": tx.category,
            "learned_from_transaction": tx,
        },
    )
    tx.enrichment_rule = rule
    tx.save(update_fields=["enrichment_rule", "updated_at"])

    return Response(TransactionSerializer(tx).data)


@api_view(["PATCH"])
def transaction_correction_patch(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    s = TransactionCorrectionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    for field, value in s.validated_data.items():
        setattr(tx, field, value)
    tx.save()
    rule, _ = EnrichmentRule.objects.update_or_create(
        user=request.user,
        label_fingerprint=build_label_fingerprint(tx.raw_label),
        defaults={
            "merchant_name": tx.merchant_name,
            "cleaned_label": tx.cleaned_label or tx.raw_label,
            "category": tx.category,
            "learned_from_transaction": tx,
        },
    )
    tx.enrichment_rule = rule
    tx.save(update_fields=["enrichment_rule", "updated_at"])
    return Response(TransactionSerializer(tx).data)


@api_view(["POST"])
def transaction_enrich_bulk(request):
    serializer = TransactionBulkEnrichSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)

    max_transactions = serializer.validated_data["max_transactions"]
    _unused_days_back = serializer.validated_data["days_back"]  # kept for API compatibility
    worker_count = serializer.validated_data["worker_count"]
    enrich_all = serializer.validated_data["enrich_all"]

    pending_qs = Transaction.objects.filter(user=request.user, enriched_at__isnull=True).order_by("date", "created_at")
    if not enrich_all:
        pending_qs = pending_qs[:max_transactions]

    tx_ids = [str(tx_id) for tx_id in pending_qs.values_list("id", flat=True)]
    if not tx_ids:
        return Response({"status": "nothing_to_enqueue", "job_ids": [], "worker_count": 0, "transaction_count": 0})

    queue = get_queue("enrich")
    chunk_plan = enqueue_user_enrichment_jobs(
        user_id=str(request.user.id),
        transaction_ids=tx_ids,
        queue=queue,
    )

    return Response(
        {
            "job_ids": chunk_plan["job_ids"],
            "status": chunk_plan["status"],
            "user_id": str(request.user.id),
            "transaction_count": len(tx_ids),
            "worker_count": chunk_plan["worker_count"],
            "chunk_sizes": chunk_plan["chunk_sizes"],
            "chunk_size": chunk_plan["chunk_size"],
            "requested_worker_count": worker_count,
            "enrich_all": enrich_all,
        }
    )


@api_view(["POST"])
def transaction_enrich(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    queue = get_queue("enrich")
    job = queue.enqueue(enrich_single_transaction, str(tx.id))
    return Response({"job_id": job.id, "status": "queued", "transaction_id": str(tx.id)})


@api_view(["PATCH"])
def transaction_recurring_patch(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    s = RecurringFlagSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    tx.is_recurring = s.validated_data["is_recurring"]
    tx.save(update_fields=["is_recurring", "updated_at"])
    return Response(TransactionSerializer(tx).data)
