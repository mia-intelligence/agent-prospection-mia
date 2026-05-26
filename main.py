"""
Agent Prospection MIA
=====================
Tourne quotidiennement (cron ou schedule.py).
Cycle complet : collect → qualify → save → email → follow-up → linkedin → stats
"""

import logging
import sys
from datetime import date

from sources.google_maps import fetch_leads_google_maps
from sources.apollo import fetch_leads_apollo
from processing.qualifier import qualify_and_personalize
from crm.airtable_client import (
    is_duplicate, save_lead, update_lead_status,
    get_leads_to_followup, get_leads_with_new_email, get_weekly_stats
)
from outreach.email_sender import (
    send_initial_email, send_followup_email, send_final_offer_email
)
from outreach.linkedin_sender import send_linkedin_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/prospection_{date.today().isoformat()}.log"),
    ],
)
logger = logging.getLogger("agent_prospection")


def run_daily_prospection():
    """
    Étape 1 : Collecter de nouveaux prospects et leur envoyer l'email initial.
    Lance chaque matin à 8h.
    """
    logger.info("=== CYCLE PROSPECTION DÉMARRÉ ===")

    # 1. Collecte des leads
    logger.info("Collecte Google Maps...")
    google_leads = fetch_leads_google_maps(max_per_sector=3)

    # Apollo désactivé — nécessite un plan payant (People Search)
    # apollo_leads = fetch_leads_apollo(max_per_sector=5)

    all_leads = google_leads
    logger.info(f"Total leads bruts : {len(all_leads)}")

    sent_count = 0
    skipped_dup = 0
    skipped_score = 0

    for lead in all_leads:
        company = lead.get("company_name", "?")

        # 2. Vérifier les doublons
        if is_duplicate(lead):
            logger.debug(f"Doublon ignoré : {company}")
            skipped_dup += 1
            continue

        # 3. Qualification via Claude
        lead = qualify_and_personalize(lead)
        score = lead.get("qualification_score", 0)

        if not lead.get("qualified"):
            logger.info(f"Score insuffisant ({score}/10) — ignoré : {company}")
            skipped_score += 1
            save_lead_with_status(lead, "Non qualifié")
            continue

        # 4. Sauvegarde Airtable
        record_id = save_lead(lead)
        if not record_id:
            logger.warning(f"Impossible de sauvegarder {company} dans Airtable")
            continue

        # 5. Envoi email initial
        if lead.get("contact_email"):
            email_sent = send_initial_email(lead)
            if email_sent:
                update_lead_status(record_id, "Email envoyé", {
                    "Date email initial": date.today().isoformat()
                })
                sent_count += 1
                logger.info(f"[{score}/10] Email envoyé → {company} ({lead.get('contact_email')})")
            else:
                update_lead_status(record_id, "Erreur envoi")
        else:
            update_lead_status(record_id, "Sans email — relance manuelle")
            logger.info(f"[{score}/10] Sauvegardé sans email → {company} (LinkedIn ou tél)")

    logger.info(
        f"Prospection terminée : {sent_count} emails envoyés, "
        f"{skipped_dup} doublons, {skipped_score} non qualifiés"
    )


def run_daily_followups():
    """
    Étape 2 : Relances automatiques des prospects existants.
    Lance chaque après-midi à 14h.
    """
    logger.info("=== CYCLE RELANCES DÉMARRÉ ===")

    followups = get_leads_to_followup()

    # Relances email J+3
    for record in followups["email_followups"]:
        success = send_followup_email(record, record["id"])
        if success:
            update_lead_status(record["id"], "Relancé", {
                "Date relance 1": date.today().isoformat()
            })
            logger.info(f"Relance J+3 → {record['fields'].get('Entreprise')}")

    # DMs LinkedIn J+5
    linkedin_manual_count = 0
    for record in followups["linkedin_followups"]:
        result = send_linkedin_message(record["fields"])
        if result["mode"] == "auto" and result["sent"]:
            update_lead_status(record["id"], "LinkedIn envoyé", {
                "LinkedIn envoyé": True,
                "Date LinkedIn": date.today().isoformat(),
            })
            logger.info(f"LinkedIn auto → {record['fields'].get('Entreprise')}")
        elif result["mode"] == "manual":
            update_lead_status(record["id"], "LinkedIn à envoyer manuellement")
            linkedin_manual_count += 1

    # 2ème relance email J+7 (offre diagnostic 99€)
    for record in followups["second_followups"]:
        success = send_final_offer_email(record)
        if success:
            update_lead_status(record["id"], "2ème relance", {
                "Date relance 2": date.today().isoformat()
            })
            logger.info(f"Relance finale → {record['fields'].get('Entreprise')}")

    if linkedin_manual_count > 0:
        logger.warning(
            f"{linkedin_manual_count} messages LinkedIn en attente d'envoi manuel "
            f"(configurer PhantomBuster pour automatiser)"
        )

    logger.info("Relances terminées")


def run_weekly_report():
    """
    Rapport hebdomadaire — lance le vendredi à 17h.
    """
    stats = get_weekly_stats()
    report = f"""
=== RAPPORT PROSPECTION MIA — Semaine du {date.today().isoformat()} ===

Nouveaux prospects contactés : {stats['total_new']}
Emails envoyés              : {stats['emails_sent']}
Réponses reçues             : {stats['responses']}
RDV planifiés               : {stats['rdv_booked']}
Audits réalisés             : {stats['audits_done']}

Objectif : 5 audits/semaine
Résultat : {stats['audits_done']}/5 {'✓' if stats['audits_done'] >= 5 else '— à accélérer'}

Taux réponse     : {round(stats['responses']/max(stats['emails_sent'],1)*100)}%
Taux conversion  : {round(stats['rdv_booked']/max(stats['responses'],1)*100)}%
"""
    logger.info(report)
    print(report)
    return stats


def run_send_pending_emails():
    """
    Envoie l'email initial aux leads enrichis manuellement avec un email.
    Toutes les 30 minutes — détecte les leads 'Sans email' qui ont maintenant une adresse.
    """
    logger.info("=== VÉRIFICATION EMAILS EN ATTENTE ===")
    pending = get_leads_with_new_email()

    if not pending:
        logger.info("Aucun lead en attente d'email")
        return 0

    sent = 0
    for record in pending:
        f = record["fields"]
        company = f.get("Entreprise", "?")
        to_email = f.get("Email", "")

        lead_for_email = {
            "contact_email": to_email,
            "company_name": company,
            "contact_first_name": f.get("Prénom", ""),
            "contact_last_name": f.get("Nom", ""),
            "email_subject": f.get("Sujet email", ""),
            "email_body": f.get("Corps email", ""),
        }

        ok = send_initial_email(lead_for_email)
        if ok:
            update_lead_status(record["id"], "Email envoyé", {
                "Date email initial": date.today().isoformat()
            })
            sent += 1
            logger.info(f"Email envoyé → {company} ({to_email})")
        else:
            logger.error(f"Échec envoi → {company}")

    logger.info(f"=== {sent} emails envoyés sur {len(pending)} en attente ===")
    return sent


def save_lead_with_status(lead: dict, status: str):
    lead["_force_status"] = status
    record_id = save_lead(lead)
    if record_id:
        update_lead_status(record_id, status)


if __name__ == "__main__":
    import sys
    import os
    os.makedirs("logs", exist_ok=True)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "prospect":
            run_daily_prospection()
        elif cmd == "followup":
            run_daily_followups()
        elif cmd == "sendemails":
            run_send_pending_emails()
        elif cmd == "report":
            run_weekly_report()
        else:
            print("Usage: python main.py [prospect|followup|sendemails|report]")
    else:
        # Par défaut : cycle complet
        run_daily_prospection()
        run_daily_followups()
