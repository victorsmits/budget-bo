from django.urls import path
from . import views

urlpatterns = [
    path("", views.account_list),
    path("/summary", views.account_summary),
    path("/<uuid:account_id>", views.account_detail),
]
