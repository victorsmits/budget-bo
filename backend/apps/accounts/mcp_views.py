"""
MCP OAuth 2.0 endpoints + MCP token management API.

OAuth flow (RFC 6749 + PKCE):
  POST /mcp/oauth/register   → dynamic client registration (RFC 7591)
  GET  /mcp/oauth/authorize  → redirect to frontend consent page (must be authenticated)
  POST /mcp/oauth/authorize  → approve consent, issue authorization code
  POST /mcp/oauth/token      → exchange code for access token
  POST /mcp/oauth/revoke     → revoke token

Token management (authenticated):
  GET    /users/mcp/tokens        → list tokens
  POST   /users/mcp/tokens        → create token
  PATCH  /users/mcp/tokens/{id}   → update label
  DELETE /users/mcp/tokens/{id}   → revoke token
"""

import base64
import hashlib
import urllib.parse

from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import McpOAuthClient, McpOAuthCode, McpToken
from .serializers import McpTokenSerializer, McpTokenCreateSerializer


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def mcp_tokens(request):
    if request.method == "GET":
        tokens = McpToken.objects.filter(user=request.user, is_active=True).order_by("-created_at")
        return Response(McpTokenSerializer(tokens, many=True).data)

    # POST — create
    ser = McpTokenCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    token = McpToken.generate(user=request.user, label=ser.validated_data.get("label", ""))
    return Response(
        {**McpTokenSerializer(token).data, "token": token.token},
        status=201,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def mcp_token_detail(request, token_id):
    try:
        token = McpToken.objects.get(id=token_id, user=request.user)
    except McpToken.DoesNotExist:
        return Response({"detail": "Not found."}, status=404)

    if request.method == "DELETE":
        token.is_active = False
        token.save(update_fields=["is_active"])
        return Response(status=204)

    # PATCH — update label
    label = request.data.get("label", token.label)
    token.label = label
    token.save(update_fields=["label"])
    return Response(McpTokenSerializer(token).data)


# ---------------------------------------------------------------------------
# OAuth 2.0 — Dynamic client registration (RFC 7591)
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_register(request):
    client_name = request.data.get("client_name", "")
    redirect_uris = request.data.get("redirect_uris", [])

    if not redirect_uris or not isinstance(redirect_uris, list):
        return Response({"error": "redirect_uris is required and must be a list"}, status=400)

    client = McpOAuthClient.register(client_name=client_name, redirect_uris=redirect_uris)

    return Response(
        {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "redirect_uris": client.redirect_uris,
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        status=201,
    )


# ---------------------------------------------------------------------------
# OAuth 2.0 — Authorization endpoint
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def oauth_authorize(request):
    """
    GET: check session, then redirect to frontend consent page.
    If not authenticated → redirect to login with next param.
    """
    client_id = request.GET.get("client_id", "")
    redirect_uri = request.GET.get("redirect_uri", "")
    state = request.GET.get("state", "")
    code_challenge = request.GET.get("code_challenge", "")
    code_challenge_method = request.GET.get("code_challenge_method", "S256")

    if not client_id or not redirect_uri:
        return Response({"error": "client_id and redirect_uri are required"}, status=400)

    try:
        client = McpOAuthClient.objects.get(client_id=client_id, is_active=True)
    except McpOAuthClient.DoesNotExist:
        return Response({"error": "Unknown client_id"}, status=400)

    if redirect_uri not in client.redirect_uris:
        return Response({"error": "redirect_uri not allowed for this client"}, status=400)

    frontend_url = settings.FRONTEND_URL
    consent_params = urllib.parse.urlencode({
        "client_id": client_id,
        "client_name": client.client_name,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    })
    consent_url = f"{frontend_url}/mcp/consent?{consent_params}"

    if not request.user.is_authenticated:
        login_url = f"{frontend_url}/login?next={urllib.parse.quote(consent_url, safe='')}"
        return redirect(login_url)

    return redirect(consent_url)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def oauth_approve(request):
    """
    POST: user approved consent — create authorization code.
    Called by the frontend consent page.
    """
    client_id = request.data.get("client_id", "")
    redirect_uri = request.data.get("redirect_uri", "")
    state = request.data.get("state", "")
    code_challenge = request.data.get("code_challenge", "")
    code_challenge_method = request.data.get("code_challenge_method", "S256")

    if not client_id or not redirect_uri:
        return Response({"error": "client_id and redirect_uri are required"}, status=400)

    try:
        client = McpOAuthClient.objects.get(client_id=client_id, is_active=True)
    except McpOAuthClient.DoesNotExist:
        return Response({"error": "Unknown client_id"}, status=400)

    if redirect_uri not in client.redirect_uris:
        return Response({"error": "redirect_uri not allowed"}, status=400)

    auth_code = McpOAuthCode.generate(
        client=client,
        user=request.user,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    params = {"code": auth_code.code}
    if state:
        params["state"] = state

    return Response({"redirect_uri": f"{redirect_uri}?{urllib.parse.urlencode(params)}"})


# ---------------------------------------------------------------------------
# OAuth 2.0 — Token endpoint
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_token(request):
    grant_type = request.data.get("grant_type", "")
    if grant_type != "authorization_code":
        return Response({"error": "unsupported_grant_type"}, status=400)

    code_str = request.data.get("code", "")
    redirect_uri = request.data.get("redirect_uri", "")
    client_id = request.data.get("client_id", "")
    code_verifier = request.data.get("code_verifier", "")

    if not code_str or not redirect_uri or not client_id:
        return Response({"error": "invalid_request", "error_description": "Missing required parameters"}, status=400)

    try:
        auth_code = McpOAuthCode.objects.select_related("client", "user").get(code=code_str)
    except McpOAuthCode.DoesNotExist:
        return Response({"error": "invalid_grant", "error_description": "Code not found"}, status=400)

    if auth_code.used:
        return Response({"error": "invalid_grant", "error_description": "Code already used"}, status=400)

    if auth_code.is_expired():
        return Response({"error": "invalid_grant", "error_description": "Code expired"}, status=400)

    if auth_code.client.client_id != client_id:
        return Response({"error": "invalid_client"}, status=400)

    if auth_code.redirect_uri != redirect_uri:
        return Response({"error": "invalid_grant", "error_description": "redirect_uri mismatch"}, status=400)

    # PKCE verification
    if auth_code.code_challenge:
        if not code_verifier:
            return Response({"error": "invalid_grant", "error_description": "code_verifier required"}, status=400)
        if auth_code.code_challenge_method == "S256":
            digest = hashlib.sha256(code_verifier.encode()).digest()
            expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        else:
            expected = code_verifier
        if expected != auth_code.code_challenge:
            return Response({"error": "invalid_grant", "error_description": "PKCE verification failed"}, status=400)

    # Mark code as used
    auth_code.used = True
    auth_code.save(update_fields=["used"])

    # Issue access token (McpToken)
    label = auth_code.client.client_name or auth_code.client.client_id
    mcp_token = McpToken.generate(
        user=auth_code.user,
        label=label,
        oauth_client=auth_code.client,
    )

    return Response({
        "access_token": mcp_token.token,
        "token_type": "Bearer",
        "scope": "mcp",
    })


# ---------------------------------------------------------------------------
# OAuth 2.0 — Revocation endpoint
# ---------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_revoke(request):
    token_str = request.data.get("token", "")
    if not token_str:
        return Response({"error": "token is required"}, status=400)

    McpToken.objects.filter(token=token_str).update(is_active=False)
    return Response({}, status=200)
