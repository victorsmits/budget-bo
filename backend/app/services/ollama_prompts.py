"""Prompt builders for transaction enrichment tasks."""

from app.services.ai_constants import VALID_CATEGORIES


def build_normalization_system_prompt() -> str:
    return (
        "Tu es expert en transactions bancaires FR. "
        "Objectif: retourner un nom compréhensible pour un humain "
        "(enseigne de boutique), pas la raison sociale légale. "
        "Si le commerçant n'est pas immédiatement évident, "
        "utilise l'outil web_search avant de répondre. "
        "Réponds UNIQUEMENT en JSON valide."
    )


def build_normalization_user_prompt(raw_label: str) -> str:
    categories = ", ".join(sorted(VALID_CATEGORIES))
    return f"""Analyse ce libellé bancaire et extrais:
nom boutique compréhensible + catégorie métier.

LIBELLÉ : \"{raw_label}\"

RÈGLES CRITIQUES :
- Le `merchant_name` doit être l'enseigne connue du client
  (ex: \"Carrefour\", \"IKEA\", \"SNCF\").
- Évite les raisons sociales (SAS, SARL, HOLDING, INC...)
  et les prestataires de paiement.
- Si le libellé semble technique/opaque (codes terminaux,
  suites de majuscules), fais une web_search.
- Si tu identifies une ville (TOUL, TOULOUSE, PARIS...),
  ajoute-la dans ta requête web_search.
- Si tu n'as pas fait de recherche sur un cas ambigu,
  ta réponse est considérée incomplète.
- Si tu vois \"UBER EATS\" => merchant \"Uber Eats\"
  (pas \"Uber BV\").
- Si tu vois \"AMAZON MKTPLACE\" => merchant \"Amazon\".
- Si c'est une station-service,
  catégorie \"transportation\" (pas shopping).
- Supermarché => \"groceries\".
  Restaurant/snack/livraison repas => \"dining\".
- Si le commerçant ou le secteur n'est pas clairement
  identifiable, utilise web_search avant de répondre.
- Si tu ne trouves PAS de meilleur libellé compréhensible,
  renvoie `cleaned_label` vide (\"\").
- Si vraiment inconnu après recherche,
  utilise \"shopping\" ou \"other\" en dernier recours.

Catégories valides : {categories}

Réponds UNIQUEMENT avec ce JSON:
{{\"cleaned_label\":\"…\",\"merchant_name\":\"…\",\"category\":\"…\",\"confidence\":0.95}}"""


def build_public_merchant_resolution_prompt(raw_label: str, current_merchant: str) -> str:
    return f"""Trouve l'enseigne publique réelle derrière ce libellé bancaire opaque.

LIBELLÉ BRUT: \"{raw_label}\"
MARCHAND ACTUEL (potentiellement technique): \"{current_merchant}\"

Consignes:
- Utilise web_search en priorité avec des variantes
  de requêtes incluant la ville détectée.
- Cherche une enseigne publique connue des clients
  (bar, snack, restaurant, boutique, etc.).
- Ne renvoie JAMAIS un nom juridique s'il existe
  un nom commercial.
- Si aucune preuve claire, renvoie merchant_name vide
  et confidence basse.

JSON attendu:
{{\"merchant_name\":\"…\",\"cleaned_label\":\"…\",\"category\":\"…\",\"confidence\":0.0,\"reasoning\":\"…\"}}"""
