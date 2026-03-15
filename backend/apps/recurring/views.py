from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_rq import get_queue
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.jobs.batch import detect_recurring_patterns
from .models import RecurringExpense
from .serializers import RecurringExpenseSerializer


@api_view(["GET"])
def recurring_list(request):
    qs = RecurringExpense.objects.filter(user=request.user, is_active=True).order_by("next_expected_date")
    return Response(RecurringExpenseSerializer(qs, many=True).data)


@api_view(["GET"])
def recurring_upcoming(request):
    end = timezone.now().date() + timedelta(days=30)
    qs = RecurringExpense.objects.filter(user=request.user, is_active=True, next_expected_date__lte=end)
    return Response(RecurringExpenseSerializer(qs, many=True).data)


@api_view(["POST"])
def recurring_detect(request):
    queue = get_queue("default")
    job = queue.enqueue(detect_recurring_patterns, str(request.user.id))
    return Response({"job_id": job.id, "status": "queued"})


@api_view(["GET"])
def recurring_summary(request):
    qs = RecurringExpense.objects.filter(user=request.user, is_active=True)
    return Response({"active_count": qs.count(), "estimated_monthly_total": sum([r.average_amount for r in qs])})


@api_view(["DELETE"])
def recurring_delete(request, recurring_id):
    row = get_object_or_404(RecurringExpense, id=recurring_id, user=request.user)
    row.is_active = False
    row.save(update_fields=["is_active", "updated_at"])
    return Response(status=204)
