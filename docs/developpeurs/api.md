# Référence API

## Documentation interactive

Générée automatiquement à partir du code (drf-spectacular) :

- Swagger : `/api/docs/`
- ReDoc : `/api/redoc/`
- Schéma OpenAPI : `/api/schema/`

## Authentification

```http
POST /api/auth/login/
Content-Type: application/json

{"username": "ngono.alice482", "password": "…", "recaptcha_token": "…"}
```

Réponse : `{"access": "<jwt>", "refresh": "<jwt>", …}`. Le JWT contient le rôle et les droits (`permissions`).

Appels suivants :

```http
Authorization: Bearer <access>
X-Academic-Year: <id de l'année>     # facultatif ; année active par défaut
```

Renouvellement : `POST /api/auth/token/refresh/` avec `{"refresh": "<jwt>"}`.

Durées : accès 16 h, rafraîchissement 1 jour (`SIMPLE_JWT` dans `settings.py`).

## Codes de réponse

| Code | Signification |
|---|---|
| 200 / 201 / 204 | Succès |
| 400 | Données invalides : le corps indique le champ (`{"note_cc": ["…"]}`) ou `non_field_errors` / `error` / `detail` |
| 401 | Jeton absent, invalide ou expiré |
| 403 | Droit insuffisant, route hors portail, ou année archivée |
| 404 | Ressource inexistante ou hors de votre périmètre |

## Principaux endpoints

| Domaine | Endpoints |
|---|---|
| Comptes | `/api/auth/` (CRUD admin), `/api/auth/{id}/reset-password/`, `/api/auth/roles/` |
| Structure | `/api/v2/filieres/`, `specialites/`, `cycles/`, `cycles-globaux/`, `levels/`, `classes/`, `annees-academiques/`, `semestres/`, `parametres-globaux/`, `configuration-etablissement/current/` ; salles : `/api/salles/` |
| Préinscription | `POST /api/v2/pre-inscriptions/` (public), `…/{id}/approve/`, `…/{id}/reject/` |
| Étudiants | `/api/etudiants/`, `/api/etudiants/me/`, `me/situation/`, `me/history/`, `portal/carte-etudiant/`, `portal/certificat-scolarite/` |
| Formateurs | `/api/formateurs/`, `/api/formateurs/portal/{me,dashboard,mes-classes,mon-emploi-du-temps,mes-notes,mon-suivi,mes-epreuves}/` |
| Emploi du temps | `/api/emploi-du-temps/`, `…/me/`, `/api/emploi-du-temps-documents/` |
| Notes | `/api/notes/`, `saisie-groupee/`, `batch-save/`, `valider/`, `devalider/`, `rattrapages/`, `me/`, `{id}/releve-notes/` |
| Scolarité | `/api/paiements/`, `aggregated/`, `me/`, `plans/`, `alerts/`, `dashboard/`, `/api/v2/frais/` |
| Paie | `/api/paie/campagnes/` (+ `generer/`, `{id}/valider/`, `{id}/payer/`), `bulletins/`, primes, retenues, avances |
| Vacations | `/api/vacations/coordonnateur/…`, `pointages/`, `recaps/` (+ `{id}/valider/`, `{id}/rejeter/`), `mes-heures/` |
| RH | `/api/personnels/`, `/api/conges/` |
| Logistique | `/api/inventaires/articles/` (+ `ajouter_stock/`), `exemplaires/` (+ `attribuer/`, `retourner/`), `/api/demandes/` (+ `soumettre/`, `approuver/`, `refuser/`, `livrer/`) |
| Trésorerie | `/api/revenus/`, `/api/depenses/` |

La liste exhaustive et les schémas de données sont dans Swagger.
