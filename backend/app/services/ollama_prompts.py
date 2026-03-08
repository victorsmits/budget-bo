"""Prompt builders for transaction enrichment tasks."""

from app.services.ai_constants import VALID_CATEGORIES


def build_normalization_system_prompt() -> str:
    return (
        "Tu es un moteur d'extraction strict pour les libellés bancaires FR. "
        "Ta priorité: identifier l'enseigne visible par le client, pas la raison sociale légale. "
        "Si le commerçant est ambigu, inconnu, ou potentiellement un intermédiaire de paiement, "
        "utilise web_search AVANT de conclure. "
        "IMPORTANT: réponds avec UN SEUL objet JSON valide, sans texte additionnel, sans markdown, sans balises."
    )


def build_normalization_user_prompt(raw_label: str) -> str:
    categories = ", ".join(sorted(VALID_CATEGORIES))
    return f'''Tâche: normaliser un libellé bancaire.
Retourne exactement 1 objet JSON avec les clés: cleaned_label, merchant_name, category, confidence.

Procédure (obligatoire):
1) Déduis l'enseigne la plus compréhensible pour un humain.
2) Si ambigu: fais web_search avant réponse.
3) Assigne une catégorie parmi la liste valide.
4) Évalue confidence entre 0 et 1.

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
- `cleaned_label` et `merchant_name` doivent être courts, propres, sans bruit technique (CB, PRLV, SEPA, FRXX...).
- Ne jamais inventer une enseigne précise sans indice solide.
- confidence guide: >0.90 très fiable, 0.70-0.89 plausible, <0.70 incertain.

Catégories valides : {categories}

Exemples attendus:
"CB CARREFOUR CITY PARIS" -> {{"cleaned_label":"Carrefour City","merchant_name":"Carrefour City","category":"groceries","confidence":0.97}}
"CARTE UBER EATS" -> {{"cleaned_label":"Uber Eats","merchant_name":"Uber Eats","category":"dining","confidence":0.96}}
"PRLV TOTAL ENERGIES" -> {{"cleaned_label":"TotalEnergies","merchant_name":"TotalEnergies","category":"transportation","confidence":0.92}}
"CB LEROY MERLIN" -> {{"cleaned_label":"Leroy Merlin","merchant_name":"Leroy Merlin","category":"home_improvement","confidence":0.95}}

Format de sortie strict (aucune clé supplémentaire, aucun commentaire):
{{"cleaned_label":"…","merchant_name":"…","category":"…","confidence":0.95}}'''
