from rest_framework import serializers
from .models import User, McpToken


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "display_name", "profile_picture"]


class McpTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = McpToken
        fields = ["id", "label", "is_active", "created_at", "last_used_at"]
        read_only_fields = ["id", "is_active", "created_at", "last_used_at"]


class McpTokenCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255, required=False, default="")
