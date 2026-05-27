"""
Scraper Societe.com — enrichissement depuis le registre des entreprises françaises.
Utile pour :
  - Trouver le nom du dirigeant (personnalisation email)
  - Trouver l'email si publié dans la fiche
  - Confirmer que l'entreprise est bien active (SIRET)
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
    "Referer": "https://www.societe.com/",
}

SEARCH_URL = "https://www.societe.com/cgi-bin/search"


def search_societe_com(company_name: str, city: str = "") -> dict:
    """
    Cherche une entreprise sur Societe.com.
    Retourne un dict avec :
      - email       : str  ('' si non trouvé)
      - dirigeant   : str  (prénom + nom du dirigeant si trouvé)
      - siret       : str
      - actif       : bool
    """
    result = {"email": "", "dirigeant": "", "siret": "", "actif": True}

    # Construction de la requête
    query = company_name
    if city:
        query += f" {city}"

    fiche_url = _find_fiche(query)
    if not fiche_url:
        return result

    time.sleep(1)
    _scrape_fiche(fiche_url, result)
    return result


def _find_fiche(query: str) -> str:
    """Recherche et retourne l'URL de la première fiche entreprise."""
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"champs": query},
            headers=HEADERS,
            timeout=8,
        )
        if resp.status_code != 200:
            return ""

        html = resp.text

        # Lien vers fiche entreprise : /societe/NOM-VILLE.html ou /societe/XXXXXX.html
        match = re.search(r'href="(/societe/[^"]+\.html)"', html)
        if match:
            return "https://www.societe.com" + match.group(1)

    except Exception as e:
        logger.debug(f"Societe.com search error: {e}")

    return ""


def _scrape_fiche(url: str, result: dict) -> None:
    """Visite une fiche Societe.com et enrichit le dict result."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return

        html = resp.text

        # ── Email ─────────────────────────────────────────────────────────
        for email in re.findall(r'mailto:([^"\'>\s]+)', html):
            if _is_valid(email):
                result["email"] = email.lower()
                break

        if not result["email"]:
            for email in EMAIL_RE.findall(html):
                if _is_valid(email):
                    result["email"] = email.lower()
                    break

        # ── Dirigeant ─────────────────────────────────────────────────────
        # Societe.com affiche le dirigeant dans un bloc structuré
        dirigeant_match = re.search(
            r'dirigeant[^>]*>.*?<[^>]+>([A-ZÉÈÀÙÂÊÎÔÛÇ][a-zéèàùâêîôûç\-]+\s+[A-ZÉÈÀÙÂÊÎÔÛÇ]+)',
            html, re.DOTALL | re.IGNORECASE,
        )
        if dirigeant_match:
            result["dirigeant"] = dirigeant_match.group(1).strip()

        # ── SIRET ─────────────────────────────────────────────────────────
        siret_match = re.search(r'\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b', html)
        if siret_match:
            result["siret"] = re.sub(r'\s', '', siret_match.group(1))

        # ── Statut actif ──────────────────────────────────────────────────
        if re.search(r'(radiée|cessation|liquidation|dissolution)', html, re.I):
            result["actif"] = False

    except Exception as e:
        logger.debug(f"Societe.com fiche error ({url}): {e}")
