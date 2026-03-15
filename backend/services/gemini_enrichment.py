"""Gemini-based batch enrichment service with Redis-backed rate limiting."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass

import redis
from django.conf import settings
from google import genai
from google.genai import types

from services.ai_constants import VALID_CATEGORIES
from services.gemini_prompts import build_batch_prompt

logger = logging.getLogger(__name__)


class GeminiDailyLimitError(RuntimeError):
    """Raised when daily Gemini call limit has been reached."""


@dataclass
class TransactionInput:
    id: str
    raw_label: str
    amount: float
    date: str


@dataclass
class EnrichmentResult:
    id: str
    cleaned_label: str
    merchant_name: str
    category: str
    is_expense: bool
    confidence: float
    reasoning: str


class GeminiEnrichmentService:
    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.daily_limit = settings.GEMINI_DAILY_LIMIT
        self.min_delay_seconds = settings.GEMINI_MIN_DELAY_SECONDS
        self.client = genai.Client(api_key=self.api_key)
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    def enrich_batch(self, transactions: list[TransactionInput]) -> list[EnrichmentResult]:
        if not transactions:
            return []

        self._apply_rate_limit()
        prompt = build_batch_prompt(transactions)

        # Gemini SDK does not support response_mime_type="application/json" when tools are enabled.
        # We enforce JSON via prompt instructions and parse with tolerant fallback.
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )

        payload = self._parse_response_payload(response)
        return self._map_results(payload, transactions)

    def _apply_rate_limit(self) -> None:
        date_key = time.strftime("%Y-%m-%d")
        daily_key = f"gemini:daily_count:{date_key}"
        current_count = int(self.redis.get(daily_key) or 0)
        if current_count >= self.daily_limit:
            raise GeminiDailyLimitError("Gemini daily limit reached")

        last_call_raw = self.redis.get("gemini:last_call")
        if last_call_raw:
            elapsed = time.time() - float(last_call_raw)
            if elapsed < self.min_delay_seconds:
                time.sleep(self.min_delay_seconds - elapsed)

        now = time.time()
        pipe = self.redis.pipeline()
        pipe.set("gemini:last_call", now)
        pipe.incr(daily_key, 1)
        pipe.expire(daily_key, 60 * 60 * 48)
        pipe.execute()

    def _parse_response_payload(self, response: object) -> dict:
        text = getattr(response, "text", "") or ""
        if text:
            return _parse_json_object(text)

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", "")
                if part_text:
                    return _parse_json_object(part_text)

        return {}

    def _map_results(self, payload: dict, transactions: list[TransactionInput]) -> list[EnrichmentResult]:
        raw_results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(raw_results, list):
            raw_results = []

        by_index: dict[int, dict] = {}
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            idx = item.get("id")
            if isinstance(idx, int):
                by_index[idx] = item

        mapped: list[EnrichmentResult] = []
        for idx, tx in enumerate(transactions):
            mapped.append(self._build_result(tx, by_index.get(idx)))

        return mapped

    def _build_result(self, tx: TransactionInput, item: dict | None) -> EnrichmentResult:
        if not item:
            return _fallback_result(tx)

        cleaned_label = str(item.get("cleaned_label", "")).strip()
        if cleaned_label.lower() == tx.raw_label.lower().strip():
            cleaned_label = ""

        merchant_name = str(item.get("merchant_name", "")).strip()
        category = _safe_category(item.get("category"))

        confidence = _safe_confidence(item.get("confidence"))
        reasoning = str(item.get("reasoning", "")).strip()
        is_expense = bool(item.get("is_expense", tx.amount < 0))

        return EnrichmentResult(
            id=tx.id,
            cleaned_label=cleaned_label,
            merchant_name=merchant_name,
            category=category,
            is_expense=is_expense,
            confidence=confidence,
            reasoning=reasoning,
        )


def _safe_category(value: object) -> str:
    candidate = str(value or "other").strip().lower()
    if candidate not in VALID_CATEGORIES:
        return "other"
    return candidate


def _safe_confidence(value: object) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, conf))


def _fallback_result(tx: TransactionInput) -> EnrichmentResult:
    return EnrichmentResult(
        id=tx.id,
        cleaned_label="",
        merchant_name="",
        category="other",
        is_expense=tx.amount < 0,
        confidence=0.0,
        reasoning="fallback: parsing_failed",
    )


def _parse_json_object(raw: str) -> dict:
    stripped = raw.strip()
    if not stripped:
        return {}

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}
