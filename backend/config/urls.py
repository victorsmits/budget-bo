from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.conf.urls.static import static
import redis
import os

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def live(request):
    return JsonResponse({"status": "live"})


def health(request):
    return JsonResponse({"status": "ok"})


def ready(request):
    db_ok = True
    redis_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False
    try:
        redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0")).ping()
    except Exception:
        redis_ok = False
    status = 200 if db_ok and redis_ok else 503
    return JsonResponse({"status": "ready" if status == 200 else "not_ready", "db": db_ok, "redis": redis_ok}, status=status)


urlpatterns = [
    path("admin/rq/", include("django_rq.urls")),
    path("admin/", admin.site.urls),
    path("auth", include("apps.accounts.urls")),
    path("credentials", include("apps.bank_credentials.urls")),
    path("transactions", include("apps.transactions.urls")),
    path("recurring", include("apps.recurring.urls")),
    path("accounts", include("apps.bank_credentials.accounts_api_urls")),
    path("auth/social/", include("allauth.urls")),
    path("users", include("apps.accounts.user_urls")),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("health", health),
    path("live", live),
    path("ready", ready),
]

# Serve static files in production
if settings.DEBUG or getattr(settings, 'STATICFILES_STORAGE', None) == 'django.contrib.staticfiles.storage.StaticFilesStorage':
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
