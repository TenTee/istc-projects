# Tests automatisés

## Lancer les tests

```bash
cd back-istc
source venv/bin/activate
python -m pytest -q                         # toute la suite (≈ 2 min)
python -m pytest tests/ -q                  # uniquement les tests de flux
python -m pytest tests/test_flux_notes.py   # un fichier
python -m pytest -k rattrapage              # par mot-clé
python -m pytest -x --lf                    # s'arrêter au 1er échec / relancer les échecs
```

La configuration est dans `back-istc/pytest.ini` (`DJANGO_SETTINGS_MODULE=smart_back.settings`). Les tests utilisent une base **SQLite temporaire** créée et détruite automatiquement : laissez `DATABASE_URL` vide (`DATABASE_URL= python -m pytest`) pour ne jamais toucher la base de production.

La CI (`.github/workflows/ci.yml`) lance la suite backend et le lint frontend à chaque push et pull request.

## Organisation

| Emplacement | Type | Contenu |
|---|---|---|
| `back-istc/tests/test_flux_*.py` | **Tests de flux** (API de bout en bout) | Les parcours utilisateurs critiques, écrits comme des scénarios |
| `<app>/tests.py` | Tests unitaires par app | Règles fines d'un modèle ou d'une vue |
| `smart_back/test_audit.py` | Non-régression | Bugs corrigés lors de l'audit |
| `conftest.py` | Fixtures communes | `monde`, `client_admin`, `client_anonyme` ; MEDIA temporaire et reCAPTCHA désactivé automatiquement |
| `smart_back/testing.py` | Fabriques | `Monde`, `creer_role`, `creer_utilisateur`, `client_api` |

### Flux couverts

| Fichier | Parcours |
|---|---|
| `test_flux_authentification.py` | Connexion (bons / mauvais identifiants, compte inactif, formateur sans fiche), droits dans le JWT, jeton périmé, refresh, reCAPTCHA (mock de Google) |
| `test_flux_inscription.py` | Formulaire public, documents, fichier dangereux, doublon, approbation (étudiant + compte + inscription + paiements), bourse à usage unique, réduction 10 %, rejet, inscription directe |
| `test_flux_notes.py` | Saisie, batch-save, bornes CC/SN, lecture seule, visibilité après validation, relevé, rattrapages, changement de pourcentages, saisie par le formateur |
| `test_flux_paiements.py` | Frais, paiements successifs et solde, suivi agrégé = portail (avec réduction), échéancier 4 tranches et imputation, alertes de retard, cloisonnement |
| `test_flux_paie_rh.py` | Campagne complète (prime, CNPS, avance → net, valider, payer, dépense, avance remboursée, campagne payée non supprimable), vacataires, campagne unique / mois, prime ponctuelle, congés (solde, éligibilité, week-end) |
| `test_flux_droits_personnel.py` | Matrice des droits du personnel : domaine refusé sans droit, lecture seule, écriture, lectures croisées, paramètres réservés, rôle inexistant, interrupteur d'urgence, migration des rôles, commande `audit_droits` |
| `test_flux_portails.py` | Chaque route des portails accessible ; toutes les routes d'administration refusées aux comptes portail ; personnel autorisé |
| `test_flux_emploi_du_temps_logistique.py` | Créneaux (pause, journée, conflits, années), visibilité dans les portails, demandes (cycle complet, refus, stock insuffisant), références uniques, attribution / retour d'exemplaire |
| `vacations/tests.py` | Arrondi ¼ h, pointage, clôture, validation, rejet, intégration paie |

## Écrire un test de flux

La fixture `monde` fournit un établissement prêt à l'emploi : année active `2026-2027`, filière, cycle, niveau, **classe** (créée par signal), module (coefficient 2), salle et un compte admin.

```python
import pytest
from smart_back.testing import client_api, creer_role, creer_utilisateur

pytestmark = pytest.mark.django_db


def test_un_secretaire_peut_lire_mais_pas_modifier_les_notes(monde):
    creer_role("secretaire", pedagogie="lecture")
    secretaire = creer_utilisateur(role="secretaire")
    etudiant = monde.nouvel_etudiant()                 # inscrit dans monde.classe

    client = client_api(secretaire)                    # client authentifié par JWT réel
    assert client.get("/api/notes/").status_code == 200
    res = client.post("/api/notes/", {"etudiant": etudiant.id, "module": monde.module.id,
                                      "note_cc": 20}, format="json")
    assert res.status_code == 403
```

Fabriques disponibles sur `monde` :

| Méthode | Crée |
|---|---|
| `monde.nouvel_etudiant(inscrire=True, **champs)` | Étudiant (+ compte portail, + inscription dans `monde.classe`) |
| `monde.nouveau_formateur(vacataire=False, avec_compte=True, **champs)` | Formateur (permanent ou vacataire, avec compte `formateur`) |
| `monde.nouveau_personnel(**champs)` | Membre du personnel |
| `monde.nouvelle_seance(formateur, jour="Lundi", debut=time(8), fin=time(10))` | Créneau d'emploi du temps |
| `monde.client_pour(user)` / `monde.client_admin()` | Client API authentifié |

Fonctions : `creer_role(code, etudiants=…, pedagogie=…, finance=…, logistique=…, rh=…)`, `creer_utilisateur(role="admin", **champs)`, `client_api(user=None, annee=None)` (`annee` ajoute l'en-tête `X-Academic-Year`).

## Bonnes pratiques

- **Un test = un comportement**, nommé en français (`test_une_bourse_ne_sert_qu_une_fois`).
- Testez via **l'API** (comme le frontend), pas en appelant les fonctions internes, sauf pour une règle de calcul pure.
- Vérifiez les **effets** (base de données, statuts, soldes), pas seulement le code HTTP.
- Tout bug corrigé reçoit un test qui échouait avant la correction.
- Toute nouvelle route de portail est ajoutée à `ROUTES_ETUDIANT` / `ROUTES_FORMATEUR` ; toute nouvelle route d'administration à `ROUTES_ADMINISTRATION`.
- Pas d'appel réseau réel : moquez (`unittest.mock.patch`), comme pour reCAPTCHA.

## Frontend

Il n'y a pas encore de tests automatisés côté frontend. Le filet de sécurité actuel est :

1. `npm run lint` (ESLint `eslint-config-next`), exécuté par la CI ;
2. `npm run build`, qui détecte les erreurs d'import et de syntaxe ;
3. les tests de flux backend, qui garantissent que chaque route appelée par les portails répond.

Piste d'évolution : ajouter Playwright (déjà compatible avec Next.js) pour 3 ou 4 parcours écran (connexion, saisie de notes, paiement).
