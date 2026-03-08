"""Ollama AI service for transaction enrichment — using official ollama-python lib."""

import json
from typing import Any

import ollama

from app.core.config import get_settings
from app.services.ai_constants import VALID_CATEGORIES
from app.services.ollama_prompts import (
    build_normalization_system_prompt,
    build_normalization_user_prompt,
)

settings = get_settings()

# ---------------------------------------------------------------------------
# Tool definition exposed to the LLM
# ---------------------------------------------------------------------------

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Recherche des informations sur une entreprise ou un commerçant inconnu. "
            "À utiliser uniquement si le libellé bancaire est ambigu et que tu n'es "
            "pas sûr du nom ou de la catégorie."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La requête de recherche, ex: 'FLOA BANK entreprise service'",
                }
            },
            "required": ["query"],
        },
    },
}

# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _execute_web_search(query: str) -> str:
    """DuckDuckGo Instant Answer — sync, no API key needed."""
    import httpx
    try:
        params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        resp = httpx.get("https://api.duckduckgo.com/", params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        snippets: list[str] = []
        if data.get("AbstractText"):
            snippets.append(data["AbstractText"][:300])
        for topic in data.get("RelatedTopics", [])[:3]:
            if text := topic.get("Text", ""):
                snippets.append(text[:150])

        return " | ".join(snippets) or "Aucun résultat trouvé."
    except Exception as e:
        return f"Erreur de recherche : {e}"


def _dispatch_tool(name: str, args: dict) -> str:
    if name == "web_search":
        return _execute_web_search(args.get("query", ""))
    return "Outil inconnu."


# ---------------------------------------------------------------------------
# OllamaService — 100% synchrone, compatible Celery
# ---------------------------------------------------------------------------

class OllamaService:
    """
    Service Ollama synchrone avec tool calling natif.

    Le modèle décide seul s'il doit chercher sur internet.
    Utilise la lib officielle `ollama` (pip install ollama).

    Modèle recommandé : qwen2.5:7b  (meilleur tool calling + JSON + français)
    """

    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self.model = model or settings.ollama_model
        self.client = ollama.Client(
            host=host or settings.ollama_base_url,
            timeout=max(10, settings.ollama_timeout),
        )

    # ------------------------------------------------------------------
    # Core: agentic loop with tool calling (sync)
    # ------------------------------------------------------------------

    def _chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Agentic loop synchrone :
        1. Envoie les messages au modèle
        2. Si le modèle appelle un outil → exécute → renvoie le résultat → boucle
        3. Retourne la réponse finale en texte
        """
        options = {"temperature": temperature, "num_predict": 256}

        for _ in range(3):  # max 3 tool-call rounds to keep latency bounded
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    tools=tools or [],
                    format="json",
                    options=options,
                )
            except Exception:
                return "{}"

            message = response.message

            # Model wants to call a tool
            if message.tool_calls:
                messages.append(message)
                for tool_call in message.tool_calls:
                    result = _dispatch_tool(
                        tool_call.function.name,
                        dict(tool_call.function.arguments),
                    )
                    messages.append({"role": "tool", "content": result})
                continue  # send tool results back to model

            # Final answer
            return message.content or "{}"

        return "{}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize_label(self, raw_label: str) -> dict[str, Any]:
        """
        Normalise un libellé bancaire brut.
        Retourne : cleaned_label, merchant_name, category, confidence
        """
        messages = [
            {
                "role": "system",
                "content": build_normalization_system_prompt(),
            },
            {
                "role": "user",
                "content": build_normalization_user_prompt(raw_label),
            },
        ]

        result = _parse_json(self._chat(messages, tools=[WEB_SEARCH_TOOL]))
        return _validate_normalize(result, raw_label)

    def categorize_transaction(
        self,
        label: str,
        amount: float,
        merchant_hint: str | None = None,
    ) -> dict[str, Any]:
        """Catégorise une transaction. Retourne category, reasoning, is_expense, confidence."""
        direction = "crédit (entrée d'argent)" if amount > 0 else "débit (dépense)"
        hint = f"Commerçant identifié : {merchant_hint}\n" if merchant_hint else ""

        messages = [
            {
                "role": "system",
                "content": "Tu es un expert en analyse de relevés bancaires français. Tu réponds UNIQUEMENT en JSON valide. Si un marchand est ambigu ou peu connu, utilise web_search avant de catégoriser.",
            },
            {
                "role": "user",
                "content": f"""Catégorise cette transaction bancaire.

Libellé : "{label}"
Montant : {amount} EUR ({direction})
{hint}Catégories valides : {", ".join(sorted(VALID_CATEGORIES))}

Règles :
- "income" UNIQUEMENT si indice explicite: salaire, paie, remboursement, allocation, virement entrant
- Un montant positif seul NE SUFFIT PAS pour classer en "income"
- Supermarchés -> "groceries"
- Restaurants/snack/livraison repas -> "dining"
- Station essence / péage / transport -> "transportation"
- Bricolage / ameublement -> "home_improvement"
- Évite "shopping" si une catégorie plus précise existe
- Si le secteur d'activité n'est pas clair, utilise web_search avant de trancher

JSON attendu :
{{"category":"…","reasoning":"…","is_expense":true,"confidence":0.95}}""",
            },
        ]

        result = _parse_json(self._chat(messages, tools=[WEB_SEARCH_TOOL]))
        return {
            "category": _safe_category(result.get("category")),
            "reasoning": result.get("reasoning", ""),
            "is_expense": result.get("is_expense", amount < 0),
            "confidence": float(result.get("confidence", 0.5)),
        }

    def is_recurring_pattern(
        self,
        label: str,
        merchant: str,
        amounts: list[float],
        dates: list[str],
    ) -> dict[str, Any]:
        """Détecte si des transactions forment un pattern récurrent."""
        messages = [
            {
                "role": "system",
                "content": "Tu es un expert en analyse de relevés bancaires. Tu réponds UNIQUEMENT en JSON valide.",
            },
            {
                "role": "user",
                "content": f"""Analyse si ces transactions forment un paiement récurrent.

Commerçant : {merchant}
Libellé : "{label}"
Montants : {amounts}
Dates : {dates}

JSON attendu :
{{"is_recurring":true,"pattern_type":"monthly","confidence":0.9,"reasoning":"…"}}""",
            },
        ]

        result = _parse_json(self._chat(messages, temperature=0.2))
        return {
            "is_recurring": bool(result.get("is_recurring", False)),
            "pattern_type": result.get("pattern_type", "unknown"),
            "confidence": float(result.get("confidence", 0.0)),
            "reasoning": result.get("reasoning", ""),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(raw: str) -> dict[str, Any]:
    """Parse JSON depuis la réponse du modèle, avec fallback regex."""
    import re
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _safe_category(value: Any) -> str:
    cat = str(value or "other").lower().strip()
    return cat if cat in VALID_CATEGORIES else "other"


def _validate_normalize(result: dict, raw_label: str) -> dict[str, Any]:
    cleaned = result.get("cleaned_label", raw_label).strip()
    return {
        "cleaned_label": cleaned,
        "merchant_name": result.get("merchant_name", cleaned).strip(),
        "category": _safe_category(result.get("category")),
        "confidence": float(result.get("confidence", 0.5)),
    }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_ollama_service: OllamaService | None = None


def get_ollama_service() -> OllamaService:
    """Retourne le singleton OllamaService."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service