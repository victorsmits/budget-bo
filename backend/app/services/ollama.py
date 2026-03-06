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
        prompt = f"""I need you to clean up this bank transaction name and tell me what it is.

Original name: "{raw_label}"

Your job:
1. Remove all the weird numbers, references and bank codes
2. Keep only the actual store or company name
3. Tell me what type of expense it is

Examples:
- "CARTE 12/10 Netflix.com 9.99" becomes "Netflix" (entertainment)
- "EUROP ASSISTANCE ITALIA SPA/REF00000000000000000000000000151219/3206903896" becomes "Europ Assistance" (insurance)
- "PRLVM SEPA EDF 123456789" becomes "EDF" (utilities)

Categories you can use: housing, transportation, food, utilities, healthcare, entertainment, shopping, subscriptions, income, insurance, education, travel, other

Reply with ONLY this format:
{{"cleaned_label": "Clean Name", "merchant_name": "merchant", "category": "category", "confidence": 0.95}}"""

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
                    
                    # Nettoyer le cleaned_label
                    cleaned_label = result.get("cleaned_label", raw_label).strip()
                    
                    # Si le cleaned_label est identique au raw_label, essayer un nettoyage basique
                    if cleaned_label == raw_label:
                        # Nettoyage basique par regex
                        import re
                        # Enlever les références après /
                        cleaned_label = re.sub(r'/.*$', '', cleaned_label)
                        # Enlever les références REF
                        cleaned_label = re.sub(r'REF[\dA-Z]*', '', cleaned_label)
                        # Enlever les numéros de téléphone longs
                        cleaned_label = re.sub(r'\b\d{10,}\b', '', cleaned_label)
                        # Nettoyer les espaces multiples
                        cleaned_label = re.sub(r'\s+', ' ', cleaned_label).strip()
                        # Si c'est toujours vide, utiliser une partie du raw_label
                        if not cleaned_label:
                            # Prendre les 30 premiers caractères
                            cleaned_label = raw_label[:30].strip()
                    
                    return {
                        "cleaned_label": cleaned_label,
                        "merchant_name": result.get("merchant_name", cleaned_label),
                        "category": category,
                        "confidence": float(result.get("confidence", 0.5))
                    }
            
            # Si tout échoue, retourner une réponse par défaut
            return {
                "cleaned_label": raw_label[:30].strip(),
                "merchant_name": raw_label[:30].strip(),
                "category": "other",
                "confidence": 0.1
            }
                
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            # En cas d'erreur, faire un nettoyage basique
            import re
            cleaned_label = raw_label
            # Enlever les références après /
            cleaned_label = re.sub(r'/.*$', '', cleaned_label)
            # Enlever les références REF
            cleaned_label = re.sub(r'REF[\dA-Z]*', '', cleaned_label)
            # Enlever les numéros de téléphone longs
            cleaned_label = re.sub(r'\b\d{10,}\b', '', cleaned_label)
            # Nettoyer les espaces multiples
            cleaned_label = re.sub(r'\s+', ' ', cleaned_label).strip()
            
            if not cleaned_label:
                cleaned_label = raw_label[:30].strip()

        return {
            "cleaned_label": cleaned_label,
            "merchant_name": cleaned_label,
            "category": "other",
            "confidence": 0.1,
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
