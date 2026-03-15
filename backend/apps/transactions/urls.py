from django.urls import path
from . import views

urlpatterns = [
    path("", views.transaction_list),
    path("enrich", views.transaction_enrich_bulk),
    path("/summary", views.transaction_summary),
    path("/<uuid:transaction_id>", views.transaction_detail_or_delete),
    path("/<uuid:transaction_id>/category", views.transaction_category_patch),
    path("/<uuid:transaction_id>/correction", views.transaction_correction_patch),
    path("/<uuid:transaction_id>/enrich", views.transaction_enrich),
    path("/<uuid:transaction_id>/recurring", views.transaction_recurring_patch),
]
