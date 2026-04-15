from django.contrib import admin
from .models import User, McpToken, McpOAuthClient, McpOAuthCode


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "is_staff", "is_superuser", "created_at")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "display_name", "profile_picture")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(McpToken)
class McpTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "is_active", "oauth_client", "created_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("user__email", "label")
    readonly_fields = ("token", "created_at", "last_used_at")


@admin.register(McpOAuthClient)
class McpOAuthClientAdmin(admin.ModelAdmin):
    list_display = ("client_name", "client_id", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("client_name", "client_id")
    readonly_fields = ("client_id", "created_at")


@admin.register(McpOAuthCode)
class McpOAuthCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "used", "expires_at", "created_at")
    list_filter = ("used",)
    search_fields = ("user__email",)
    readonly_fields = ("code", "created_at")
