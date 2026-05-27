# CLAUDE.md — Mémoire & Stratégie MIA
> Fichier de mémoire permanente pour OpenClaw. Mis à jour après chaque session importante.
> **Dernière mise à jour** : 27 mai 2026

---

## 🧠 Qui est Laetitia / MIA

**Laetitia Coloré** — Fondatrice de MIA (Médiation Intelligence Appliquée)

MIA ce n'est PAS des agents IA génériques. C'est :
1. **Audit** des process de l'entreprise
2. **Structuration** : identifier ce qui peut être automatisé
3. **Custom dev** : créer des applications sur mesure avec leurs outils existants
4. **Maintenance** : suivi mensuel

**Le vrai problème des clients de MIA :**
> "Ils font des tableaux Excel à pagaille, ils ne savent plus où trouver leurs KPIs,
> zéro alertes, gestion réactive au jour le jour. Ils ne prévoient pas — ils subissent."

**Les 4 alertes qui font mouche :**
1. 🚨 Chantier moins rentable que le devis initial
2. 🚨 Retard vs. planning
3. 🚨 Dépassement budgétaire
4. 🚨 Problème trésorerie / cash flow

**Message clé (validé) :**
*"Vous gérez au jour le jour sans visibilité. On crée un tableau de bord temps réel avec alertes — vous voyez AVANT que ça devienne un problème."*

---

## 💼 Clients actuels (mai 2026)

| Client | Secteur | Statut | Next |
|---|---|---|---|
| Menuiserie Alu/PVC | Menuiserie | App livrée ✅ — attente retour APIs (TomTom vs Maps) | Devis custom dev |
| Irisolaris | Électricité solaire | Audit fait jeudi dernier | Mise au propre + devis |

**Modèle tarifaire :**
- Audit demi-journée : 350€ HT (1-5 personnes)
- Audit journée complète : 850€ HT (5-50 personnes)
- Maintenance : 180-250€/mois selon ce qui est mis en place
- Custom dev : devis selon projet

---

## 🎯 Stratégie de prospection validée

### Profil cible idéal (validé en session)
> **PME artisanales : 20-25 salariés, ~1M€ de chiffre d'affaires**
> C'est la taille où la douleur est maximale : trop grand pour gérer à l'instinct,
> trop petit pour avoir un DAF ou des outils pros. Elles subissent sans visibilité.

### Secteurs prioritaires (expertise Laetitia)
| Secteur | Pourquoi | Taille cible | Zone |
|---|---|---|---|
| **Menuiseries** (fabrication + pose) | 10+ ans d'expérience, besoin fort en rentabilité chantier | 20-25 salariés, ~1M€ CA | PACA |
| **Électricité solaire** | 3 ans avec Irisolaris, marché en croissance | 20-25 salariés, ~1M€ CA | PACA |
| **Plombiers / chauffagistes** | Même douleur chantier, forte densité en PACA | 20-25 salariés, ~1M€ CA | PACA |

### À éviter pour l'instant
- Artisans solo ou < 5 salariés : budget trop serré pour l'audit
- Grands groupes > 50 salariés : cycles de décision trop longs
- Garages/voitures : peu d'emails publics, mauvais retour testé
- Kinésithérapeutes : secteur différent, pas l'expertise de Laetitia

### Volume recommandé par test
- **Premier test** : 15 leads par secteur, pas plus
- **Si bons résultats** (>10% réponse) : doubler
- **Si aucun retour** : changer de message ou de secteur

---

## 🤖 Personas de prospection (commandes prêtes)

Utilise ces personas pour lancer les recherches. Syntaxe :
```
python main.py search "SECTEURS" "VILLES"
```

### Persona "Menuisiers PACA"
```bash
python main.py search "menuisier,menuiserie,charpentier" "Toulon,Marseille,Aix-en-Provence"
```
*Pain point* : rentabilité chantier, devis sur site, suivi temps réel

### Persona "Électricité solaire PACA"
```bash
python main.py search "électricien solaire,installateur photovoltaique,énergie solaire" "Toulon,Var,Bouches-du-Rhône"
```
*Pain point* : suivi chantiers multi-sites, rentabilité pose, SAV planifié

### Persona "Plombiers / Chauffagistes PACA"
```bash
python main.py search "plombier,chauffagiste,plomberie chauffage" "Toulon,Marseille,Draguignan"
```
*Pain point* : devis rapide sur chantier, planning interventions, suivi stocks

### Persona "Artisans Var"
```bash
python main.py search "électricien,menuisier,plombier,carreleur" "Brignoles,Saint-Maximin,Draguignan"
```
*Zone* : petites villes du Var — moins concurrencées, artisans plus accessibles

### Enrichissement leads existants (sans nouvelle recherche)
```bash
python main.py enrich
```
*Reprend tous les leads Airtable sans email et tente de trouver leurs contacts.*

---

## 📋 Règles d'opération

### ⚠️ IMPORTANT — Approbation requise
**Aucune recherche de leads ne se lance sans l'accord explicite de Laetitia.**
- Les crons automatiques (prospect 8h) sont désactivés
- Seul `search` déclenché manuellement ou via ce bot est autorisé
- `followup` et `sendemails` tournent en automatique (pas de coût API Maps)

### Budget par recherche
- Max 20 leads par commande `search`
- Max 30 leads pour le cron `prospect` si réactivé
- Toujours confirmer avant de lancer si > 20 leads

### Avant de lancer une recherche, demander :
1. Quel secteur / persona ?
2. Quelle zone géographique ?
3. Combien de leads maximum ?
4. Quel message / angle d'approche ?

---

## 📊 Historique des tests

| Date | Persona | Zone | Leads | Emails trouvés | Réponses | Verdict |
|---|---|---|---|---|---|---|
| 2026-05-27 | Garage/voiture/moto | Rousset, Trets | ~20 | 8 | ? | ⚠️ peu d'emails |
| — | — | — | — | — | — | — |

*Mettre à jour après chaque campagne.*

---

## 🗓️ Log des décisions stratégiques

| Date | Décision | Raison |
|---|---|---|
| 2026-05-27 | Focus menuiseries + électricité solaire | Expertise Laetitia, besoin prouvé |
| 2026-05-27 | Profil cible : 20-25 salariés, ~1M€ CA | Taille idéale : douleur max, budget suffisant |
| 2026-05-27 | Stop garages | Trop peu d'emails publics |
| 2026-05-27 | Désactivation cron automatique | Contrôle budget, pilotage via OpenClaw |
| 2026-05-27 | Email avant qualification Claude | Éviter dépense tokens sans email |

---

## 💡 Comment travailler avec Laetitia

- Elle réfléchit avant d'agir — ne pas mettre la pression
- Elle est praticienne : elle veut des exemples concrets, pas de la théorie
- Elle a une vraie expertise terrain (10+ ans menuiserie, 3 ans solaire)
- Quand elle dit "je réfléchis" → attendre son signal GO
- Toujours lui demander AVANT de lancer une campagne
- Lui proposer des options courtes avec pros/cons, pas des listes infinies

---

## 🔧 Infrastructure technique

- **VPS** : Hostinger Ubuntu 24.04 — 187.124.38.54
- **Code** : /home/openclaw/prospection/
- **Venv** : /home/openclaw/prospection/venv/
- **GitHub** : https://github.com/mia-intelligence/agent-prospection-mia
- **Airtable** : MIA_Prospection_V1, table "Prospects"
- **Email** : Brevo, expéditeur contact@mia-intelligence.com
- **Calendly** : https://calendly.com/mia-intelligence/audit-act-ia

### Commandes disponibles
```bash
python main.py prospect          # prospection quotidienne (DÉSACTIVÉ — cron off)
python main.py followup          # relances automatiques J+3, J+5, J+7
python main.py sendemails        # envoie les emails en attente (leads enrichis)
python main.py report            # rapport hebdomadaire
python main.py search S Z        # recherche manuelle secteurs S dans zones Z
python main.py enrich            # enrichit les leads sans email dans Airtable
```
