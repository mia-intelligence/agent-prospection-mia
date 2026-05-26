"""
Envoi d'emails via Brevo (ex-SendinBlue).
Gère : email initial, relance J+3, offre finale J+7.
"""

import requests
import logging
from datetime import date
from config import BREVO_API_KEY, MIA_EMAIL, MIA_NAME, CALENDLY_LINK

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "api-key": BREVO_API_KEY,
}

SIGNATURE = f"""
---
{MIA_NAME}
MIA — Médiation Intelligence Appliquée
contact@mia-intelligence.com | 06 17 81 33 05
mia-intelligence.com
"""


def send_initial_email(lead: dict) -> bool:
    """Envoie l'email de prospection initial généré par Claude."""
    to_email = lead.get("contact_email")
    if not to_email:
        logger.warning(f"Pas d'email pour {lead.get('company_name')} — email ignoré")
        return False

    to_name = _get_display_name(lead)
    subject = lead.get("email_subject", f"Un truc que j'ai remarqué sur votre activité")
    body = lead.get("email_body", "") + SIGNATURE

    return _send(to_email, to_name, subject, body)


def send_followup_email(lead: dict, record_id: str) -> bool:
    """Relance J+3 : cas concret d'un professionnel du même secteur."""
    to_email = lead["fields"].get("Email")
    if not to_email:
        return False

    first_name = lead["fields"].get("Prénom", "")
    company = lead["fields"].get("Entreprise", "votre activité")
    pain_point = lead["fields"].get("Pain point", "les tâches répétitives")
    sector = lead["fields"].get("Secteur", "votre secteur")

    greeting = f"Bonjour {first_name}" if first_name else "Bonjour"

    body = f"""{greeting},

Je me permets de revenir rapidement.

Cette semaine j'ai passé une journée avec un professionnel du même secteur que vous. Il perdait beaucoup de temps sur {pain_point}. Ensemble on a trouvé comment récupérer ce temps.

Est-ce que ça vous parle pour {company} ?

Un échange de 30 minutes, sans engagement : {CALENDLY_LINK}

Bonne journée,{SIGNATURE}"""

    subject = f"Re: {lead['fields'].get('Sujet email', 'Votre activité')}"
    return _send(to_email, _get_display_name_from_fields(lead["fields"]), subject, body)


def send_final_offer_email(lead: dict) -> bool:
    """Dernière relance J+7 : message court, humain, sans pitch commercial."""
    to_email = lead["fields"].get("Email")
    if not to_email:
        return False

    first_name = lead["fields"].get("Prénom", "")
    greeting = f"Bonjour {first_name}" if first_name else "Bonjour"

    body = f"""{greeting},

Dernier message de ma part, promis.

Je sais que le quotidien prend tout le temps — c'est souvent pour ça qu'on n'a jamais l'occasion de prendre du recul sur son activité.

Si à un moment vous voulez qu'on regarde ensemble ce qui pourrait vous faire gagner du temps, 30 minutes suffisent pour avoir une première réponse concrète.

Rien à préparer : {CALENDLY_LINK}

Belle journée,{SIGNATURE}"""

    subject = "Une dernière chose avant de vous laisser"
    return _send(to_email, _get_display_name_from_fields(lead["fields"]), subject, body)


def _send(to_email: str, to_name: str, subject: str, body: str) -> bool:
    payload = {
        "sender": {"name": MIA_NAME, "email": MIA_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "textContent": body,
    }

    try:
        response = requests.post(BREVO_SEND_URL, json=payload, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logger.info(f"Email envoyé à {to_email}")
        return True
    except requests.HTTPError as e:
        logger.error(f"Brevo HTTP error pour {to_email}: {e.response.status_code} — {e.response.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"Erreur envoi email vers {to_email}: {e}")
        return False


def _get_display_name(lead: dict) -> str:
    parts = [lead.get("contact_first_name", ""), lead.get("contact_last_name", "")]
    name = " ".join(p for p in parts if p).strip()
    return name or lead.get("company_name", "")


def _get_display_name_from_fields(fields: dict) -> str:
    parts = [fields.get("Prénom", ""), fields.get("Nom", "")]
    name = " ".join(p for p in parts if p).strip()
    return name or fields.get("Entreprise", "")
