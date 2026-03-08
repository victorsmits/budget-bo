"""Prompt builders for transaction enrichment tasks."""

from app.services.ai_constants import VALID_CATEGORIES


def build_normalization_system_prompt() -> str:
    return (
        "Tu es un expert en analyse de relevés bancaires français. "
        "Tu réponds UNIQUEMENT en JSON valide. "
        "Si tu ne reconnais pas le commerçant, utilise l'outil web_search."
    )


def build_normalization_user_prompt(raw_label: str) -> str:
    categories = ", ".join(sorted(VALID_CATEGORIES))
    return f'''Analyse ce libellé bancaire et extrais le nom du commerçant + catégorie.

LIBELLÉ : "{raw_label}"

RÈGLES :
- Supprimer : CARTE, CB, PRLV, PRLVM, PRELEVEMENT, SEPA, VIR, codes X1234, refs /REF…
- Supprimer les villes en fin de libellé (PARIS, LYON…)
- "BOUCH."→Boucherie | "PHARM."→Pharmacie | "ELECTRO."→Électronique
- Virement entrant / SALAIRE → category "income"
- Si tu ne reconnais pas le commerçant → utilise web_search avant de répondre

Catégories valides : {categories}

Exemples :
"PRLVM SEPA NETFLIX.COM"   → {{"cleaned_label":"Netflix","merchant_name":"Netflix","category":"subscriptions","confidence":0.98}}
"X7722 CANAL PLUS FR ISSY" → {{"cleaned_label":"Canal+","merchant_name":"Canal+","category":"subscriptions","confidence":0.95}}
"CARTE 05/03 CARREFOUR"    → {{"cleaned_label":"Carrefour","merchant_name":"Carrefour","category":"food","confidence":0.95}}
"VIR SEPA SALAIRE MARS"    → {{"cleaned_label":"Salaire","merchant_name":"Salaire","category":"income","confidence":0.97}}

Réponds UNIQUEMENT avec ce JSON :
{{"cleaned_label":"…","merchant_name":"…","category":"…","confidence":0.95}}'''
