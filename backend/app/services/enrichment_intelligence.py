"""Rule-based helpers to improve merchant naming and category quality."""

from __future__ import annotations

import re

from app.services.ai_constants import VALID_CATEGORIES

LEGAL_SUFFIXES = {
    "sas",
    "sasu",
    "sarl",
    "sa",
    "eurl",
    "eirl",
    "inc",
    "llc",
    "ltd",
    "gmbh",
    "bv",
    "plc",
    "holding",
}

INCOME_KEYWORDS = (
    "salaire",
    "paie",
    "payroll",
    "remboursement",
    "refund",
    "virement entrant",
    "versement",
    "allocation",
    "caf",
    "pole emploi",
    "indemn",
)

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "groceries": ("carrefour", "auchan", "intermarche", "monoprix", "casino", "lidl", "aldi", "u express"),
    "dining": ("restaurant", "brasserie", "boulangerie", "snack", "pizza", "uber eats", "deliveroo", "mcdonald", "kfc"),
    "transportation": ("sncf", "ratp", "uber", "bolt", "blablacar", "essence", "total", "bp", "shell", "péage"),
    "utilities": ("edf", "engie", "veolia", "suez", "eau", "electricite", "gaz", "orange", "sfr", "free mobile"),
    "subscriptions": ("netflix", "spotify", "canal", "prime", "disney", "apple.com/bill", "youtube"),
    "healthcare": ("pharmacie", "doctolib", "hopital", "medecin", "laboratoire", "dentiste", "mutuelle"),
    "travel": ("air france", "ryanair", "booking", "airbnb", "trainline", "hotel", "voyage"),
    "home_improvement": ("leroy merlin", "castorama", "brico", "ikea", "mr bricolage"),
    "insurance": ("assurance", "axa", "maif", "macif", "allianz", "generali"),
    "education": ("ecole", "universite", "formation", "udemy", "coursera"),
    "income": INCOME_KEYWORDS,
}


def _clean_tokens(value: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s&+.-]", " ", value.lower())
    return [token for token in cleaned.split() if token]


def normalize_consumer_merchant(merchant_name: str | None, cleaned_label: str, raw_label: str) -> str:
    """Prefer a consumer-facing brand over legal company suffixes."""
    source = merchant_name or cleaned_label or raw_label
    tokens = _clean_tokens(source)

    compact = [token for token in tokens if token not in LEGAL_SUFFIXES and len(token) > 1]
    if not compact:
        compact = _clean_tokens(cleaned_label or raw_label)

    pretty = " ".join(compact[:4]).strip()
    if not pretty:
        return (cleaned_label or raw_label).strip()

    return pretty.title()


def has_explicit_income_signal(label: str, merchant: str) -> bool:
    """Return True only when text strongly indicates a real income transaction."""
    corpus = f"{label} {merchant}".lower()
    return any(keyword in corpus for keyword in INCOME_KEYWORDS)


def infer_category_from_text(label: str, merchant: str, amount: float) -> str | None:
    """Infer category from merchant/label with deterministic sector hints."""
    del amount
    corpus = f"{label} {merchant}".lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in corpus for keyword in keywords):
            if category in VALID_CATEGORIES:
                return category

    return None
