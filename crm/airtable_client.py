"""
Intégration Airtable — CRM des prospects.
Table cible : MIA_Prospection_V1 > Prospects
"""

import logging
from datetime import date, timedelta
from pyairtable import Api
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, FOLLOW_UP_DELAY_DAYS, LINKEDIN_DELAY_DAYS, SECOND_FOLLOW_UP_DAYS

logger = logging.getLogger(__name__)

TABLE_NAME = "Prospects"


def get_table():
    api = Api(AIRTABLE_API_KEY)
    return api.table(AIRTABLE_BASE_ID, TABLE_NAME)


def is_duplicate(lead: dict) -> bool:
    """Vérifie si le lead existe déjà (par email ou place_id)."""
    table = get_table()

    if lead.get("contact_email"):
        formula = f"FIND('{lead['contact_email']}', {{Email}})"
        results = table.all(formula=formula)
        if results:
            return True

    if lead.get("place_id"):
        formula = f"{{PlaceID}} = '{lead['place_id']}'"
        results = table.all(formula=formula)
        if results:
            return True

    return False


def save_lead(lead: dict) -> str | None:
    """Enregistre un nouveau prospect. Retourne l'ID Airtable créé."""
    table = get_table()
    today = date.today().isoformat()

    record_fields = {
        "Entreprise": lead.get("company_name", ""),
        "Secteur": lead.get("sector", ""),
        "Zone": lead.get("zone", ""),
        "Source": lead.get("source", ""),
        "Prénom": lead.get("contact_first_name", ""),
        "Nom": lead.get("contact_last_name", ""),
        "Email": lead.get("contact_email", ""),
        "Téléphone": lead.get("phone", ""),
        "Site web": lead.get("website", ""),
        "LinkedIn": lead.get("linkedin_url", ""),
        "Adresse": lead.get("address", ""),
        "Score Claude": lead.get("qualification_score", 0),
        "Raison score": lead.get("score_reason", ""),
        "Pain point": lead.get("pain_point", ""),
        "Sujet email": lead.get("email_subject", ""),
        "Corps email": lead.get("email_body", ""),
        "Message LinkedIn": lead.get("linkedin_message", ""),
        "Taille entreprise": lead.get("company_size", ""),
        "Audit recommandé": lead.get("recommended_audit", ""),
        "Prix recommandé": lead.get("recommended_price", 0),
        "Statut": "Nouveau",
        "Date ajout": today,
        "PlaceID": lead.get("place_id", ""),
    }

    try:
        record = table.create(record_fields)
        return record["id"]
    except Exception as e:
        logger.error(f"Erreur Airtable save_lead [{lead.get('company_name')}]: {e}")
        return None


def update_lead_status(record_id: str, status: str, extra_fields: dict = None):
    """Met à jour le statut d'un prospect."""
    table = get_table()
    fields = {"Statut": status}
    if extra_fields:
        fields.update(extra_fields)
    try:
        table.update(record_id, fields)
    except Exception as e:
        logger.error(f"Erreur Airtable update [{record_id}]: {e}")


def get_leads_with_new_email() -> list[dict]:
    """Leads enrichis manuellement avec un email — statut 'Sans email' mais Email renseigné."""
    table = get_table()
    formula = "AND({Statut} = 'Sans email', {Email} != '')"
    return table.all(formula=formula)


def get_leads_without_email() -> list[dict]:
    """Leads Airtable sans email à enrichir (statut 'Sans email', champ Email vide)."""
    table = get_table()
    formula = "AND({Statut} = 'Sans email', {Email} = '')"
    return table.all(formula=formula)


def get_leads_to_followup() -> list[dict]:
    """Retourne les prospects qui nécessitent une relance aujourd'hui."""
    table = get_table()
    today = date.today().isoformat()

    # Leads à relancer par email (J+3)
    formula = (
        f"AND("
        f"{{Statut}} = 'Email envoyé', "
        f"{{Date email initial}} <= '{(date.today() - timedelta(days=FOLLOW_UP_DELAY_DAYS)).isoformat()}'"
        f")"
    )
    email_followups = table.all(formula=formula)

    # Leads à contacter sur LinkedIn (J+5 depuis email)
    formula_linkedin = (
        f"AND("
        f"{{Statut}} = 'Email envoyé', "
        f"{{LinkedIn}} != '', "
        f"{{Date email initial}} <= '{(date.today() - timedelta(days=LINKEDIN_DELAY_DAYS)).isoformat()}', "
        f"{{LinkedIn envoyé}} = 0"
        f")"
    )
    linkedin_followups = table.all(formula=formula_linkedin)

    # 2ème relance email avec offre Diagnostic 99€ (J+7)
    formula_second = (
        f"AND("
        f"{{Statut}} = 'Relancé', "
        f"{{Date relance 1}} <= '{(date.today() - timedelta(days=SECOND_FOLLOW_UP_DAYS)).isoformat()}'"
        f")"
    )
    second_followups = table.all(formula=formula_second)

    return {
        "email_followups": email_followups,
        "linkedin_followups": linkedin_followups,
        "second_followups": second_followups,
    }


def get_weekly_stats() -> dict:
    """Retourne les statistiques de la semaine."""
    table = get_table()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    formula = f"{{Date ajout}} >= '{week_ago}'"
    all_recent = table.all(formula=formula)

    stats = {
        "total_new": len(all_recent),
        "emails_sent": len([r for r in all_recent if r["fields"].get("Statut") in ["Email envoyé", "Relancé", "2ème relance"]]),
        "responses": len([r for r in all_recent if r["fields"].get("Statut") in ["Réponse reçue", "RDV planifié", "Audit réalisé"]]),
        "rdv_booked": len([r for r in all_recent if r["fields"].get("Statut") in ["RDV planifié", "Audit réalisé"]]),
        "audits_done": len([r for r in all_recent if r["fields"].get("Statut") == "Audit réalisé"]),
    }
    return stats
