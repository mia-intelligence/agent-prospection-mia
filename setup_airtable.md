# Configuration Airtable — MIA_Prospection_V1

## Table à créer : "Prospects"

Créer ces champs dans la table (ou adapter si tu en as déjà une partie) :

| Champ | Type Airtable |
|-------|--------------|
| Entreprise | Single line text |
| Secteur | Single line text |
| Zone | Single line text |
| Source | Single select (google_maps / apollo) |
| Prénom | Single line text |
| Nom | Single line text |
| Email | Email |
| Téléphone | Phone number |
| Site web | URL |
| LinkedIn | URL |
| Adresse | Single line text |
| Score Claude | Number (integer) |
| Raison score | Long text |
| Pain point | Single line text |
| Sujet email | Single line text |
| Corps email | Long text |
| Message LinkedIn | Long text |
| Taille entreprise | Single select (petite / moyenne) |
| Audit recommandé | Single select (demi-journée / journée complète) |
| Prix recommandé | Number (350 ou 850) |
| Statut | Single select (voir valeurs ci-dessous) |
| Date ajout | Date |
| Date email initial | Date |
| Date relance 1 | Date |
| Date relance 2 | Date |
| Date LinkedIn | Date |
| LinkedIn envoyé | Checkbox |
| PlaceID | Single line text |
| ApolloID | Single line text |

## Valeurs du champ "Statut"
- Nouveau
- Non qualifié
- Email envoyé
- Relancé
- 2ème relance
- LinkedIn envoyé
- LinkedIn à envoyer manuellement
- Sans email — relance manuelle
- Réponse reçue
- RDV planifié
- Audit réalisé
- Perdu
- Erreur envoi

## Récupérer l'ID de la base
URL Airtable de ta base : https://airtable.com/appXXXXXX/...
L'ID commence par "app" — c'est ta AIRTABLE_BASE_ID.
