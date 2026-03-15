from django.urls import path
from . import views

urlpatterns = [
    path("/login", views.auth_login),
    path("/callback", views.auth_callback),
    path("/logout", views.auth_logout),
    path("/me", views.auth_me),
    path("test-login", views.auth_test_login),
]
