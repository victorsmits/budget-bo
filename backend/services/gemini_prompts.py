"""Prompt builders for Gemini transaction enrichment."""

from __future__ import annotations

from services.ai_constants import VALID_CATEGORIES


def build_batch_prompt(transactions: list[object]) -> str:
    """Build a single prompt containing all transactions to enrich."""
    categories = ", ".join(sorted(VALID_CATEGORIES))
    lines: list[str] = []
    for idx, tx in enumerate(transactions):
        lines.append(
            f'[{idx}] tx_id="{getattr(tx, "id", "")}" | '
            f'raw_label="{getattr(tx, "raw_label", "")}" | '
            f'amount={getattr(tx, "amount", 0)} | '
            f'date="{getattr(tx, "date", "")}"'
        )

    tx_block = "\n".join(lines)
    return (
        "Tu es un expert en transactions bancaires françaises.\n"
        f"Analyse ces {len(transactions)} transactions et pour chacune retourne :\n"
        "cleaned_label, merchant_name, category, is_expense, confidence, reasoning.\n\n"
        "Utilise GoogleSearch pour tout commerçant ambigu ou peu connu.\n\n"
        f"Catégories valides : {categories}\n\n"
        "Règles critiques :\n"
        "- merchant_name = nom enseigne connu client (pas raison sociale légale)\n"
        "- \"income\" UNIQUEMENT si signal explicite : salaire, virement entrant, remboursement\n"
        "- groceries = supermarché ; dining = restaurant/livraison ; transportation = essence/péage\n"
        "- Si cleaned_label introuvable → renvoie \"\"  (jamais copier le libellé brut)\n"
        "- Utilise EXACTEMENT tx_id comme valeur de id dans la réponse JSON\n"
        "- Réponds UNIQUEMENT avec ce JSON, sans texte avant/après :\n\n"
        '{"results": [\n'
        '  {"id": "tx_uuid", "index": 0, "cleaned_label": "...", "merchant_name": "...", "category": "...",\n'
        '   "is_expense": true, "confidence": 0.95, "reasoning": "..."},\n'
        "  ...\n"
        "]}\n\n"
        "Transactions à analyser :\n"
        f"{tx_block}"
    )
