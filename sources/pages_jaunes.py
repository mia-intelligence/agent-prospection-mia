"""
Scraper PagesJaunes — enrichissement email depuis les fiches pros.
Stratégie :
  1. Recherche par téléphone (le plus précis — on a le tel depuis Google Maps)
  2. Recherche par nom + ville si pas de tel
  3. Visite de la fiche pour extraire l'email
"""

import re
import time
import logging
import requests
from sources.email_scraper import EMAIL_RE, _is_valid

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCH_URL = "https://www.pagesjaunes.fr/pros/recherche"


def search_pages_jaunes(company_name: str, city: str, phone: str = "") -> str:
    """
    Cherche une entreprise sur PagesJaunes et retourne son email si trouvé.
    Essaie d'abord par téléphone (plus précis), puis par nom+ville.
    """
    # Nettoyage du téléphone
    phone_clean = re.sub(r"[\s\.\-]", "", phone or "")

    fiche_url = None

    # ── Recherche par téléphone ───────────────────────────────────────────
    if phone_clean and len(phone_clean) >= 10:
        fiche_url = _find_fiche_url(phone_clean, "")
        if fiche_url:
            logger.debug(f"PJ: fiche trouvée par tel ({phone_clean}) → {fiche_url}")

    # ── Recherche par nom + ville ─────────────────────────────────────────
    if not fiche_url:
        fiche_url = _find_fiche_url(company_name, city)
        if fiche_url:
            logger.debug(f"PJ: fiche trouvée par nom → {fiche_url}")

    if not fiche_url:
        return ""

    # ── Scraping de la fiche ──────────────────────────────────────────────
    time.sleep(1)
    return _scrape_fiche(fiche_url)


def _find_fiche_url(quoiqui: str, ou: str) -> str:
    """Lance une recherche et retourne l'URL de la première fiche."""
    params = {"quoiqui": quoiqui}
    if ou:
        params["ou"] = ou

    try:
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return ""

        html = resp.text

        # Cherche le lien vers une fiche pro (/pros/XXXXX)
        match = re.search(r'href="(/pros/[a-zA-Z0-9\-]+)"', html)
        if match:
            return "https://www.pagesjaunes.fr" + match.group(1)

    except Exception as e:
        logger.debug(f"PJ search error: {e}")

    return ""


def _scrape_fiche(url: str) -> str:
    """Visite une fiche PagesJaunes et extrait l'email."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return ""

        html = resp.text

        # 1. Cherche mailto:
        for email in re.findall(r'mailto:([^"\'>\s]+)', html):
            if _is_valid(email):
                return email.lower()

        # 2. Cherche patterns email dans le HTML
        for email in EMAIL_RE.findall(html):
            if _is_valid(email):
                return email.lower()

    except Exception as e:
        logger.debug(f"PJ fiche error ({url}): {e}")

    return ""
