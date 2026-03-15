from django.urls import path
from . import views

urlpatterns = [
    path("", views.credential_list_create),
    path("<uuid:credential_id>", views.credential_detail_delete),
    path("<uuid:credential_id>/sync", views.credential_sync),
]
