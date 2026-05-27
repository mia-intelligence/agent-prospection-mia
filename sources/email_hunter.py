"""
Chasseur d'emails — 3 couches sans API payante :

  1. DuckDuckGo  : recherche web ciblée sur le nom de l'entreprise + zone
  2. Patterns    : génère les adresses les plus probables (contact@, info@…)
  3. SMTP probe  : vérifie silencieusement si la boîte existe (sans envoyer)

Usage :
    from sources.email_hunter import hunt_email
    email, verified = hunt_email("Garage Martin", "Rousset, France", "https://garage-martin.fr")
    # verified=True  → envoi auto OK
    # verified=False → email probable, sauvegardé en attente de validation
"""

import re
import socket
import smtplib
import logging
import time

logger = logging.getLogger(__name__)

# ── Regex & filtres ───────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)

EXCLUDE = re.compile(
    r"(noreply|no-reply|donotreply|example|wixpress|wordpress|sentry|"
    r"privacy|support@wix|info@wix|@sentry\.io|@example\.com|@shutterstock|"
    r"@adobe|@google|@facebook|@instagram|@linkedin)",
    re.I,
)

# Préfixes à tester dans l'ordre de probabilité pour les TPE françaises
COMMON_PREFIXES = [
    "contact", "info", "bonjour", "accueil",
    "direction", "gestion", "pro", "hello",
    "secretariat", "commercial", "garage",
]

# Délai entre requêtes DDG pour éviter le rate-limit (secondes)
DDG_DELAY = 1.5


# ── Fonction principale ───────────────────────────────────────────────────────

def hunt_email(
    company_name: str,
    zone: str,
    website: str = "",
    phone: str = "",
) -> tuple[str, bool, dict]:
    """
    Cherche l'email d'une entreprise sans API payante.
    Cascade : PagesJaunes → Societe.com → DuckDuckGo → Patterns SMTP

    Retourne (email, verified, extras) :
      - verified=True  : email trouvé sur le web → envoi auto
      - verified=False : email deviné par pattern → validation manuelle
      - extras         : dict avec dirigeant, siret, actif (depuis Societe.com)
    """
    domain = _extract_domain(website)
    city = zone.replace(", France", "").strip()
    extras = {"dirigeant": "", "siret": "", "actif": True}

    # ── Couche 1 : PagesJaunes ────────────────────────────────────────────
    try:
        from sources.pages_jaunes import search_pages_jaunes
        email = search_pages_jaunes(company_name, city, phone)
        if email:
            logger.info(f"[PagesJaunes] Email : {email} ({company_name})")
            return email, True, extras
    except Exception as e:
        logger.debug(f"PagesJaunes error: {e}")

    # ── Couche 2 : Societe.com ────────────────────────────────────────────
    try:
        from sources.societe_com import search_societe_com
        data = search_societe_com(company_name, city)
        extras.update({k: data[k] for k in ("dirigeant", "siret", "actif")})
        if data.get("email"):
            logger.info(f"[Societe.com] Email : {data['email']} ({company_name})")
            return data["email"], True, extras
        if not data.get("actif"):
            logger.info(f"[Societe.com] Entreprise inactive — ignorée : {company_name}")
            return "", False, extras
    except Exception as e:
        logger.debug(f"Societe.com error: {e}")

    # ── Couche 3 : DuckDuckGo ─────────────────────────────────────────────
    email = _search_duckduckgo(company_name, zone, domain)
    if email:
        logger.info(f"[DDG] Email : {email} ({company_name})")
        return email, True, extras

    # ── Couche 4 : Patterns + SMTP ────────────────────────────────────────
    if domain:
        email = _try_patterns_with_smtp(domain)
        if email:
            return email, False, extras
        probable = f"contact@{domain}"
        logger.info(f"[Pattern] Email probable : {probable} ({company_name})")
        return probable, False, extras

    return "", False, extras


# ── Couche 1 : DuckDuckGo ─────────────────────────────────────────────────────

def _search_duckduckgo(company_name: str, zone: str, domain: str = "") -> str:
    """Lance 2-3 requêtes DDG et extrait le premier email valide trouvé."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("duckduckgo-search non installé — pip install duckduckgo-search")
        return ""

    # Zone nettoyée (ex: "Rousset, France" → "Rousset")
    city = zone.replace(", France", "").strip()

    queries = [
        f'"{company_name}" {city} email contact',
        f'"{company_name}" {city} "@"',
    ]
    if domain:
        queries.insert(0, f'"{company_name}" "@{domain}"')

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = list(ddgs.text(query, max_results=5))
                for r in results:
                    text = r.get("body", "") + " " + r.get("href", "")
                    for email in EMAIL_RE.findall(text):
                        if _is_valid(email):
                            return email.lower()
                time.sleep(DDG_DELAY)
            except Exception as e:
                logger.debug(f"DDG query failed ({query[:40]}…): {e}")
                time.sleep(DDG_DELAY)

    return ""


# ── Couche 2 & 3 : Patterns + SMTP probe ─────────────────────────────────────

def _try_patterns_with_smtp(domain: str) -> str:
    """
    Génère les patterns courants et teste leur existence via SMTP.
    Retourne le premier validé, ou '' si le serveur bloque les probes.
    """
    # Vérifier d'abord que le domaine a un MX (sinon inutile de continuer)
    if not _has_mx(domain):
        logger.debug(f"Pas de MX pour {domain}")
        return ""

    mx_host = _get_mx(domain)
    if not mx_host:
        return ""

    for prefix in COMMON_PREFIXES:
        email = f"{prefix}@{domain}"
        result = _smtp_probe(email, mx_host)
        if result == "valid":
            logger.info(f"[SMTP] Email vérifié : {email}")
            return email
        elif result == "blocked":
            # Le serveur ne répond pas aux probes — on arrête
            logger.debug(f"SMTP probe bloqué sur {domain}")
            return ""
        # result == "invalid" → essaye le préfixe suivant

    return ""


def _smtp_probe(email: str, mx_host: str) -> str:
    """
    Teste silencieusement si une boîte mail existe.
    Retourne : 'valid' | 'invalid' | 'blocked'
    """
    try:
        with smtplib.SMTP(timeout=5) as smtp:
            smtp.connect(mx_host, 25)
            smtp.ehlo("mia-intelligence.com")
            smtp.mail("")
            code, msg = smtp.rcpt(email)
            smtp.rset()
            if code == 250:
                return "valid"
            elif code in (550, 551, 553):
                return "invalid"
            else:
                return "blocked"
    except (smtplib.SMTPConnectError, ConnectionRefusedError, socket.timeout,
            OSError, smtplib.SMTPException):
        return "blocked"


def _has_mx(domain: str) -> bool:
    """Vérifie qu'un domaine a un enregistrement MX."""
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


def _get_mx(domain: str) -> str:
    """Retourne le serveur mail prioritaire du domaine."""
    try:
        import dns.resolver
        records = dns.resolver.resolve(domain, "MX")
        return str(sorted(records, key=lambda r: r.preference)[0].exchange).rstrip(".")
    except Exception:
        return ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_domain(website: str) -> str:
    """Extrait le domaine depuis une URL."""
    if not website:
        return ""
    match = re.search(r"(?:https?://)?(?:www\.)?([^/\s?#]+)", website)
    domain = match.group(1) if match else ""
    # Ignore les domaines de plateformes génériques
    generics = {"wix.com", "wordpress.com", "jimdo.com", "webnode.fr",
                "site123.com", "pages.google.com", "facebook.com"}
    if any(g in domain for g in generics):
        return ""
    return domain


def _is_valid(email: str) -> bool:
    """Filtre les emails génériques ou invalides."""
    if EXCLUDE.search(email):
        return False
    if any(email.endswith(ext) for ext in [".png", ".jpg", ".gif", ".svg", ".webp", ".pdf"]):
        return False
    parts = email.split("@")
    if len(parts) != 2 or "." not in parts[1]:
        return False
    # Rejeter les domaines trop courts ou suspects
    domain = parts[1]
    if len(domain) < 4 or domain.count(".") == 0:
        return False
    return True
