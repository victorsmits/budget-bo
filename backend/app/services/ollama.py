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
                "stop": ["\n\n", "###", "---"],  # Ajout de stop tokens
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
        prompt = f"""You are a transaction classifier. Analyze this bank transaction label and extract structured information.

Raw label: "{raw_label}"

Instructions:
1. Clean common bank prefixes like "PRLVM SEPA", "VIREMENT", "CARTE", "CB", etc.
2. Extract the actual merchant name
3. Assign the most appropriate category
4. Be concise and accurate

Available categories: housing, transportation, food, utilities, healthcare, entertainment, shopping, subscriptions, income, insurance, education, travel, other

Respond ONLY with a JSON object (no extra text, no explanation):
{{"cleaned_label": "Merchant Name", "merchant_name": "merchant", "category": "category_name", "confidence": 0.95}}"""

        try:
            response = await self._generate(prompt, temperature=0.1)
            # Nettoyer la réponse pour trouver le JSON
            response = response.strip()
            
            # Si la réponse contient des backticks, extraire le JSON à l'intérieur
            if "```" in response:
                # Trouver le contenu entre les backticks
                start = response.find("```") + 3
                end = response.rfind("```")
                if start > 2 and end > start:
                    response = response[start:end].strip()
                # Enlever "json" s'il est présent après ```
                if response.startswith("json"):
                    response = response[4:].strip()
            
            # Chercher le JSON dans la réponse
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                
                # Utiliser une approche plus robuste pour extraire le JSON valide
                # Reconstruire le JSON en ne gardant que les clés valides
                import re
                
                # Chercher les paires clé-valeur valides avec regex
                pattern = r'"(\w+)"\s*:\s*"([^"]*)"'
                matches = re.findall(pattern, json_str)
                
                # Chercher aussi les valeurs numériques
                pattern_num = r'"(\w+)"\s*:\s*([\d.]+)'
                matches_num = re.findall(pattern_num, json_str)
                
                # Construire le dictionnaire
                result = {}
                for key, value in matches:
                    result[key] = value
                for key, value in matches_num:
                    try:
                        result[key] = float(value)
                    except:
                        result[key] = value
                
                # Si on a les clés requises, utiliser le résultat
                if "cleaned_label" in result or "category" in result:
                    category = result.get("category", "other").lower().strip()
                    if category not in ["housing", "transportation", "food", "utilities", "healthcare", 
                                      "entertainment", "shopping", "subscriptions", "income", 
                                      "insurance", "education", "travel", "other"]:
                        category = "other"
                    
                    return {
                        "cleaned_label": result.get("cleaned_label", raw_label).strip(),
                        "merchant_name": result.get("merchant_name", "").strip(),
                        "category": category,
                        "confidence": min(max(float(result.get("confidence", 0.5)), 0.0), 1.0),
                    }
                
                # Sinon, essayer de parser le JSON directement (peut échouer)
                try:
                    json_str = json_str.replace('\n', '').replace('\r', '')
                    json_str = json_str.replace("'", '"')
                    result = json.loads(json_str)
                    
                    category = result.get("category", "other").lower().strip()
                    if category not in ["housing", "transportation", "food", "utilities", "healthcare", 
                                      "entertainment", "shopping", "subscriptions", "income", 
                                      "insurance", "education", "travel", "other"]:
                        category = "other"
                    
                    return {
                        "cleaned_label": result.get("cleaned_label", raw_label).strip(),
                        "merchant_name": result.get("merchant_name", "").strip(),
                        "category": category,
                        "confidence": min(max(float(result.get("confidence", 0.5)), 0.0), 1.0),
                    }
                except:
                    pass
                    
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            # Ne pas essayer d'afficher 'response' si elle n'est pas définie
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
