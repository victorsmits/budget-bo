from rest_framework import serializers
from .models import User


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "display_name", "profile_picture"]
