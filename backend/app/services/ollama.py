"""Ollama AI service for transaction enrichment."""

import json
from typing import Any

import httpx
from app.core.config import get_settings

settings = get_settings()


class OllamaService:
    """
    Service for interacting with local Ollama AI.
    
    Used to:
    - Normalize transaction labels (e.g., "PRLVM SEPA NETFLIX" -> "Netflix")
    - Categorize transactions
    - Search unknown merchants via DuckDuckGo if needed
    """

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        """Initialize Ollama service."""
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = 30.0

    async def _generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Send generation request to Ollama API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 150,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def normalize_label(self, raw_label: str) -> dict[str, Any]:
        """
        Normalize a transaction label using AI.
        
        Returns:
            Dict with:
            - cleaned_label: Normalized merchant name
            - merchant_name: Extracted merchant
            - category: Suggested category
            - confidence: 0.0 to 1.0
        """
        prompt = f"""Analyze this bank transaction label and extract structured information.

Raw label: "{raw_label}"

Respond with ONLY a JSON object in this exact format:
{{
    "cleaned_label": "Human-readable merchant name",
    "merchant_name": "Short merchant name",
    "category": "One of: housing, transportation, food, utilities, healthcare, entertainment, shopping, subscriptions, income, insurance, education, travel, other",
    "confidence": 0.95
}}

Rules:
- Clean common bank prefixes like "PRLVM SEPA", "VIREMENT", "CARTE", etc.
- Extract the actual merchant name
- Infer category from merchant type
- Confidence should reflect certainty (0.5-1.0)

JSON response:"""

        try:
            response = await self._generate(prompt, temperature=0.3)
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return {
                    "cleaned_label": result.get("cleaned_label", raw_label),
                    "merchant_name": result.get("merchant_name", ""),
                    "category": result.get("category", "other"),
                    "confidence": float(result.get("confidence", 0.5)),
                }
        except Exception:
            pass

        return {
            "cleaned_label": raw_label,
            "merchant_name": "",
            "category": "other",
            "confidence": 0.0,
        }

    async def categorize_transaction(
        self,
        label: str,
        amount: float,
        merchant_hint: str | None = None,
    ) -> dict[str, Any]:
        """
        Categorize a transaction based on label and context.
        
        Returns:
            Dict with category and reasoning
        """
        hint = f"Merchant: {merchant_hint}\n" if merchant_hint else ""
        prompt = f"""Categorize this financial transaction:

Label: "{label}"
Amount: {amount} EUR
{hint}
Categories: housing, transportation, food, utilities, healthcare, entertainment, shopping, subscriptions, income, insurance, education, travel, other

Respond with ONLY JSON:
{{
    "category": "category_name",
    "reasoning": "Brief explanation",
    "is_expense": true/false,
    "confidence": 0.95
}}

JSON:"""

        try:
            response = await self._generate(prompt, temperature=0.2)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return {
                    "category": result.get("category", "other"),
                    "reasoning": result.get("reasoning", ""),
                    "is_expense": result.get("is_expense", amount < 0),
                    "confidence": float(result.get("confidence", 0.5)),
                }
        except Exception:
            pass

        return {
            "category": "other",
            "reasoning": "",
            "is_expense": amount < 0,
            "confidence": 0.0,
        }

    async def is_recurring_pattern(
        self,
        label: str,
        merchant: str,
        amounts: list[float],
        dates: list[str],
    ) -> dict[str, Any]:
        """
        AI-assisted check if transactions form a recurring pattern.
        
        Complements the algorithmic detection with LLM reasoning.
        """
        prompt = f"""Analyze if these transactions form a recurring payment pattern:

Merchant: {merchant}
Label pattern: "{label}"
Amounts: {amounts}
Dates: {dates}

Common recurring payments: rent, utilities, subscriptions (Netflix, Spotify), insurance, salary, gym, phone bills.

Respond with ONLY JSON:
{{
    "is_recurring": true/false,
    "pattern_type": "monthly/weekly/quarterly/annual/unknown",
    "confidence": 0.9,
    "reasoning": "Brief explanation"
}}

JSON:"""

        try:
            response = await self._generate(prompt, temperature=0.2)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except Exception:
            pass

        return {
            "is_recurring": False,
            "pattern_type": "unknown",
            "confidence": 0.0,
            "reasoning": "",
        }


# Global instance
_ollama_service: OllamaService | None = None


def get_ollama_service() -> OllamaService:
    """Get or create Ollama service singleton."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
