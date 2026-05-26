"""
Source de leads : Apollo.io API
Trouve des professions libérales, PME et consultants via Apollo.
"""

import requests
import logging
from config import (
    APOLLO_API_KEY, TARGET_SECTORS_APOLLO,
    APOLLO_EMPLOYEE_RANGE, APOLLO_LOCATIONS
)

logger = logging.getLogger(__name__)

APOLLO_BASE_URL = "https://api.apollo.io/v1"


def fetch_leads_apollo(max_per_sector: int = 10) -> list[dict]:
    """
    Récupère des leads depuis Apollo.io pour les secteurs et zones configurés.
    """
    if not APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY manquant — source Apollo ignorée")
        return []

    leads = []
    seen_ids = set()

    for sector in TARGET_SECTORS_APOLLO:
        for location in APOLLO_LOCATIONS:
            try:
                results = _search_apollo(sector, location, max_per_sector)
                for person in results:
                    person_id = person.get("id")
                    if person_id in seen_ids:
                        continue
                    seen_ids.add(person_id)

                    lead = _normalize_apollo_lead(person, sector, location)
                    if lead:
                        leads.append(lead)

            except Exception as e:
                logger.error(f"Erreur Apollo [{sector} / {location}]: {e}")
                continue

    logger.info(f"Apollo: {len(leads)} leads collectés")
    return leads


def _search_apollo(sector: str, location: str, max_results: int) -> list:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }

    payload = {
        "q_organization_industry_tag_ids": [],
        "organization_industry_tag_ids": [],
        "q_keywords": sector,
        "person_locations": [location],
        "organization_num_employees_ranges": [
            f"{APOLLO_EMPLOYEE_RANGE['min']},{APOLLO_EMPLOYEE_RANGE['max']}"
        ],
        "contact_email_status": ["verified"],
        "per_page": max_results,
        "page": 1,
    }

    try:
        response = requests.post(
            f"{APOLLO_BASE_URL}/mixed_people/search",
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("people", [])

    except requests.HTTPError as e:
        logger.error(f"Apollo HTTP error: {e.response.status_code} — {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.error(f"Apollo request error: {e}")
        return []


def _normalize_apollo_lead(person: dict, sector: str, location: str) -> dict | None:
    # Filtrer si pas d'email
    email = person.get("email", "")
    if not email or "catch-all" in str(person.get("email_status", "")):
        return None

    org = person.get("organization", {}) or {}
    employees = org.get("num_employees", 0) or 0

    # Garder uniquement les TPE (1-50 salariés)
    if employees > 50:
        return None

    first_name = person.get("first_name", "")
    last_name = person.get("last_name", "")
    if not first_name and not last_name:
        return None

    return {
        "source": "apollo",
        "apollo_id": person.get("id", ""),
        "company_name": org.get("name", ""),
        "sector": sector,
        "address": ", ".join(filter(None, [
            person.get("city", ""),
            person.get("state", ""),
            person.get("country", ""),
        ])),
        "zone": location,
        "phone": person.get("phone_numbers", [{}])[0].get("sanitized_number", "") if person.get("phone_numbers") else "",
        "website": org.get("website_url", ""),
        "contact_first_name": first_name,
        "contact_last_name": last_name,
        "contact_email": email,
        "linkedin_url": person.get("linkedin_url", ""),
        "title": person.get("title", ""),
        "employees_count": employees,
        "status": "new",
    }
