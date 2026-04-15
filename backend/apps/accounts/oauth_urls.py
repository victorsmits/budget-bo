from django.urls import path
from . import mcp_views

urlpatterns = [
    path("/register", mcp_views.oauth_register),
    path("/authorize", mcp_views.oauth_authorize),
    path("/approve", mcp_views.oauth_approve),
    path("/token", mcp_views.oauth_token),
    path("/revoke", mcp_views.oauth_revoke),
]
