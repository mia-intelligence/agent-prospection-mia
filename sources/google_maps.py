"""
Source de leads : Google Maps Places API (New)
Activer "Places API (New)" dans Google Cloud Console → APIs & Services → Bibliothèque.
"""

import requests
import time
import logging
from config import GOOGLE_MAPS_API_KEY, SEARCH_ZONES, TARGET_SECTORS_MAPS

logger = logging.getLogger(__name__)

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
])


def fetch_leads_google_maps(max_per_sector: int = 3) -> list[dict]:
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY manquant — source Google Maps ignorée")
        return []

    leads = []
    seen_ids = set()

    for zone in SEARCH_ZONES:
        for sector in TARGET_SECTORS_MAPS:
            try:
                results = _search_places(sector, zone, max_per_sector)
                for place in results:
                    place_id = place.get("id")
                    if place_id in seen_ids:
                        continue
                    seen_ids.add(place_id)
                    lead = _normalize(place, sector, zone)
                    if lead:
                        leads.append(lead)
                time.sleep(0.1)
            except requests.HTTPError as e:
                logger.error(f"Places API error pour '{sector} {zone}': {e.response.status_code} — {e.response.text[:200]}")
            except Exception as e:
                logger.error(f"Places API error pour '{sector} {zone}': {e}")

    logger.info(f"Google Maps: {len(leads)} leads collectés")
    return leads


def _search_places(sector: str, zone: str, max_results: int) -> list:
    response = requests.post(
        PLACES_URL,
        json={
            "textQuery": f"{sector} {zone}",
            "languageCode": "fr",
            "maxResultCount": min(max_results, 20),
        },
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("places", [])


def _normalize(place: dict, sector: str, zone: str) -> dict | None:
    name = place.get("displayName", {}).get("text", "").strip()
    if not name:
        return None

    if place.get("businessStatus") == "CLOSED_PERMANENTLY":
        return None

    reviews = place.get("userRatingCount", 0) or 0
    rating = place.get("rating", 0) or 0
    if reviews > 500 and rating >= 4.5:
        return None

    return {
        "source": "google_maps",
        "place_id": place.get("id", ""),
        "company_name": name,
        "sector": sector,
        "address": place.get("formattedAddress", ""),
        "zone": zone,
        "phone": place.get("nationalPhoneNumber", ""),
        "website": place.get("websiteUri", ""),
        "rating": rating,
        "reviews_count": reviews,
        "contact_first_name": "",
        "contact_last_name": "",
        "contact_email": "",
        "linkedin_url": "",
        "status": "new",
    }
