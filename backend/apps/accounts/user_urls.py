from django.urls import path
from . import views, mcp_views

urlpatterns = [
    path("/me", views.users_me),
    path("/mcp/tokens", mcp_views.mcp_tokens),
    path("/mcp/tokens/<uuid:token_id>", mcp_views.mcp_token_detail),
]
