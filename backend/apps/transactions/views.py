from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EnrichmentRule, Transaction
from .pagination import UniformPagination
from .serializers import RecurringFlagSerializer, TransactionCategoryPatchSerializer, TransactionCorrectionSerializer, TransactionSerializer


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
        label_fingerprint=tx.raw_label.lower().strip(),
        defaults={
            "merchant_name": tx.merchant_name,
            "cleaned_label": tx.cleaned_label or tx.raw_label,
            "category": tx.category,
            "learned_from_transaction": tx,
        },
    )
    return Response(TransactionSerializer(tx).data)


@api_view(["PATCH"])
def transaction_recurring_patch(request, transaction_id):
    tx = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    s = RecurringFlagSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    tx.is_recurring = s.validated_data["is_recurring"]
    tx.save(update_fields=["is_recurring", "updated_at"])
    return Response(TransactionSerializer(tx).data)
