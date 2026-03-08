"""Prompt builders for transaction enrichment tasks."""

from app.services.ai_constants import VALID_CATEGORIES


def build_normalization_system_prompt() -> str:
    return (
        "Tu es expert en transactions bancaires FR. "
        "Objectif: retourner un nom compréhensible pour un humain (enseigne de boutique), "
        "pas la raison sociale légale. "
        "Si le commerçant n'est pas immédiatement évident, utilise l'outil web_search avant de répondre. "
        "Réponds UNIQUEMENT en JSON valide."
    )


def build_normalization_user_prompt(raw_label: str) -> str:
    categories = ", ".join(sorted(VALID_CATEGORIES))
    return f'''Analyse ce libellé bancaire et extrais: nom boutique compréhensible + catégorie métier.

LIBELLÉ : "{raw_label}"

RÈGLES CRITIQUES :
- Le `merchant_name` doit être l'enseigne connue du client (ex: "Carrefour", "IKEA", "SNCF").
- Évite les raisons sociales (SAS, SARL, HOLDING, INC...) et les prestataires de paiement.
- Si tu vois "UBER EATS" => merchant "Uber Eats" (pas "Uber BV").
- Si tu vois "AMAZON MKTPLACE" => merchant "Amazon".
- Si c'est une station-service, catégorie "transportation" (pas shopping).
- Supermarché => "groceries". Restaurant/snack/livraison repas => "dining".
- Si le commerçant ou le secteur n'est pas clairement identifiable, utilise web_search sans hésiter avant de répondre.
- Si tu ne trouves PAS de meilleur libellé compréhensible que le libellé brut, renvoie `cleaned_label` vide (""), jamais une copie du libellé initial.
- Si vraiment inconnu après recherche, utilise "shopping" ou "other" mais EN DERNIER RECOURS.

Catégories valides : {categories}

Exemples attendus:
"CB CARREFOUR CITY PARIS" -> {{"cleaned_label":"Carrefour City","merchant_name":"Carrefour City","category":"groceries","confidence":0.97}}
"CARTE UBER EATS" -> {{"cleaned_label":"Uber Eats","merchant_name":"Uber Eats","category":"dining","confidence":0.96}}
"PRLV TOTAL ENERGIES" -> {{"cleaned_label":"TotalEnergies","merchant_name":"TotalEnergies","category":"transportation","confidence":0.92}}
"CB LEROY MERLIN" -> {{"cleaned_label":"Leroy Merlin","merchant_name":"Leroy Merlin","category":"home_improvement","confidence":0.95}}

Réponds UNIQUEMENT avec ce JSON:
{{"cleaned_label":"…","merchant_name":"…","category":"…","confidence":0.95}}'''
