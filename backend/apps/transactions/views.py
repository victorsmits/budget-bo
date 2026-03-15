from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django_rq import get_queue
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.jobs.enrich import (
    enrich_single_transaction,
    enrich_user_transactions,
    enrich_user_transactions_chunk,
)

from services.enrichment_memory import build_label_fingerprint

from .models import EnrichmentRule, Transaction
from .pagination import UniformPagination
from .serializers import RecurringFlagSerializer, TransactionBulkEnrichSerializer, TransactionCategoryPatchSerializer, TransactionCorrectionSerializer, TransactionSerializer


@api_view(["GET"])
def transaction_list(request):
    qs = Transaction.objects.filter(user=request.user).order_by("-date", "-created_at")
    if cat := request.query_params.get("category"):
        qs = qs.filter(category=cat)
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
    by_category = list(qs.values("category").annotate(total=Sum("amount")).order_by("category"))
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
    return Response(TransactionSerializer(tx).data)


@api_view(["PATCH"])
def transaction_correction_patch(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    s = TransactionCorrectionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    for field, value in s.validated_data.items():
        setattr(tx, field, value)
    tx.save()
    EnrichmentRule.objects.update_or_create(
        user=request.user,
        label_fingerprint=build_label_fingerprint(tx.raw_label),
        defaults={
            "merchant_name": tx.merchant_name,
            "cleaned_label": tx.cleaned_label or tx.raw_label,
            "category": tx.category,
            "learned_from_transaction": tx,
        },
    )
    return Response(TransactionSerializer(tx).data)


@api_view(["POST"])
def transaction_enrich_bulk(request):
    serializer = TransactionBulkEnrichSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)

    max_transactions = serializer.validated_data["max_transactions"]
    days_back = serializer.validated_data["days_back"]
    worker_count = serializer.validated_data["worker_count"]
    enrich_all = serializer.validated_data["enrich_all"]

    pending_qs = Transaction.objects.filter(user=request.user, enriched_at__isnull=True).order_by("date", "created_at")
    if not enrich_all:
        pending_qs = pending_qs[:max_transactions]

    tx_ids = [str(tx_id) for tx_id in pending_qs.values_list("id", flat=True)]
    if not tx_ids:
        return Response({"status": "nothing_to_enqueue", "job_ids": [], "worker_count": 0, "transaction_count": 0})

    queue = get_queue("enrich")

    if worker_count <= 1:
        job = queue.enqueue(
            enrich_user_transactions,
            str(request.user.id),
            days_back,
            len(tx_ids),
        )
        return Response(
            {
                "job_ids": [job.id],
                "status": "queued",
                "user_id": str(request.user.id),
                "transaction_count": len(tx_ids),
                "worker_count": 1,
                "chunk_sizes": [len(tx_ids)],
                "enrich_all": enrich_all,
            }
        )

    actual_workers = min(worker_count, len(tx_ids))
    chunks: list[list[str]] = [[] for _ in range(actual_workers)]
    for index, tx_id in enumerate(tx_ids):
        chunks[index % actual_workers].append(tx_id)

    job_ids: list[str] = []
    chunk_sizes: list[int] = []
    for chunk in chunks:
        if not chunk:
            continue
        job = queue.enqueue(
            enrich_user_transactions_chunk,
            str(request.user.id),
            chunk,
        )
        job_ids.append(job.id)
        chunk_sizes.append(len(chunk))

    return Response(
        {
            "job_ids": job_ids,
            "status": "queued",
            "user_id": str(request.user.id),
            "transaction_count": len(tx_ids),
            "worker_count": len(job_ids),
            "chunk_sizes": chunk_sizes,
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
