from app.services.enrichment_pipeline import run_enrichment_pipeline


class FakeOllamaService:
    def __init__(
        self,
        normalization: dict,
        categorization: dict | None = None,
        resolution: dict | None = None,
    ):
        self._normalization = normalization
        self._categorization = categorization or {}
        self._resolution = resolution or {}
        self.categorize_calls = 0
        self.resolve_calls = 0

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

    def resolve_public_merchant(self, raw_label: str, current_merchant: str) -> dict:
        self.resolve_calls += 1
        return self._resolution


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
    assert service.resolve_calls == 0
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


def test_pipeline_uses_llm_public_resolution_for_opaque_labels() -> None:
    service = FakeOllamaService(
        normalization={
            "cleaned_label": "",
            "merchant_name": "Arcadya Garonne Toul",
            "category": "shopping",
            "confidence": 0.8,
        },
        resolution={
            "merchant_name": "Esprit Toulousain",
            "cleaned_label": "Esprit Toulousain",
            "category": "drinking",
            "confidence": 0.72,
            "reasoning": "search evidence found for local bar",
        },
    )

    result = run_enrichment_pipeline(
        raw_label="X7722 ARCADYA GARONNE TOUL",
        signed_amount=-21.90,
        initial_is_expense=True,
        ollama_service=service,  # type: ignore[arg-type]
    )

    assert service.resolve_calls == 1
    assert result.cleaned_label == "Esprit Toulousain"
    assert result.category.value == "drinking"


def test_pipeline_keeps_low_confidence_when_resolution_fails() -> None:
    service = FakeOllamaService(
        normalization={
            "cleaned_label": "",
            "merchant_name": "Ligimida",
            "category": "shopping",
            "confidence": 0.95,
        },
        resolution={
            "merchant_name": "",
            "cleaned_label": "",
            "category": "other",
            "confidence": 0.2,
            "reasoning": "insufficient evidence",
        },
    )

    result = run_enrichment_pipeline(
        raw_label="X7722 LIGIMIDA TOULOUSE",
        signed_amount=-10.5,
        initial_is_expense=True,
        ollama_service=service,  # type: ignore[arg-type]
    )

    assert service.resolve_calls == 1
    assert result.confidence < 0.8
