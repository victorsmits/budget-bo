from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_add_mcptoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="McpOAuthClient",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("client_id", models.CharField(db_index=True, max_length=128, unique=True)),
                ("client_name", models.CharField(blank=True, max_length=255)),
                ("redirect_uris", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "MCP OAuth Client"},
        ),
        migrations.CreateModel(
            name="McpOAuthCode",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("code", models.CharField(db_index=True, max_length=128, unique=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="auth_codes", to="accounts.mcpoauthclient")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mcp_auth_codes", to=settings.AUTH_USER_MODEL)),
                ("redirect_uri", models.URLField()),
                ("code_challenge", models.CharField(blank=True, max_length=128)),
                ("code_challenge_method", models.CharField(default="S256", max_length=10)),
                ("expires_at", models.DateTimeField()),
                ("used", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "MCP OAuth Code"},
        ),
        migrations.AddField(
            model_name="mcptoken",
            name="oauth_client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tokens",
                to="accounts.mcpoauthclient",
            ),
        ),
    ]
