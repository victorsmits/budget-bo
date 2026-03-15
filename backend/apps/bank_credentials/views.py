from django.shortcuts import get_object_or_404
from django_rq import get_queue
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.jobs.sync import sync_credential_transactions
from .models import BankCredential
from .serializers import BankCredentialSerializer


@api_view(["GET", "POST"])
def credential_list_create(request):
    if request.method == "GET":
        qs = BankCredential.objects.filter(user=request.user, is_active=True).order_by("-created_at")
        return Response(BankCredentialSerializer(qs, many=True).data)
    serializer = BankCredentialSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "DELETE"])
def credential_detail_delete(request, credential_id):
    credential = get_object_or_404(BankCredential, id=credential_id, user=request.user)
    if request.method == "GET":
        return Response(BankCredentialSerializer(credential).data)
    credential.is_active = False
    credential.save(update_fields=["is_active", "updated_at"])
    return Response(status=204)


@api_view(["POST"])
def credential_sync(request, credential_id):
    credential = get_object_or_404(BankCredential, id=credential_id, user=request.user, is_active=True)
    queue = get_queue("sync")
    job = queue.enqueue(sync_credential_transactions, str(credential.id))
    return Response({"job_id": job.id, "status": "queued"})
