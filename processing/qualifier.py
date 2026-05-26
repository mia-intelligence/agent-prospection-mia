"""
Qualification des leads via Claude API.
Score chaque prospect et génère un email personnalisé depuis un problème concret.
"""

import json
import logging
import anthropic
from config import ANTHROPIC_API_KEY, MIN_SCORE_TO_CONTACT, CALENDLY_LINK, MIA_NAME

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Tu es un expert en développement commercial pour MIA — Médiation Intelligence Appliquée.
MIA aide les TPE, artisans et commerçants à gagner du temps et de l'argent grâce à des outils adaptés à leur activité.

Laetitia de MIA propose deux types d'audit payants :
- Demi-journée d'audit (350€ HT) : pour les petites structures (artisans seuls, 1-5 personnes)
- Journée complète d'audit (850€ HT) : pour les structures plus grandes (5-50 personnes)

Le premier contact vise UNIQUEMENT à décrocher un RDV découverte de 30 minutes (gratuit, via Calendly).
Ce RDV permet à Laetitia de se présenter, comprendre l'activité, et proposer l'audit adapté.
NE PAS mentionner de prix dans les emails de prospection.

Règles absolues pour la rédaction :
1. JAMAIS de jargon technique : pas de "IA", "LLM", "automatisation", "algorithme", "digital"
2. Toujours partir d'UN problème concret du quotidien de ce secteur (devis, planning, relances, admin, stocks...)
3. Ton chaleureux, direct, terrain — comme un message d'une vraie personne, pas d'un commercial
4. Court : email de prospection = max 100 mots corps
5. Appel à l'action unique : un RDV de 30 minutes, lien Calendly en bas

Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans explication."""


def qualify_and_personalize(lead: dict) -> dict:
    """
    Envoie le lead à Claude pour scoring + génération email personnalisé.
    Retourne le lead enrichi avec score, email_subject, email_body, linkedin_message.
    """
    lead_summary = _format_lead_for_claude(lead)

    prompt = f"""Voici un prospect pour MIA :
{lead_summary}

Tu dois :
1. Scorer ce prospect de 1 à 10 (10 = parfait candidat pour un audit)
   - Critères : TPE/indépendant, secteur avec beaucoup de tâches répétitives (admin, devis, relances, planning), pas de grand groupe
   - Score < 7 = ne pas contacter
2. Estimer la taille de l'entreprise : "petite" (1-5 pers.) ou "moyenne" (5-50 pers.)
   - Petite → audit recommandé : demi-journée (350€)
   - Moyenne → audit recommandé : journée complète (850€)
3. Identifier UN problème concret quotidien typique de leur secteur (ex: pour un plombier → "les devis refaits à la main à chaque intervention")
4. Écrire l'email de prospection :
   - Max 100 mots
   - Prénom si disponible, sinon "Bonjour"
   - Accroche sur le problème concret, PAS de mention de prix ni de "IA"
   - CTA : proposer 30 min d'échange, lien Calendly [CALENDLY]
5. Écrire le message LinkedIn (max 50 mots, humain, pas de pitch commercial)

Réponds en JSON avec cette structure exacte :
{{
  "score": 8,
  "score_reason": "Artisan indépendant, beaucoup de devis manuels et relances clients",
  "company_size": "petite",
  "recommended_audit": "demi-journée",
  "recommended_price": 350,
  "pain_point": "les devis refaits à la main à chaque intervention",
  "email_subject": "Votre sujet ici",
  "email_body": "Corps de l'email ici... [CALENDLY]",
  "linkedin_message": "Message LinkedIn court ici..."
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        # Nettoyer si Claude a ajouté des backticks
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        score = int(result.get("score", 0))

        # Injecter le lien Calendly dans l'email
        email_body = result.get("email_body", "")
        if "[CALENDLY]" in email_body:
            email_body = email_body.replace("[CALENDLY]", CALENDLY_LINK)
        elif CALENDLY_LINK not in email_body:
            email_body += f"\n\n30 minutes suffisent : {CALENDLY_LINK}"

        lead.update({
            "qualification_score": score,
            "score_reason": result.get("score_reason", ""),
            "company_size": result.get("company_size", "petite"),
            "recommended_audit": result.get("recommended_audit", "demi-journée"),
            "recommended_price": result.get("recommended_price", 350),
            "pain_point": result.get("pain_point", ""),
            "email_subject": result.get("email_subject", ""),
            "email_body": email_body,
            "linkedin_message": result.get("linkedin_message", ""),
            "qualified": score >= MIN_SCORE_TO_CONTACT,
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON invalide de Claude pour {lead.get('company_name')}: {e}")
        lead["qualified"] = False
        lead["qualification_score"] = 0
    except Exception as e:
        logger.error(f"Erreur qualification [{lead.get('company_name')}]: {e}")
        lead["qualified"] = False
        lead["qualification_score"] = 0

    return lead


def _format_lead_for_claude(lead: dict) -> str:
    parts = []
    if lead.get("company_name"):
        parts.append(f"Entreprise : {lead['company_name']}")
    if lead.get("sector"):
        parts.append(f"Secteur : {lead['sector']}")
    if lead.get("contact_first_name"):
        name = lead["contact_first_name"]
        if lead.get("contact_last_name"):
            name += f" {lead['contact_last_name']}"
        parts.append(f"Contact : {name}")
    if lead.get("title"):
        parts.append(f"Poste : {lead['title']}")
    if lead.get("address"):
        parts.append(f"Localisation : {lead['address']}")
    if lead.get("website"):
        parts.append(f"Site web : {lead['website']}")
    if lead.get("employees_count"):
        parts.append(f"Taille : ~{lead['employees_count']} salariés")
    if lead.get("reviews_count"):
        parts.append(f"Avis Google : {lead['reviews_count']} (note {lead.get('rating', '?')}/5)")
    return "\n".join(parts)
