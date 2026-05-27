"""
Envoi d'emails via Brevo (ex-SendinBlue).
Gère : email initial, relance J+3, offre finale J+7.
Emails envoyés en HTML avec signature MIA officielle + lien de désinscription RGPD.
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

# ── Signature HTML MIA ────────────────────────────────────────────────────────
SIGNATURE_HTML = """
<table cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;border-radius:6px;overflow:hidden;font-family:Arial,sans-serif;">
  <tr>
    <td style="width:300px;background-color:#ffffff;vertical-align:middle;padding:20px 24px;border:1px solid #e0e8f0;">
      <div style="font-family:Georgia,'Times New Roman',serif;font-size:24px;font-style:italic;color:#1A2540;line-height:1;margin-bottom:10px;">Laetitia Coloré</div>
      <div style="font-size:11px;color:#3d5080;margin-bottom:2px;">Fondatrice de</div>
      <div style="font-size:11px;color:#1A2540;font-weight:bold;margin-bottom:10px;">MIA médiation intelligence appliquée</div>
      <div style="font-size:11px;color:#1A2540;margin-bottom:5px;">Tél : <a href="tel:+33617813305" style="color:#1A2540;text-decoration:none;">06 17 81 33 05</a></div>
      <div style="font-size:11px;color:#1A2540;margin-bottom:5px;">Mail : <a href="mailto:contact@mia-intelligence.com" style="color:#1A2540;text-decoration:none;">contact@mia-intelligence.com</a></div>
      <div style="font-size:11px;color:#1A2540;margin-bottom:12px;">Site : <a href="https://mia-intelligence.com" style="color:#1A2540;text-decoration:none;">mia-intelligence.com</a></div>
      <div style="width:80px;height:3px;background-color:#1A2540;"></div>
    </td>
    <td style="background-color:#e8effd;vertical-align:middle;text-align:center;padding:0;width:180px;">
      <img src="data:image/png;base64,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" alt="Logo MIA" width="180" height="180" style="display:block;" />
    </td>
  </tr>
</table>
"""

# ── Constructeur HTML ─────────────────────────────────────────────────────────

def _build_html(body_text: str) -> str:
    """
    Enveloppe le corps texte dans un email HTML complet.
    - Convertit les sauts de ligne en <br>
    - Ajoute la signature MIA
    - Ajoute le footer de désinscription (conformité RGPD)
    """
    body_html = (
        body_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>\n")
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:20px;background-color:#f4f6fb;font-family:Arial,sans-serif;">
  <table width="640" cellpadding="0" cellspacing="0" border="0"
         style="margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;
                box-shadow:0 2px 8px rgba(26,37,64,0.08);">

    <!-- Corps du message -->
    <tr>
      <td style="padding:36px 40px 24px 40px;font-size:14px;line-height:1.75;color:#1A2540;">
        {body_html}
      </td>
    </tr>

    <!-- Séparateur -->
    <tr>
      <td style="padding:0 40px;">
        <div style="height:1px;background:#e0e8f0;"></div>
      </td>
    </tr>

    <!-- Signature MIA -->
    <tr>
      <td style="padding:20px 40px 24px 40px;">
        {SIGNATURE_HTML}
      </td>
    </tr>

    <!-- Footer désinscription RGPD -->
    <tr>
      <td style="padding:14px 40px 20px 40px;background:#f4f6fb;font-size:10px;
                 color:#9aabbd;text-align:center;border-top:1px solid #e0e8f0;">
        Vous recevez cet email car votre activité correspond au profil des entreprises
        que j'accompagne.<br>
        Pour ne plus recevoir mes messages :
        <a href="mailto:{MIA_EMAIL}?subject=D%C3%A9sinscription%20prospection%20MIA"
           style="color:#9aabbd;text-decoration:underline;">cliquez ici</a>.
      </td>
    </tr>

  </table>
</body>
</html>"""


# ── Fonctions d'envoi ─────────────────────────────────────────────────────────

def send_initial_email(lead: dict) -> bool:
    """Envoie l'email de prospection initial généré par Claude."""
    to_email = lead.get("contact_email")
    if not to_email:
        logger.warning(f"Pas d'email pour {lead.get('company_name')} — email ignoré")
        return False

    to_name = _get_display_name(lead)
    subject = lead.get("email_subject", "Un truc que j'ai remarqué sur votre activité")
    body_text = lead.get("email_body", "")

    return _send(to_email, to_name, subject, body_text)


def send_followup_email(lead: dict, record_id: str) -> bool:
    """Relance J+3 : cas concret d'un professionnel du même secteur."""
    to_email = lead["fields"].get("Email")
    if not to_email:
        return False

    first_name = lead["fields"].get("Prénom", "")
    company    = lead["fields"].get("Entreprise", "votre activité")
    pain_point = lead["fields"].get("Pain point", "les tâches répétitives")

    greeting = f"Bonjour {first_name}" if first_name else "Bonjour"

    body = f"""{greeting},

Je me permets de revenir rapidement.

Cette semaine j'ai passé une journée avec un professionnel du même secteur que vous. Il perdait beaucoup de temps sur {pain_point}. Ensemble on a trouvé comment récupérer ce temps.

Est-ce que ça vous parle pour {company} ?

Un échange de 30 minutes, sans engagement : {CALENDLY_LINK}

Bonne journée,
Laetitia"""

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

Belle journée,
Laetitia"""

    subject = "Une dernière chose avant de vous laisser"
    return _send(to_email, _get_display_name_from_fields(lead["fields"]), subject, body)


def _send(to_email: str, to_name: str, subject: str, body_text: str) -> bool:
    """Envoie l'email en HTML via l'API Brevo transactionnelle."""
    payload = {
        "sender": {"name": MIA_NAME, "email": MIA_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": _build_html(body_text),
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
