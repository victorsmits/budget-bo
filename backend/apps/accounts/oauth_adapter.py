from allauth.socialaccount.providers.google.adapter import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.conf import settings


class BudgetBoGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def get_callback_url(self, request, app):
        """
        Override callback URL to use OAUTH_BASE_URL if defined
        This fixes HTTP/HTTPS issues behind reverse proxies
        """
        callback_url = super().get_callback_url(request, app)
        
        # If OAUTH_BASE_URL is set, replace the scheme and domain
        oauth_base_url = getattr(settings, 'OAUTH_BASE_URL', '')
        if oauth_base_url:
            from urllib.parse import urlparse, urlunparse
            
            # Parse current callback URL
            parsed_callback = urlparse(callback_url)
            # Parse base URL to get scheme and netloc
            parsed_base = urlparse(oauth_base_url)
            
            # Rebuild callback URL with base scheme and netloc
            callback_url = urlunparse((
                parsed_base.scheme,  # https
                parsed_base.netloc,  # budget.victorsmits.com
                parsed_callback.path,  # /auth/social/google/login/callback/
                parsed_callback.params,
                parsed_callback.query,
                parsed_callback.fragment
            ))
        
        return callback_url


def oauth2_client_callback_url(request):
    """
    Custom callback URL function for OAuth2Client
    """
    oauth_base_url = getattr(settings, 'OAUTH_BASE_URL', '')
    if oauth_base_url:
        from urllib.parse import urljoin
        return urljoin(oauth_base_url, '/auth/social/google/login/callback/')
    return None
