"""
Source de leads : Google Maps Places API
Trouve les TPE/artisans locaux par secteur et zone géographique.
"""

import googlemaps
import time
import logging
from config import GOOGLE_MAPS_API_KEY, SEARCH_ZONES, TARGET_SECTORS_MAPS

logger = logging.getLogger(__name__)


def fetch_leads_google_maps(max_per_sector: int = 5) -> list[dict]:
    """
    Récupère des leads depuis Google Maps pour tous les secteurs et zones.
    Retourne une liste de prospects normalisés.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY manquant — source Google Maps ignorée")
        return []

    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    leads = []
    seen_place_ids = set()

    for zone in SEARCH_ZONES:
        for sector in TARGET_SECTORS_MAPS:
            try:
                results = _search_places(gmaps, sector, zone, max_per_sector)
                for place in results:
                    place_id = place.get("place_id")
                    if place_id in seen_place_ids:
                        continue
                    seen_place_ids.add(place_id)

                    lead = _normalize_google_maps_lead(place, sector, zone)
                    if lead:
                        leads.append(lead)

                time.sleep(0.2)  # Respecter les rate limits Google

            except Exception as e:
                logger.error(f"Erreur Google Maps [{sector} / {zone}]: {e}")
                continue

    logger.info(f"Google Maps: {len(leads)} leads collectés")
    return leads


def _search_places(gmaps, sector: str, zone: str, max_results: int) -> list:
    query = f"{sector} {zone}"
    try:
        response = gmaps.places(query=query)
        results = response.get("results", [])[:max_results]

        # Récupérer les détails pour avoir le site web et le téléphone
        detailed = []
        for place in results:
            place_id = place.get("place_id")
            if place_id:
                try:
                    detail = gmaps.place(
                        place_id=place_id,
                        fields=["name", "formatted_address", "formatted_phone_number",
                                "website", "rating", "user_ratings_total", "place_id",
                                "business_status", "types"]
                    )
                    detailed.append(detail.get("result", place))
                    time.sleep(0.1)
                except Exception:
                    detailed.append(place)
            else:
                detailed.append(place)
        return detailed

    except Exception as e:
        logger.error(f"Places API error pour '{query}': {e}")
        return []


def _normalize_google_maps_lead(place: dict, sector: str, zone: str) -> dict | None:
    name = place.get("name", "").strip()
    if not name:
        return None

    # Filtrer les établissements fermés
    if place.get("business_status") == "CLOSED_PERMANENTLY":
        return None

    # Filtrer les grandes chaînes (rating élevé avec beaucoup d'avis = déjà bien équipés)
    rating = place.get("rating", 0)
    reviews = place.get("user_ratings_total", 0)
    if reviews > 500 and rating >= 4.5:  # Probablement une chaîne nationale
        return None

    return {
        "source": "google_maps",
        "place_id": place.get("place_id", ""),
        "company_name": name,
        "sector": sector,
        "address": place.get("formatted_address", ""),
        "zone": zone,
        "phone": place.get("formatted_phone_number", ""),
        "website": place.get("website", ""),
        "rating": rating,
        "reviews_count": reviews,
        "contact_first_name": "",
        "contact_last_name": "",
        "contact_email": "",
        "linkedin_url": "",
        "status": "new",
    }
