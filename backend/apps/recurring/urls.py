from django.urls import path
from . import views

urlpatterns = [
    path("", views.recurring_list),
    path("upcoming", views.recurring_upcoming),
    path("detect", views.recurring_detect),
    path("stats/summary", views.recurring_summary),
    path("<uuid:recurring_id>", views.recurring_delete),
]
