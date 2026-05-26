#!/bin/bash
# Installation sur le VPS Hostinger (Linux)
# Coller dans le terminal VPS après avoir uploadé le projet

# 1. Installer les dépendances
cd /opt/agent-prospection-mia
pip3 install -r requirements.txt

# 2. Ajouter les cron jobs (édite la crontab)
# crontab -e
# Puis coller les lignes suivantes :

# Prospection quotidienne — lundi à vendredi à 8h
# 0 8 * * 1-5 cd /opt/agent-prospection-mia && python3 main.py prospect >> logs/cron.log 2>&1

# Relances quotidiennes — lundi à vendredi à 14h
# 0 14 * * 1-5 cd /opt/agent-prospection-mia && python3 main.py followup >> logs/cron.log 2>&1

# Rapport hebdomadaire — vendredi à 17h
# 0 17 * * 5 cd /opt/agent-prospection-mia && python3 main.py report >> logs/cron.log 2>&1

# 3. Créer le dossier logs
mkdir -p /opt/agent-prospection-mia/logs

echo "Cron jobs à ajouter avec : crontab -e"
