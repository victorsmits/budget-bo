from app.services.enrichment_pipeline import run_enrichment_pipeline


class FakeOllamaService:
    def __init__(self, normalization: dict, categorization: dict | None = None):
        self._normalization = normalization
        self._categorization = categorization or {}
        self.categorize_calls = 0

    def normalize_label(self, raw_label: str) -> dict:
        return self._normalization

    def categorize_transaction(
        self,
        label: str,
        amount: float,
        merchant_hint: str | None = None,
    ) -> dict:
        self.categorize_calls += 1
        return self._categorization


def test_pipeline_prefers_heuristic_when_clear_keyword_match() -> None:
    service = FakeOllamaService(
        normalization={
            "cleaned_label": "Carrefour City",
            "merchant_name": "Carrefour City",
            "category": "shopping",
            "confidence": 0.72,
        }
    )

    result = run_enrichment_pipeline(
        raw_label="CB CARREFOUR CITY PARIS",
        signed_amount=-52.10,
        initial_is_expense=True,
        ollama_service=service,  # type: ignore[arg-type]
    )

    assert result.category.value == "groceries"
    assert service.categorize_calls == 0
    assert result.confidence > 0.6


def test_pipeline_blocks_income_without_explicit_signal() -> None:
    service = FakeOllamaService(
        normalization={
            "cleaned_label": "Virement",
            "merchant_name": "Acme",
            "category": "income",
            "confidence": 0.9,
        },
        categorization={
            "category": "income",
            "is_expense": False,
            "confidence": 0.8,
            "reasoning": "positive amount",
        },
    )

    result = run_enrichment_pipeline(
        raw_label="VIR ACME 1234",
        signed_amount=120.00,
        initial_is_expense=False,
        ollama_service=service,  # type: ignore[arg-type]
    )

    assert result.category.value != "income"
    assert result.category.value in {"other", "shopping"}


def test_pipeline_triggers_second_pass_when_ambiguous() -> None:
    service = FakeOllamaService(
        normalization={
            "cleaned_label": "",
            "merchant_name": "PAYMENT XYZ",
            "category": "other",
            "confidence": 0.3,
        },
        categorization={
            "category": "subscriptions",
            "is_expense": True,
            "confidence": 0.91,
            "reasoning": "merchant matches SaaS billing",
        },
    )

    result = run_enrichment_pipeline(
        raw_label="CB PAYMENT XYZ",
        signed_amount=-9.99,
        initial_is_expense=True,
        ollama_service=service,  # type: ignore[arg-type]
    )

    assert service.categorize_calls == 1
    assert result.category.value == "subscriptions"
    assert "llm_categorization" in result.reasoning
