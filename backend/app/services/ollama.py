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
        self.timeout = 120.0

    async def _generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Send generation request to Ollama API."""
        url = f"{self.base_url}/api/generate"
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
        prompt = f"""Tu es un expert en analyse de relevés bancaires français.

MISSION : Analyser ce libellé bancaire et extraire le nom propre du commerçant + catégorie.

LIBELLÉ À ANALYSER : "{raw_label}"

RÈGLES DE DÉCODAGE DES LIBELLÉS FRANÇAIS :
- "CARTE", "CB", "X7722", "X1234" = paiement par carte (à supprimer)
- "PRLV", "PRLVM", "PRELEVEMENT" = prélèvement automatique (à supprimer)
- "VIR SEPA", "VIREMENT EN VOTRE FAVEUR" = virement entrant → catégorie "income"
- "BOUCH.", "BOUCHERIE" = Boucherie
- "PHARM.", "PHIE", "PHARMACIE" = Pharmacie
- "ELECTRO." = Électronique/Multimédia
- Les codes alphanumériques (REF000..., /320690..., YYW10487...) sont des références bancaires à IGNORER
- Les noms de villes en fin de libellé (PARIS, LYON, TOULOUSE...) sont à IGNORER

CATÉGORIES AUTORISÉES : housing, transportation, food, utilities, healthcare, entertainment, shopping, subscriptions, income, insurance, education, travel, other

EXEMPLES D'ANALYSE :

1. "X7722 CANAL PLUS FR ISSY L" 
   → cleaned_label: "Canal+" | category: "subscriptions" | confidence: 0.95

2. "PRLVM SEPA NETFLIX.COM"
   → cleaned_label: "Netflix" | category: "subscriptions" | confidence: 0.98

3. "VIREMENT EN VOTRE FAVEUR PayPal Europe"
   → cleaned_label: "PayPal" | category: "income" | confidence: 0.95

4. "EUROP ASSISTANCE ITALIA SPA/REF00000000000000000000000000151219/3206903896"
   → cleaned_label: "Europ Assistance" | category: "insurance" | confidence: 0.92

5. "CARTE 05/03 CARREFOUR CITY"
   → cleaned_label: "Carrefour City" | category: "food" | confidence: 0.95

6. "X7722 LIDL"
   → cleaned_label: "Lidl" | category: "food" | confidence: 0.95

7. "PRLV SEPA FREE MOBILE"
   → cleaned_label: "Free Mobile" | category: "utilities" | confidence: 0.95

8. "VIR SEPA SALAIRE MARS 2026"
   → cleaned_label: "Salaire" | category: "income" | confidence: 0.95

9. "X7722 SHELL AUTOROUTE A6"
   → cleaned_label: "Shell" | category: "transportation" | confidence: 0.90

10. "PRLV SEPA MACIF ASSURANCES"
    → cleaned_label: "Macif" | category: "insurance" | confidence: 0.95

INSTRUCTIONS FINALES :
1. cleaned_label doit être COURT, LISIBLE, sans codes ni références
2. merchant_name = même valeur que cleaned_label généralement
3. Choisis la catégorie la plus appropriée parmi celles listées
4. confidence : 0.0 à 1.0 selon ta certitude

RÉPONDS UNIQUEMENT AVEC CE JSON (rien d'autre) :
{{"cleaned_label": "Nom", "merchant_name": "Nom", "category": "categorie", "confidence": 0.95}}"""

        response = await self._generate(prompt, temperature=0.1)
        print(f"[AI RAW RESPONSE]: {response!r}")

        # Parse JSON directement
        result = json.loads(response.strip())
        
        category = result.get("category", "other").lower().strip()
        if category not in ["housing", "transportation", "food", "utilities", "healthcare", 
                          "entertainment", "shopping", "subscriptions", "income", 
                          "insurance", "education", "travel", "other"]:
            category = "other"

        return {
            "cleaned_label": result.get("cleaned_label", raw_label).strip(),
            "merchant_name": result.get("merchant_name", result.get("cleaned_label", raw_label)).strip(),
            "category": category,
            "confidence": float(result.get("confidence", 0.5))
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
        hint = f"Commerçant identifié : {merchant_hint}\n" if merchant_hint else ""
        direction = "crédit (entrée d'argent)" if amount > 0 else "débit (dépense)"
        
        prompt = f"""Catégorise cette transaction bancaire française.

Libellé : "{label}"
Montant : {amount} EUR ({direction})
{hint}
Catégories valides : housing, transportation, food, utilities, healthcare, entertainment, shopping, subscriptions, income, insurance, education, travel, other

Règles :
- Si c'est un virement entrant (VIREMENT EN VOTRE FAVEUR, SALAIRE) → "income"
- Si c'est un remboursement avec montant positif → "income"
- Analyse le libellé pour déterminer la catégorie appropriée

Réponds UNIQUEMENT avec ce JSON :
{{
    "category": "nom_categorie",
    "reasoning": "Explication courte en français",
    "is_expense": true,
    "confidence": 0.95
}}"""

        response = await self._generate(prompt, temperature=0.2)
        result = json.loads(response.strip())
        
        return {
            "category": result.get("category", "other"),
            "reasoning": result.get("reasoning", ""),
            "is_expense": result.get("is_expense", amount < 0),
            "confidence": float(result.get("confidence", 0.5)),
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
        prompt = f"""Analyse si ces transactions forment un paiement récurrent :

Commerçant : {merchant}
Libellé : "{label}"
Montants : {amounts}
Dates : {dates}

Paiements récurrents courants : loyer, factures, abonnements (Netflix, Spotify), assurance, salaire, salle de sport, téléphone.

Analyse la régularité et le motif des dates/montants.

Réponds UNIQUEMENT en JSON :
{{
    "is_recurring": true,
    "pattern_type": "monthly",
    "confidence": 0.9,
    "reasoning": "Explication courte"
}}"""

        response = await self._generate(prompt, temperature=0.2)
        result = json.loads(response.strip())
        
        return {
            "is_recurring": result.get("is_recurring", False),
            "pattern_type": result.get("pattern_type", "unknown"),
            "confidence": float(result.get("confidence", 0.0)),
            "reasoning": result.get("reasoning", ""),
        }


# Global instance
_ollama_service: OllamaService | None = None


def get_ollama_service() -> OllamaService:
    """Get or create Ollama service singleton."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
