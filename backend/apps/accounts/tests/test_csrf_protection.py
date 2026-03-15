from types import SimpleNamespace
from unittest.mock import patch

from django.test import Client, TestCase

from apps.accounts.models import User
from apps.bank_credentials.models import BankCredential
from apps.recurring.models import RecurringExpense
from apps.transactions.models import Transaction


class CsrfProtectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="csrf@example.com")
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

        self.credential = BankCredential.objects.create(
            user=self.user,
            bank_name="Test Bank",
            encrypted_login="enc-login",
            encrypted_password="enc-password",
        )
        self.transaction = Transaction.objects.create(
            user=self.user,
            credential=self.credential,
            date="2024-01-01",
            amount="12.50",
            raw_label="Test transaction",
            transaction_key="tx-1",
        )
        self.recurring = RecurringExpense.objects.create(
            user=self.user,
            pattern_name="Netflix",
            average_amount="15.99",
            matching_label_pattern="netflix",
            matched_transaction_count=2,
            first_seen_date="2024-01-01",
            last_seen_date="2024-02-01",
        )

    def _csrf_token(self):
        response = self.client.get("/users/me")
        self.assertEqual(response.status_code, 200)
        token = response.cookies.get("csrftoken")
        self.assertIsNotNone(token)
        return token.value

    def _call(self, method: str, path: str, *, csrf: bool, data=None):
        headers = {}
        if csrf:
            token = self._csrf_token()
            headers["HTTP_X_CSRFTOKEN"] = token

        return getattr(self.client, method.lower())(
            path,
            data=data,
            content_type="application/json",
            **headers,
        )

    def test_all_mutable_endpoints_reject_missing_csrf(self):
        tx_id = self.transaction.id
        credential_id = self.credential.id
        recurring_id = self.recurring.id

        mutable_endpoints = [
            ("post", "/auth/logout", {}),
            ("post", "/credentials", {}),
            ("delete", f"/credentials/{credential_id}", None),
            ("post", f"/credentials/{credential_id}/sync", {}),
            ("delete", f"/transactions/{tx_id}", None),
            ("patch", f"/transactions/{tx_id}/category", {"category": "food"}),
            ("patch", f"/transactions/{tx_id}/correction", {"category": "food"}),
            ("patch", f"/transactions/{tx_id}/recurring", {"is_recurring": True}),
            ("post", "/transactions/enrich", {}),
            ("post", f"/transactions/{tx_id}/enrich", {}),
            ("post", "/recurring/detect", {}),
            ("delete", f"/recurring/{recurring_id}", None),
        ]

        for method, path, payload in mutable_endpoints:
            with self.subTest(method=method, path=path):
                response = self._call(method, path, csrf=False, data=payload)
                self.assertEqual(response.status_code, 403)

    @patch("apps.recurring.views.get_queue")
    @patch("apps.transactions.views.get_queue")
    @patch("apps.bank_credentials.views.get_queue")
    def test_all_mutable_endpoints_accept_valid_csrf(
        self,
        bank_get_queue,
        transactions_get_queue,
        recurring_get_queue,
    ):
        fake_queue = SimpleNamespace(enqueue=lambda *args, **kwargs: SimpleNamespace(id="job-1"))
        bank_get_queue.return_value = fake_queue
        transactions_get_queue.return_value = fake_queue
        recurring_get_queue.return_value = fake_queue

        tx_id = self.transaction.id
        credential_id = self.credential.id
        recurring_id = self.recurring.id

        mutable_endpoints = [
            ("post", "/auth/logout", {}),
            (
                "post",
                "/credentials",
                {
                    "bank_name": "Another bank",
                    "login": "login",
                    "password": "password",
                },
            ),
            ("delete", f"/credentials/{credential_id}", None),
            ("post", f"/credentials/{credential_id}/sync", {}),
            ("delete", f"/transactions/{tx_id}", None),
            ("patch", f"/transactions/{tx_id}/category", {"category": "food"}),
            ("patch", f"/transactions/{tx_id}/correction", {"category": "food"}),
            ("patch", f"/transactions/{tx_id}/recurring", {"is_recurring": True}),
            ("post", "/transactions/enrich", {}),
            ("post", f"/transactions/{tx_id}/enrich", {}),
            ("post", "/recurring/detect", {}),
            ("delete", f"/recurring/{recurring_id}", None),
        ]

        for method, path, payload in mutable_endpoints:
            with self.subTest(method=method, path=path):
                response = self._call(method, path, csrf=True, data=payload)
                self.assertNotEqual(response.status_code, 403)


class PublicLoginCsrfTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_public_mutable_endpoint_requires_csrf(self):
        response = self.client.post("/authtest-login", data={"email": "foo@example.com"}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_public_mutable_endpoint_accepts_csrf(self):
        token = "a" * 32
        self.client.cookies["csrftoken"] = token
        response = self.client.post(
            "/authtest-login",
            data={"email": "foo@example.com"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertNotEqual(response.status_code, 403)
