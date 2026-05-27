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

    # 1. Collecte des leads — plafond 30/jour pour maîtriser le budget
    logger.info("Collecte Google Maps...")
    google_leads = fetch_leads_google_maps(max_per_sector=3, max_total=30)

    # Apollo désactivé — nécessite un plan payant (People Search)
    # apollo_leads = fetch_leads_apollo(max_per_sector=5)

    all_leads = google_leads
    logger.info(f"Total leads bruts : {len(all_leads)}")

    sent_count = 0
    skipped_dup = 0
    skipped_no_email = 0

    for lead in all_leads:
        company = lead.get("company_name", "?")

        # 2. Vérifier les doublons
        if is_duplicate(lead):
            logger.debug(f"Doublon ignoré : {company}")
            skipped_dup += 1
            continue

        # 3. EMAIL EN PREMIER — pas d'email = pas de Claude, pas d'Airtable
        if not lead.get("contact_email"):
            logger.info(f"Ignoré (pas d'email trouvé) : {company}")
            skipped_no_email += 1
            continue

        # 4. Qualification via Claude (seulement si email disponible)
        lead = qualify_and_personalize(lead)
        score = lead.get("qualification_score", 0)

        if not lead.get("qualified"):
            logger.info(f"Score insuffisant ({score}/10) — ignoré : {company}")
            continue

        # 5. Sauvegarde Airtable
        record_id = save_lead(lead)
        if not record_id:
            logger.warning(f"Impossible de sauvegarder {company} dans Airtable")
            continue

        # 6. Envoi email
        if lead.get("email_verified") is False:
            # Email deviné (pattern) → attente validation Laetitia dans Airtable
            update_lead_status(record_id, "Email probable")
            logger.info(f"[{score}/10] Email probable → {company} ({lead.get('contact_email')})")
        else:
            # Email confirmé (scraping/DDG) → envoi automatique
            email_sent = send_initial_email(lead)
            if email_sent:
                update_lead_status(record_id, "Email envoyé", {
                    "Date email initial": date.today().isoformat()
                })
                sent_count += 1
                logger.info(f"[{score}/10] Email envoyé → {company} ({lead.get('contact_email')})")
            else:
                update_lead_status(record_id, "Erreur envoi")

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


def run_enrich_existing() -> str:
    """
    Reprend les leads Airtable avec statut 'Sans email' (champ Email vide)
    et tente de trouver leur email via PagesJaunes, Societe.com, DDG et patterns.
    Lance manuellement : python main.py enrich
    """
    from crm.airtable_client import get_leads_without_email
    from sources.email_hunter import hunt_email
    import time

    leads = get_leads_without_email()
    logger.info(f"=== ENRICHISSEMENT : {len(leads)} leads sans email dans Airtable ===")

    enriched = verified_count = probable_count = inactive_count = 0

    for record in leads:
        f = record["fields"]
        company  = f.get("Entreprise", "?")
        zone     = f.get("Zone", "")
        website  = f.get("Site web", "")
        phone    = f.get("Téléphone", "")

        logger.info(f"Enrichissement → {company}")

        email, verified, extras = hunt_email(
            company_name=company,
            zone=zone,
            website=website,
            phone=phone,
        )

        # Entreprise inactive détectée sur Societe.com
        if not extras.get("actif", True):
            update_lead_status(record["id"], "Inactif")
            inactive_count += 1
            logger.info(f"Inactive → {company}")
            time.sleep(2)
            continue

        if email:
            enriched += 1
            extra_fields = {"Email": email}

            # Enrichir avec le nom du dirigeant si trouvé
            if extras.get("dirigeant") and not f.get("Nom"):
                parts = extras["dirigeant"].split()
                if len(parts) >= 2:
                    extra_fields["Prénom"] = parts[0].capitalize()
                    extra_fields["Nom"] = " ".join(parts[1:]).upper()

            if extras.get("siret"):
                extra_fields["SIRET"] = extras["siret"]

            if verified:
                # Email fiable → garde statut "Sans email" pour que le cron sendemails l'envoie
                update_lead_status(record["id"], "Sans email", extra_fields)
                verified_count += 1
                logger.info(f"✓ Email trouvé (vérifié) → {company} : {email}")
            else:
                # Email probable → statut spécifique, Laetitia valide dans Airtable
                update_lead_status(record["id"], "Email probable", extra_fields)
                probable_count += 1
                logger.info(f"~ Email probable → {company} : {email}")
        else:
            logger.info(f"✗ Aucun email trouvé → {company}")

        time.sleep(2)  # Respecte les rate-limits des sites

    summary = (
        f"\n=== ENRICHISSEMENT TERMINÉ ===\n"
        f"Leads traités       : {len(leads)}\n"
        f"Emails trouvés      : {enriched} ({verified_count} vérifiés + {probable_count} probables)\n"
        f"Entreprises inactives: {inactive_count}\n"
        f"Sans email (reste)  : {len(leads) - enriched - inactive_count}\n"
        f"\nLes emails vérifiés seront envoyés automatiquement par le cron sendemails.\n"
        f"Les emails probables sont visibles dans Airtable — valide et change le statut en 'Sans email'."
    )
    logger.info(summary)
    return summary


def save_lead_with_status(lead: dict, status: str):
    lead["_force_status"] = status
    record_id = save_lead(lead)
    if record_id:
        update_lead_status(record_id, status)


def run_custom_search(secteurs: list[str], zones: list[str]) -> str:
    """
    Recherche personnalisée depuis Telegram — secteurs et zones au choix.
    Plafonnée à 20 leads bruts pour maîtriser le budget.
    Retourne un résumé lisible pour le bot.
    """
    logger.info(f"=== RECHERCHE PERSONNALISÉE: {secteurs} / {zones} ===")

    # Passe zones et secteurs en paramètre — pas d'override du module config
    leads = fetch_leads_google_maps(
        max_per_sector=2,
        zones=zones,
        sectors=secteurs,
        max_total=20,
    )

    sent = qualifies = skipped_no_email = 0
    for lead in leads:
        if is_duplicate(lead):
            continue
        # Email d'abord — Claude seulement si contactable
        if not lead.get("contact_email"):
            skipped_no_email += 1
            continue
        lead = qualify_and_personalize(lead)
        if not lead.get("qualified"):
            continue
        qualifies += 1
        rid = save_lead(lead)
        if rid:
            if lead.get("email_verified") is False:
                update_lead_status(rid, "Email probable")
            else:
                ok = send_initial_email(lead)
                if ok:
                    update_lead_status(rid, "Email envoyé", {"Date email initial": date.today().isoformat()})
                    sent += 1

    return (
        f"Recherche terminée — {secteurs} dans {zones}\n"
        f"Leads trouvés : {len(leads)}\n"
        f"Sans email (ignorés) : {skipped_no_email}\n"
        f"Qualifiés avec email : {qualifies}\n"
        f"Emails envoyés : {sent}\n"
        f"Emails probables (à valider) : {qualifies - sent}"
    )


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
        elif cmd == "search":
            # Usage: python main.py search "dentiste,médecin" "Draguignan,Toulon"
            secteurs = sys.argv[2].split(",") if len(sys.argv) > 2 else ["dentiste"]
            zones = [z + ", France" for z in sys.argv[3].split(",")] if len(sys.argv) > 3 else ["Var, France"]
            result = run_custom_search(secteurs, zones)
            print(result)
        elif cmd == "enrich":
            # Enrichit les leads Airtable 'Sans email' avec PagesJaunes, Societe.com, DDG
            print(run_enrich_existing())
        else:
            print("Usage: python main.py [prospect|followup|sendemails|report|search|enrich]")
            print("  search : python main.py search 'dentiste,médecin' 'Draguignan,Toulon'")
            print("  enrich : python main.py enrich   ← reprend les leads sans email dans Airtable")
    else:
        run_daily_prospection()
        run_daily_followups()
