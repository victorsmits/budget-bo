import os
from django.conf import settings
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import UserMeSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def auth_login(request):
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        return Response({"detail": "Google OAuth is not configured"}, status=503)
    
    # En prod, on ajoute /api, en dev on ne l'ajoute pas
    base_url = "/api" if not settings.DEBUG else ""
    return redirect(f"{base_url}/auth/social/google/login/")


@api_view(["GET"])
@permission_classes([AllowAny])
def auth_callback(request):
    return redirect(settings.FRONTEND_URL)


@api_view(["POST"])
def auth_logout(request):
    logout(request)
    return Response({"status": "logged_out"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ensure_csrf_cookie
def auth_me(request):
    return Response(UserMeSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_test_login(request):
    email = request.data.get("email")
    if not email:
        return Response({"detail": "email is required"}, status=400)
    user, _ = User.objects.get_or_create(email=email, defaults={"oauth_id": f"test-{email}"})
    login(request, user)
    return Response(UserMeSerializer(user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@ensure_csrf_cookie
def users_me(request):
    return Response(UserMeSerializer(request.user).data)
