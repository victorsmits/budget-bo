from django.urls import path
from . import views

urlpatterns = [
    path("", views.transaction_list),
    path("/enrich", views.transaction_enrich_bulk),
    path("/summary", views.transaction_summary),
    path("/analytics/timeseries", views.transaction_analytics_timeseries),
    path("/analytics/grouped", views.transaction_analytics_grouped),
    path("/analytics/compare", views.transaction_analytics_compare),
    path("/analytics/top", views.transaction_analytics_top),
    path("/analytics/anomalies", views.transaction_analytics_anomalies),
    path("/analytics/query", views.transaction_analytics_query),
    path("/<uuid:transaction_id>", views.transaction_detail_or_delete),
    path("/<uuid:transaction_id>/category", views.transaction_category_patch),
    path("/<uuid:transaction_id>/correction", views.transaction_correction_patch),
    path("/<uuid:transaction_id>/enrich", views.transaction_enrich),
    path("/<uuid:transaction_id>/recurring", views.transaction_recurring_patch),
]
