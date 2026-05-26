"""
LinkedIn outreach — deux modes :
1. PhantomBuster API (si configuré) : envoi automatique du DM
2. Mode manuel : stocke le message dans Airtable pour envoi manuel
"""

import requests
import logging
from config import PHANTOMBUSTER_API_KEY, PHANTOMBUSTER_AGENT_ID

logger = logging.getLogger(__name__)


def send_linkedin_message(lead_fields: dict) -> dict:
    """
    Envoie ou prépare le DM LinkedIn pour ce prospect.
    Retourne {"sent": bool, "mode": "auto"|"manual", "message": str}
    """
    linkedin_url = lead_fields.get("LinkedIn", "")
    message = lead_fields.get("Message LinkedIn", "")

    if not linkedin_url or not message:
        return {"sent": False, "mode": "skip", "message": ""}

    if PHANTOMBUSTER_API_KEY and PHANTOMBUSTER_AGENT_ID:
        success = _send_via_phantombuster(linkedin_url, message)
        return {"sent": success, "mode": "auto", "message": message}
    else:
        # Mode manuel : le message est déjà dans Airtable, on log juste
        logger.info(
            f"LinkedIn MANUEL requis pour {lead_fields.get('Entreprise')} "
            f"— {linkedin_url}\nMessage : {message}"
        )
        return {"sent": False, "mode": "manual", "message": message}


def _send_via_phantombuster(linkedin_url: str, message: str) -> bool:
    """
    Lance l'agent PhantomBuster "LinkedIn Message Sender" avec ce prospect.
    Nécessite un agent PhantomBuster configuré avec votre compte LinkedIn.
    """
    headers = {
        "X-Phantombuster-Key": PHANTOMBUSTER_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "id": PHANTOMBUSTER_AGENT_ID,
        "argument": {
            "profileUrls": [linkedin_url],
            "message": message,
        },
    }

    try:
        response = requests.post(
            "https://api.phantombuster.com/api/v2/agents/launch",
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        logger.info(f"PhantomBuster lancé pour {linkedin_url}")
        return True
    except requests.HTTPError as e:
        logger.error(f"PhantomBuster HTTP error: {e.response.status_code} — {e.response.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"PhantomBuster error: {e}")
        return False
