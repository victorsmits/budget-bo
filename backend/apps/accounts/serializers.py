from rest_framework import serializers
from .models import User, McpToken, McpOAuthClient


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "display_name", "profile_picture"]


class McpOAuthClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = McpOAuthClient
        fields = ["client_id", "client_name"]


class McpTokenSerializer(serializers.ModelSerializer):
    oauth_client = McpOAuthClientSerializer(read_only=True)

    class Meta:
        model = McpToken
        fields = ["id", "label", "is_active", "created_at", "last_used_at", "oauth_client"]
        read_only_fields = ["id", "is_active", "created_at", "last_used_at", "oauth_client"]


class McpTokenCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255, required=False, default="")
