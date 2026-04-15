from django.core.management.base import BaseCommand
from apps.accounts.models import User, McpToken


class Command(BaseCommand):
    help = "Manage MCP tokens (create, list, revoke)"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action")

        create = sub.add_parser("create", help="Create a token for a user")
        create.add_argument("email", help="User email")
        create.add_argument("--label", default="", help="Optional label")

        sub.add_parser("list", help="List all active tokens")

        revoke = sub.add_parser("revoke", help="Revoke a token")
        revoke.add_argument("token", help="Token string to revoke")

    def handle(self, *args, **options):
        action = options.get("action")

        if action == "create":
            self._create(options["email"], options.get("label", ""))
        elif action == "list":
            self._list()
        elif action == "revoke":
            self._revoke(options["token"])
        else:
            self.stderr.write("Usage: manage.py mcp_tokens {create,list,revoke}")

    def _create(self, email, label):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User not found: {email}"))
            return

        mcp_token = McpToken.generate(user, label=label)
        self.stdout.write(self.style.SUCCESS(f"\nToken created for {email}:\n"))
        self.stdout.write(f"  {mcp_token.token}\n")
        self.stdout.write(f"\nUse this as authorization_token on claude.ai.\n")

    def _list(self):
        tokens = McpToken.objects.filter(is_active=True).select_related("user").order_by("user__email")
        if not tokens:
            self.stdout.write("No active MCP tokens.")
            return

        self.stdout.write(f"{'Email':<35} {'Label':<20} {'Created':<20} {'Last used':<20}")
        self.stdout.write("-" * 95)
        for t in tokens:
            last = t.last_used_at.strftime("%Y-%m-%d %H:%M") if t.last_used_at else "never"
            self.stdout.write(
                f"{t.user.email:<35} {(t.label or '-'):<20} "
                f"{t.created_at.strftime('%Y-%m-%d %H:%M'):<20} {last:<20}"
            )

    def _revoke(self, token_str):
        try:
            t = McpToken.objects.get(token=token_str, is_active=True)
        except McpToken.DoesNotExist:
            self.stderr.write(self.style.ERROR("Token not found or already revoked."))
            return

        t.is_active = False
        t.save(update_fields=["is_active"])
        self.stdout.write(self.style.SUCCESS(f"Token revoked for {t.user.email}."))
