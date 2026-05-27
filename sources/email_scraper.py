"""
Enrichissement email — scrape les sites web des prospects pour trouver leurs adresses.
Cherche dans la page d'accueil et la page /contact (ou équivalents français).
Aucune dépendance externe : requests + re suffisent.
"""

import re
import logging
import requests

logger = logging.getLogger(__name__)

# Pages contact courantes à tester si la home ne contient pas d'email
CONTACT_PATHS = ["/contact", "/nous-contacter", "/contactez-nous", "/contact.html", "/contact.php"]

# Patterns à exclure — adresses génériques inutiles
EXCLUDE_PATTERNS = re.compile(
    r"(noreply|no-reply|donotreply|example|wixpress|wordpress|sentry|privacy|"
    r"support@wix|info@wix|@sentry\.io|@example\.com)",
    re.IGNORECASE,
)

# Regex email standard
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def scrape_email(website_url: str, timeout: int = 5) -> str:
    """
    Tente de trouver un email sur le site web du prospect.
    Essaie la page d'accueil, puis les pages /contact courantes.
    Retourne le premier email valide trouvé, ou '' si rien.
    """
    if not website_url:
        return ""

    base_url = website_url.rstrip("/")

    # 1. Page d'accueil
    email = _extract_from_url(base_url, timeout)
    if email:
        return email

    # 2. Pages contact
    for path in CONTACT_PATHS:
        email = _extract_from_url(base_url + path, timeout)
        if email:
            return email

    return ""


def _extract_from_url(url: str, timeout: int) -> str:
    """Télécharge une page et extrait le premier email valide."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return ""

        content = resp.text

        # Priorité 1 : liens mailto: (le plus fiable)
        mailto_matches = re.findall(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', content)
        for email in mailto_matches:
            if _is_valid(email):
                logger.debug(f"Email trouvé (mailto) sur {url}: {email}")
                return email.lower()

        # Priorité 2 : patterns email dans le texte brut
        matches = EMAIL_RE.findall(content)
        for email in matches:
            if _is_valid(email):
                logger.debug(f"Email trouvé (regex) sur {url}: {email}")
                return email.lower()

    except requests.exceptions.Timeout:
        logger.debug(f"Timeout sur {url}")
    except requests.exceptions.ConnectionError:
        logger.debug(f"Connexion impossible : {url}")
    except Exception as e:
        logger.debug(f"Erreur scraping {url}: {e}")

    return ""


def _is_valid(email: str) -> bool:
    """Filtre les emails génériques ou invalides."""
    if EXCLUDE_PATTERNS.search(email):
        return False
    # Pas d'images ou fichiers avec @ dans le nom
    if any(email.endswith(ext) for ext in [".png", ".jpg", ".gif", ".svg", ".webp"]):
        return False
    # Domaine doit avoir au moins un point
    parts = email.split("@")
    if len(parts) != 2 or "." not in parts[1]:
        return False
    return True
