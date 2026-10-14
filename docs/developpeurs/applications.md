# Carte des applications

## Backend (`back-istc/`)

| App | Préfixe d'URL | Responsabilité |
|---|---|---|
| `smart_back` | — | Projet : `settings.py`, `urls.py`, `testing.py` (fabriques de test), `test_audit.py` |
| `users` | `/api/auth/` | `CustomUser` (username/mot de passe générés), `Role` (5 domaines × none/lecture/ecriture), login JWT, reCAPTCHA (`recaptcha.py`), `PortalAccessMiddleware`, `permissions.py` |
| `academique` | `/api/v2/` | Structure (universités, départements, filières, spécialités, cycles, niveaux, classes, années, salles), `ParametresGlobaux`, `CycleGlobal`, préinscriptions (+ approbation), inscriptions, épreuves, affectations, configuration établissement, middlewares d'année |
| `etudiants` | `/api/etudiants/` | Dossier étudiant (matricule auto), `Inscription`, sanctions, portail (`me/`, situation, historique, carte, certificat) |
| `formateurs` | `/api/formateurs/` | Formateurs (permanent / vacataire), comptes portail, **API du portail formateur** (`portal/…`), documents de cours |
| `modules` | `/api/modules/` | Cours / modules (coefficient, semestre, classes rattachées) |
| `emploidutemps` | `/api/emploi-du-temps/` | Créneaux + règles (`clean()`), documents d'emploi du temps officiels |
| `notes` | `/api/notes/` | Notes (CC / SN / rattrapage), saisie groupée, validation, relevés, rattrapages, portail (`me/`) |
| `assiduite` | `/api/assiduite/` | Absences et retards des étudiants |
| `paiements` | `/api/paiements/`, `/api/v2/frais/` … | Frais, paiements, bourses, réductions, échéanciers (classe / filière / étudiant), alertes, tableau de bord, `finance.py` |
| `paie` | `/api/paie/` | Primes, retenues, avances, campagnes, bulletins, statistiques |
| `vacations` | `/api/vacations/` | Coordinations de filière, pointages, récaps mensuels, validation finance, « mes heures » |
| `personnels` | `/api/personnels/` | Personnel non enseignant, ancienneté, soldes de congés |
| `conges` | `/api/conges/` | Congés (jours ouvrés, solde) |
| `inventaires` | `/api/inventaires/` | Articles, exemplaires, mouvements |
| `demandes` | `/api/demandes/` | Demandes de matériel (soumettre → approuver → livrer) |
| `revenus`, `depenses` | `/api/revenus/`, `/api/depenses/` | Trésorerie |
| `communication` | `/api/communication/` | Messages / actualités (modèle `Communication`) |
| `files` | `/api/files/` | Fichiers génériques (upload, téléchargement) |
| `logs` | `/api/logs/` | Journal d'activité |
| `admin_api` | — | Ancienne API (students / trainers) **non branchée** dans `smart_back/urls.py` : candidate à la suppression |
| `tests/` | — | **Tests de flux** de bout en bout (voir [Tests](tests.md)) |
| `scripts/` | — | Sauvegarde PostgreSQL, scripts de données de démonstration (ne jamais lancer en prod) |

## Frontend (`frontend/src/`)

| Dossier | Contenu |
|---|---|
| `app/(dashboard)/…` | Pages de l'administration (une page = un dossier `page.js`) |
| `app/(formateur-portal)/formateur-portal/…` | Portail formateur |
| `app/(portal)/portal/…` | Portail étudiant |
| `app/login`, `app/preinscription` | Pages publiques |
| `app/api/media-download/route.js` | Proxy de téléchargement des fichiers |
| `components/layout/` | `Header` (sélecteur d'année, profil), `Sidebar`, `FormateurSidebar`, `StudentSidebar`, `PortalGuard` |
| `components/<domaine>/` | Composants par domaine : `finances/`, `grades/`, `schedule/`, `students/`, `system/`, `settings/`, `vacations/`, `importExport/`, `certificates/` |
| `components/common/` | Squelettes de chargement, `ErrorState`, `SearchableSelect` |
| `services/api/` | `client.js` (axios, intercepteurs, `getMediaUrl`, `clearSession`), `endpoints.js`, `services.js` |
| `config/routes.js` | Menus des trois espaces |
| `utils/permissions.js` | `useUserPermissions`, `hasReadAccess`, rôles admin |
| `context/` | Année académique, barre latérale |
| `theme/` | Thème MUI |
