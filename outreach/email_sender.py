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
      <img src="https://mia-intelligence.com/assets/images/LogoMIAFBF.png" alt="Logo MIA" width="180" height="180" style="display:block;" />
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
