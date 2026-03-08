"""Ollama AI service for transaction enrichment."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from app.core.config import get_settings

settings = get_settings()

ALLOWED_CATEGORIES = {
    "housing",
    "transportation",
    "food",
    "utilities",
    "healthcare",
    "entertainment",
    "shopping",
    "subscriptions",
    "income",
    "insurance",
    "education",
    "travel",
    "other",
}

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class OllamaService:
    """Service for interacting with local Ollama AI."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = float(settings.ollama_timeout)

    async def _generate(self, prompt: str, temperature: float) -> str:
        """Send generation request to Ollama API and return raw response text."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": 256,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    def _parse_json_response(self, raw_response: str, fallback: dict[str, Any]) -> dict[str, Any]:
        """Parse model JSON safely, including markdown/code-fence wrappers."""
        cleaned = raw_response.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = JSON_BLOCK_RE.search(cleaned)
            if not match:
                return fallback
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return fallback

    async def _search_web_context(self, query: str) -> str:
        """Fetch lightweight context from DuckDuckGo Instant Answer API."""
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get("https://api.duckduckgo.com/", params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return ""

        topics = []
        for item in data.get("RelatedTopics", [])[:5]:
            if "Text" in item:
                topics.append(item["Text"])
            for sub in item.get("Topics", [])[:3]:
                if "Text" in sub:
                    topics.append(sub["Text"])

        context_parts = [
            data.get("AbstractText", ""),
            data.get("Answer", ""),
            " | ".join(topics[:5]),
        ]
        return " | ".join(part for part in context_parts if part).strip()

    def _needs_web_search(self, raw_label: str, result: dict[str, Any]) -> bool:
        cleaned_label = str(result.get("cleaned_label", "")).strip().lower()
        confidence = float(result.get("confidence", 0.0))
        unknown_tokens = {"unknown", "inconnu", "other", "n/a", ""}

        return (
            confidence < 0.65
            or cleaned_label in unknown_tokens
            or len(cleaned_label) < 3
            or cleaned_label == raw_label.strip().lower()
        )

    async def normalize_label(self, raw_label: str) -> dict[str, Any]:
        """Normalize label + categorize transaction with optional web-assisted retry."""
        base_prompt = f"""Tu es un expert en analyse de relevés bancaires français.

Analyse ce libellé bancaire puis réponds UNIQUEMENT en JSON.

LIBELLÉ : \"{raw_label}\"
CATÉGORIES : {", ".join(sorted(ALLOWED_CATEGORIES))}

Règles:
- Supprime les marqueurs techniques (CB, CARTE, PRLV, PRLVM, références, ville finale).
- cleaned_label doit être court et lisible.
- merchant_name doit généralement être égal à cleaned_label.
- Si virement entrant/salaire/remboursement entrant, catégorie = income.

Format de réponse:
{{"cleaned_label":"Nom","merchant_name":"Nom","category":"food","confidence":0.91}}"""

        fallback = {
            "cleaned_label": raw_label,
            "merchant_name": raw_label,
            "category": "other",
            "confidence": 0.35,
        }

        first_pass = self._parse_json_response(
            await self._generate(base_prompt, temperature=0.1),
            fallback=fallback,
        )

        if self._needs_web_search(raw_label, first_pass):
            web_context = await self._search_web_context(raw_label)
            if web_context:
                retry_prompt = (
                    f"{base_prompt}\n\n"
                    f"Contexte web pour aider l'identification du commerçant: {web_context}\n"
                    "Réutilise ce contexte uniquement s'il est pertinent."
                )
                first_pass = self._parse_json_response(
                    await self._generate(retry_prompt, temperature=0.05),
                    fallback=first_pass,
                )

        category = str(first_pass.get("category", "other")).strip().lower()
        if category not in ALLOWED_CATEGORIES:
            category = "other"

        return {
            "cleaned_label": str(first_pass.get("cleaned_label", raw_label)).strip() or raw_label,
            "merchant_name": str(
                first_pass.get("merchant_name") or first_pass.get("cleaned_label") or raw_label
            ).strip(),
            "category": category,
            "confidence": max(0.0, min(float(first_pass.get("confidence", 0.5)), 1.0)),
        }

    async def categorize_transaction(
        self,
        label: str,
        amount: float,
        merchant_hint: str | None = None,
    ) -> dict[str, Any]:
        """Categorize a transaction based on label and context."""
        hint = f"Commerçant identifié : {merchant_hint}\n" if merchant_hint else ""
        direction = "crédit (entrée d'argent)" if amount > 0 else "débit (dépense)"

        prompt = f"""Catégorise cette transaction bancaire française.

Libellé : \"{label}\"
Montant : {amount} EUR ({direction})
{hint}
Catégories valides : {", ".join(sorted(ALLOWED_CATEGORIES))}

Réponds UNIQUEMENT en JSON :
{{"category":"food","reasoning":"Explication courte","is_expense":true,"confidence":0.95}}"""

        fallback = {
            "category": "income" if amount > 0 else "other",
            "reasoning": "Fallback automatique",
            "is_expense": amount < 0,
            "confidence": 0.4,
        }
        result = self._parse_json_response(await self._generate(prompt, temperature=0.2), fallback)

        category = str(result.get("category", "other")).strip().lower()
        if category not in ALLOWED_CATEGORIES:
            category = "other"

        return {
            "category": category,
            "reasoning": str(result.get("reasoning", "")),
            "is_expense": bool(result.get("is_expense", amount < 0)),
            "confidence": max(0.0, min(float(result.get("confidence", 0.5)), 1.0)),
        }

    async def is_recurring_pattern(
        self,
        label: str,
        merchant: str,
        amounts: list[float],
        dates: list[str],
    ) -> dict[str, Any]:
        """AI-assisted check if transactions form a recurring pattern."""
        prompt = f"""Analyse si ces transactions forment un paiement récurrent.

Commerçant : {merchant}
Libellé : \"{label}\"
Montants : {amounts}
Dates : {dates}

Réponds UNIQUEMENT en JSON :
{{"is_recurring":true,"pattern_type":"monthly","confidence":0.9,"reasoning":"Explication courte"}}"""

        fallback = {
            "is_recurring": False,
            "pattern_type": "unknown",
            "confidence": 0.0,
            "reasoning": "",
        }
        result = self._parse_json_response(await self._generate(prompt, temperature=0.2), fallback)

        return {
            "is_recurring": bool(result.get("is_recurring", False)),
            "pattern_type": str(result.get("pattern_type", "unknown")),
            "confidence": max(0.0, min(float(result.get("confidence", 0.0)), 1.0)),
            "reasoning": str(result.get("reasoning", "")),
        }


_ollama_service: OllamaService | None = None


def get_ollama_service() -> OllamaService:
    """Get or create Ollama service singleton."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
