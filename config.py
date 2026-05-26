import os
from dotenv import load_dotenv

load_dotenv()

# APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
PHANTOMBUSTER_API_KEY = os.getenv("PHANTOMBUSTER_API_KEY", "")
PHANTOMBUSTER_AGENT_ID = os.getenv("PHANTOMBUSTER_AGENT_ID", "")

# Expéditeur MIA
MIA_EMAIL = os.getenv("MIA_EMAIL", "contact@mia-intelligence.com")
MIA_NAME = os.getenv("MIA_NAME", "Laetitia Coloré — MIA")
CALENDLY_LINK = os.getenv("CALENDLY_LINK", "https://calendly.com/mia-intelligence/diagnostic-express")

# Paramètres prospection
LEADS_PER_DAY_TARGET = 30          # leads bruts à collecter par jour
MIN_SCORE_TO_CONTACT = 7           # score Claude min (sur 10) pour envoyer un email
FOLLOW_UP_DELAY_DAYS = 3           # délai relance email (jours)
LINKEDIN_DELAY_DAYS = 5            # délai DM LinkedIn après email initial (jours)
SECOND_FOLLOW_UP_DAYS = 7          # délai 2ème relance (offre diagnostic 99€)

# Zones géographiques (Google Maps)
# 4 zones × 10 secteurs = 40 requêtes/run → ~22€ sur 15 jours (budget 50€)
SEARCH_ZONES = [
    "Saint-Maximin-la-Sainte-Baume, France",
    "Toulon, France",
    "Brignoles, France",
    "Hyères, France",
]

# Secteurs cibles pour Google Maps — 10 secteurs les plus rentables pour un audit
TARGET_SECTORS_MAPS = [
    "plombier",
    "électricien",
    "menuisier",
    "coiffeur",
    "auto-école",
    "kinésithérapeute",
    "agence immobilière",
    "garage automobile",
    "comptable",
    "coach",
]

# Secteurs cibles pour Apollo.io
TARGET_SECTORS_APOLLO = [
    "construction",
    "retail",
    "health and wellness",
    "real estate",
    "professional services",
    "education",
    "beauty",
]

APOLLO_EMPLOYEE_RANGE = {"min": 1, "max": 50}
APOLLO_LOCATIONS = ["Var, France", "Bouches-du-Rhône, France", "Alpes-Maritimes, France"]
