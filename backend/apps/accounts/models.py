import secrets
import uuid
import datetime
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    oauth_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    profile_picture = models.URLField(null=True, blank=True)
    encryption_key_salt = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class McpOAuthClient(models.Model):
    """OAuth 2.0 client registered dynamically (e.g. claude.ai)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.CharField(max_length=128, unique=True, db_index=True)
    client_name = models.CharField(max_length=255, blank=True)
    redirect_uris = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "MCP OAuth Client"

    def __str__(self):
        return f"{self.client_name or self.client_id}"

    @classmethod
    def register(cls, client_name="", redirect_uris=None):
        client_id = secrets.token_urlsafe(32)
        return cls.objects.create(
            client_id=client_id,
            client_name=client_name,
            redirect_uris=redirect_uris or [],
        )


class McpOAuthCode(models.Model):
    """Short-lived OAuth 2.0 authorization code."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=128, unique=True, db_index=True)
    client = models.ForeignKey(McpOAuthClient, on_delete=models.CASCADE, related_name="auth_codes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mcp_auth_codes")
    redirect_uri = models.URLField()
    code_challenge = models.CharField(max_length=128, blank=True)
    code_challenge_method = models.CharField(max_length=10, default="S256")
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "MCP OAuth Code"

    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def generate(cls, client, user, redirect_uri, code_challenge="", code_challenge_method="S256"):
        code = secrets.token_urlsafe(48)
        expires_at = timezone.now() + datetime.timedelta(minutes=10)
        return cls.objects.create(
            code=code,
            client=client,
            user=user,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=expires_at,
        )


class McpToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mcp_tokens")
    oauth_client = models.ForeignKey(
        McpOAuthClient, on_delete=models.SET_NULL, null=True, blank=True, related_name="tokens"
    )
    token = models.CharField(max_length=128, unique=True, db_index=True)
    label = models.CharField(max_length=255, blank=True, help_text="Optional label (e.g. 'claude.ai')")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "MCP Token"

    def __str__(self):
        return f"{self.user.email} — {self.label or 'default'}"

    @classmethod
    def generate(cls, user, label="", oauth_client=None):
        token = secrets.token_urlsafe(48)
        return cls.objects.create(user=user, token=token, label=label, oauth_client=oauth_client)
