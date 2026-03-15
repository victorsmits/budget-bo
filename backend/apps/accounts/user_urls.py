from django.urls import path
from . import views

urlpatterns = [
    path("/me", views.users_me),
]
