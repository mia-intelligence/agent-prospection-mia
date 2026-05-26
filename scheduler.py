"""
Planificateur local (pour tester sur Windows).
Sur le VPS Linux, utiliser cron (voir README).
"""

import schedule
import time
import logging
from main import run_daily_prospection, run_daily_followups, run_weekly_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Prospection : lundi au vendredi à 8h
schedule.every().monday.at("08:00").do(run_daily_prospection)
schedule.every().tuesday.at("08:00").do(run_daily_prospection)
schedule.every().wednesday.at("08:00").do(run_daily_prospection)
schedule.every().thursday.at("08:00").do(run_daily_prospection)
schedule.every().friday.at("08:00").do(run_daily_prospection)

# Relances : lundi au vendredi à 14h
schedule.every().monday.at("14:00").do(run_daily_followups)
schedule.every().tuesday.at("14:00").do(run_daily_followups)
schedule.every().wednesday.at("14:00").do(run_daily_followups)
schedule.every().thursday.at("14:00").do(run_daily_followups)
schedule.every().friday.at("14:00").do(run_daily_followups)

# Rapport hebdo : vendredi à 17h
schedule.every().friday.at("17:00").do(run_weekly_report)

print("Planificateur démarré. Ctrl+C pour arrêter.")
print("Prochain cycle :", schedule.next_run())

while True:
    schedule.run_pending()
    time.sleep(30)
