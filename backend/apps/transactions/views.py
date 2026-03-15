import re

from django.db.models import Q, Sum,Count, Value
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
