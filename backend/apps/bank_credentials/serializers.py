from rest_framework import serializers
from services.security import EncryptionService
from .models import BankCredential


class BankCredentialSerializer(serializers.ModelSerializer):
    login = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = BankCredential
        fields = [
            "id", "bank_name", "bank_label", "bank_website", "sync_status", "sync_error_message",
            "last_sync_at", "created_at", "updated_at", "is_active", "login", "password"
        ]
        read_only_fields = ["id", "sync_status", "sync_error_message", "last_sync_at", "created_at", "updated_at"]

    def create(self, validated_data):
        login_raw = validated_data.pop("login")
        password_raw = validated_data.pop("password")
        service = EncryptionService()
        validated_data["encrypted_login"] = service.encrypt(login_raw)
        validated_data["encrypted_password"] = service.encrypt(password_raw)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
