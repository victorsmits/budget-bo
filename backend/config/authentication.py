from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session auth for API endpoints without DRF CSRF enforcement."""

    def enforce_csrf(self, request):
        return
