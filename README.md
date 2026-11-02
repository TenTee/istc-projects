# SmartCampus

Plateforme de gestion d'établissement de formation (école, institut, centre de formation).

- **Administration** : préinscriptions en ligne, dossiers étudiants, discipline, structure académique, cours, emplois du temps, notes et relevés, assiduité, scolarité (paiements, reçus et factures PDF, échéanciers, bourses), paie du personnel et des formateurs, heures des vacataires, inventaire, congés.
- **Portail formateur** : classes, saisie des notes, emploi du temps, épreuves, heures, coordination de filière.
- **Portail étudiant** : scolarité et reçus, notes, emploi du temps, documents de cours, assiduité, discipline.

Ce document permet à un développeur qui découvre le projet de l'installer, de le comprendre, de le modifier et de le livrer. Le détail est dans [`docs/`](docs/index.md) ; chaque section ci-dessous renvoie vers la page complète.

---

## Sommaire

1. [En bref](#1-en-bref)
2. [Organisation du dépôt](#2-organisation-du-dépôt)
3. [Installer le projet sur son poste](#3-installer-le-projet-sur-son-poste)
4. [Configuration (`.env`)](#4-configuration-env)
5. [Architecture](#5-architecture)
6. [Tests et qualité](#6-tests-et-qualité)
7. [Travailler au quotidien](#7-travailler-au-quotidien)
8. [Versions et livraison](#8-versions-et-livraison)
9. [Exploitation du serveur](#9-exploitation-du-serveur)
10. [Documentation](#10-documentation)
11. [Points d'attention et dette technique](#11-points-dattention-et-dette-technique)
12. [Passation : accès à transmettre](#12-passation--accès-à-transmettre)

---

## 1. En bref

| | |
|---|---|
| **Backend (API)** | Python 3.11+ (3.12 en CI), Django 5.2, Django REST Framework, SimpleJWT, django-filter, drf-spectacular, ReportLab (PDF) — dossier [`back-istc/`](back-istc/) |
| **Frontend** | Node 20+, Next.js 16 (App Router), React 19, MUI 5, axios, react-hook-form + yup, recharts, jsPDF, xlsx — dossier [`frontend/`](frontend/) |
| **Base de données** | PostgreSQL en production, SQLite en développement et pour les tests |
| **Authentification** | JWT (access + refresh) ; rôles avec droits par domaine contrôlés **par le serveur** |
| **Hébergement** | Frontend sur **Vercel** (déploiement automatique à chaque push sur `main`) ; API sur un serveur Linux (Ubuntu ou Bitnami) via le script [`outils/deploiement/deployer_backend.sh`](outils/deploiement/deployer_backend.sh) |
| **API de production** | `https://back.smartcampus.isare-istc.education` (définie dans [`frontend/api-cibles.json`](frontend/api-cibles.json)) |
| **Documentation de l'API** | `/api/docs/` (Swagger) et `/api/redoc/` sur toute instance de l'API |
| **Versionnage** | Automatique : chaque push sur `main` crée une version `X.Y.Z` affichée en bas du menu latéral ([§ 8](#8-versions-et-livraison)) |
| **Dépôt** | `https://github.com/TenTee/istc-projects`, branche principale `main` |

---

## 2. Organisation du dépôt

```text
istc-projects/
├── back-istc/                 API Django
│   ├── smart_back/            projet : settings.py, urls.py, testing.py (fabriques de test), celery.py
│   ├── users/                 comptes, rôles, login JWT, « Mon profil », middlewares de droits
│   ├── academique/            structure, années, préinscriptions, inscriptions, épreuves, configuration établissement
│   ├── etudiants/             dossiers étudiants, portail étudiant, sanctions disciplinaires
│   ├── formateurs/            formateurs, comptes, API du portail formateur
│   ├── paiements/             frais, paiements, échéanciers, bourses, reçus / factures PDF, corrections
│   ├── notes/ modules/ emploidutemps/ assiduite/ vacations/ paie/ personnels/ conges/
│   ├── inventaires/ demandes/ revenus/ depenses/ communication/ files/ logs/
│   ├── admin_api/             ancienne API non branchée (à supprimer)
│   ├── tests/                 tests de flux de bout en bout (pytest)
│   ├── scripts/               sauvegarde PostgreSQL ; scripts de données factices (jamais en production)
│   └── requirements.txt
├── frontend/                  interface Next.js
│   ├── src/app/(dashboard)/   pages de l'administration
│   ├── src/app/(formateur-portal)/  portail formateur
│   ├── src/app/(portal)/      portail étudiant
│   ├── src/app/login, src/app/preinscription   pages publiques
│   ├── src/components/        composants par domaine (finances/, discipline/, students/, layout/, common/…)
│   ├── src/services/api/      client.js (axios + jetons), endpoints.js, services.js
│   ├── src/config/            routes.js (menus), versions.json (historique des versions)
│   ├── scripts/build-cible.mjs   build avec l'adresse d'API choisie
│   └── api-cibles.json        adresses d'API par cible de build
├── docs/                      documentation MkDocs : guide/, installation/, developpeurs/
├── outils/
│   ├── deploiement/           livraison automatique du backend (+ tests du script)
│   ├── version/               versionnage automatique (versionner.py + tests)
│   ├── demo/                  démo locale avec données fictives, outil de captures d'écran
│   └── doc-word/              génération de la documentation Word à partir de docs/
├── .github/workflows/         ci.yml (tests, lint, build, docs) ; version.yml (versionnage)
├── NOUVEAUTES.md              nouveautés de la prochaine livraison (à remplir avant de pousser)
├── CHANGELOG.md, VERSION      tenus à jour par le robot de versionnage
├── CONTRIBUTING.md            règles de contribution
└── mkdocs.yml                 configuration du site de documentation
```

La carte détaillée des applications et de leurs routes : [`docs/developpeurs/applications.md`](docs/developpeurs/applications.md).

---

## 3. Installer le projet sur son poste

Prérequis : **Git**, **Python 3.11 ou plus** (3.12 conseillé), **Node.js 20 ou plus**. PostgreSQL n'est pas nécessaire en développement.

### 3.1 API (terminal 1)

```bash
git clone https://github.com/TenTee/istc-projects.git
cd istc-projects/back-istc
python3 -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Dans `back-istc/.env`, pour le développement :

```ini
SECRET_KEY=une-cle-de-dev-quelconque
DEBUG=True
DATABASE_URL=                 # vide = SQLite (back-istc/db.sqlite3)
RECAPTCHA_SECRET_KEY=         # vide = pas de reCAPTCHA
```

Puis :

```bash
python manage.py migrate
python manage.py creer_superadmin      # nom, e-mail, mot de passe (sans écho), rôle superadmin
python manage.py runserver             # http://127.0.0.1:8000/api/docs/
```

### 3.2 Interface (terminal 2)

```bash
cd istc-projects/frontend
npm ci
cp .env.example .env.local             # NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm run dev                            # http://localhost:3000
```

Connectez-vous avec le super-administrateur créé plus haut.

### 3.3 Démo avec des données fictives (facultatif)

```bash
./outils/demo/lancer_demo.sh           # interface sur :3001, API sur :8001, base outils/demo/demo.sqlite3
./outils/demo/lancer_demo.sh --reset   # repartir d'une démo neuve
```

Comptes `admin.demo`, `formateur.demo`, `etudiant.demo`, mot de passe `Demo2026!`. La démo ne touche pas à votre base de développement. Détails : [`outils/demo/README.md`](outils/demo/README.md).

Guide complet du poste de développement : [`docs/installation/installation-locale.md`](docs/installation/installation-locale.md).

---

## 4. Configuration (`.env`)

### 4.1 API — `back-istc/.env` (modèle : [`.env.example`](back-istc/.env.example))

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | Clé secrète Django. Longue et aléatoire en production ; ne jamais la publier. |
| `DEBUG` | `True` en développement, **`False` en production**. |
| `ALLOWED_HOSTS` | Domaines de l'API, séparés par des virgules (remplace la liste par défaut). |
| `DATABASE_URL` | `postgresql://utilisateur:motdepasse@hote:5432/base`. Vide = SQLite. |
| `DB_SSL_REQUIRE` | `True` si la base distante exige SSL. |
| `CORS_ALLOWED_ORIGINS` | Adresses complètes des interfaces (ex. `https://xxx.vercel.app`), **ajoutées** à celles du code. |
| `RECAPTCHA_SECRET_KEY` | Clé secrète reCAPTCHA v2 (login et préinscription). Vide = vérification désactivée. |
| `CONTROLE_DROITS_PERSONNEL` | `True` (défaut). `False` = interrupteur d'urgence qui coupe le contrôle des droits du personnel. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis pour Celery (facultatif, peu utilisé). |

### 4.2 Interface — `frontend/.env.local` (modèle : [`.env.example`](frontend/.env.example))

| Variable | Rôle |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Adresse de l'API, sans `/api` à la fin. |
| `NEXT_PUBLIC_RECAPTCHA_SITE_KEY` | Clé **publique** reCAPTCHA. Vide = reCAPTCHA masqué. |

Les variables `NEXT_PUBLIC_*` sont **figées au moment du build** : toute modification demande un nouveau build. En production, `npm run build:prod` remplace l'adresse de l'API par celle de [`frontend/api-cibles.json`](frontend/api-cibles.json).

Référence complète : [`docs/installation/configuration.md`](docs/installation/configuration.md).

---

## 5. Architecture

```text
Navigateur (Next.js)  ──axios──►  API Django/DRF  ──►  PostgreSQL
   Authorization: Bearer <jwt>                    └──►  media/ (fichiers envoyés)
   X-Academic-Year: <id de l'année choisie>
```

### 5.1 Parcours d'une requête

1. Le frontend appelle `apiRequest()` ([`frontend/src/services/api/client.js`](frontend/src/services/api/client.js)), qui ajoute le jeton JWT et l'année académique choisie. Sur un 401, il rafraîchit le jeton puis rejoue la requête ; en cas d'échec, il renvoie vers `/login`.
2. Côté Django, les middlewares filtrent avant toute vue :
   - `ArchiveAcademicYearMiddleware` : seule l'année **active** est accessible, sauf pour les super-administrateurs ;
   - `PortalAccessMiddleware` ([`users/middleware.py`](back-istc/users/middleware.py)) : les comptes **étudiant** et **formateur** n'atteignent que les routes de la liste blanche `PORTAL_RULES` ;
   - `StaffAccessMiddleware` ([`users/acces_personnel.py`](back-istc/users/acces_personnel.py)) : pour le personnel, la matrice `REGLES` associe chaque motif d'URL aux domaines requis en lecture et en écriture. **Une route sans règle est réservée aux administrateurs** ;
   - `AcademicYearMiddleware` : rend l'année demandée disponible partout via `get_current_academic_year_id()`.
3. La vue DRF applique `IsAuthenticated`, puis, si besoin, `HasRolePermission` (`users/permissions.py`).

### 5.2 Rôles et droits

- Un **rôle** (`users.Role`) donne à chaque domaine (`etudiants`, `pedagogie`, `finance`, `rh`, `logistique`) le niveau `none`, `lecture` ou `ecriture`. Les administrateurs (`is_superuser` ou rôle admin) ne sont pas limités.
- Le frontend masque les menus et les boutons (`utils/permissions.js`, `components/layout/Sidebar.js`, `app/(dashboard)/layout.js`), mais **la sécurité est assurée par le serveur**.
- `python manage.py audit_droits` liste les droits effectifs de chaque compte.

Détails et matrice testée : [`docs/developpeurs/permissions.md`](docs/developpeurs/permissions.md).

### 5.3 Règles métier centralisées

| Sujet | Où |
|---|---|
| Situation financière d'un étudiant (dû, payé, reste) | `paiements/finance.py::situation_financiere` — **source unique** pour le suivi, le portail et le tableau de bord |
| Correction / suppression de paiement, recalcul des soldes et des tranches, journal | `paiements/corrections.py` |
| Reçus et factures PDF | `paiements/documents_pdf.py` (ReportLab) |
| Note finale (CC + SN ou rattrapage) | `notes/models.py::Note.save()` |
| Règles des créneaux d'emploi du temps | `emploidutemps/models.py::EmploiDuTemps.clean()` |
| Heures des vacataires | `vacations/models.py`, `vacations/services.py` |
| Paie (générer, valider, payer) | `paie/views.py` |
| Congés (jours ouvrés, solde) | `conges/models.py::Conge.save()` |
| Identifiants des comptes (génération, réinitialisation, messages) | `users/utils.py` |

L'**année académique** structure les données : une seule année est active, les classes sont recopiées d'une année à l'autre, et les données annuelles sont filtrées par l'en-tête `X-Academic-Year`.

Pour aller plus loin : [`docs/developpeurs/architecture.md`](docs/developpeurs/architecture.md).

---

## 6. Tests et qualité

```bash
cd back-istc && python -m pytest -q              # ≈ 280 tests (SQLite en mémoire, ~3 min)
cd back-istc && python manage.py makemigrations --check --dry-run   # aucune migration oubliée
cd frontend  && npm run lint && npm run build
python -m pytest outils/version -q && bash outils/deploiement/test_deployer_backend.sh
mkdocs build --strict
```

- Les **tests de flux** (`back-istc/tests/test_flux_*.py`) jouent des parcours complets à travers l'API, avec un vrai jeton JWT, donc **à travers les middlewares de droits** : inscription, notes, paiements et reçus, paie, portails, droits du personnel, identifiants, discipline…
- La fabrique `smart_back/testing.py` fournit `Monde.creer()` (un établissement complet : année, filière, classe, module, administrateur…), `creer_role`, `creer_utilisateur` et `client_api`.
- Le frontend n'a pas de tests automatisés : ESLint et le build sont les seuls garde-fous.
- La **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) lance à chaque push : les tests backend, `makemigrations --check`, le lint et le build du frontend, les tests des outils et le build de la documentation.

Guide : [`docs/developpeurs/tests.md`](docs/developpeurs/tests.md).

---

## 7. Travailler au quotidien

Les règles complètes sont dans [`CONTRIBUTING.md`](CONTRIBUTING.md). Les plus importantes :

1. **Nouvelle route d'API** : ajoutez sa règle dans `REGLES` ([`users/acces_personnel.py`](back-istc/users/acces_personnel.py)).
2. **Route appelée par un portail** : ajoutez-la à `PORTAL_RULES` ([`users/middleware.py`](back-istc/users/middleware.py)) **et** filtrez les données sur l'utilisateur connecté.
3. **Une règle métier vit à un seul endroit** (modèle ou service) ; montants en `Decimal` ; opérations multi-tables dans `transaction.atomic()`.
4. **Modèle modifié** : livrez sa migration (`python manage.py makemigrations`).
5. **Bug corrigé** : ajoutez le test qui échouait avant la correction.
6. **Écran modifié** : mettez à jour la page correspondante de `docs/guide/`, avec les libellés exacts de l'interface.
7. **Avant chaque push sur `main`** : décrivez les nouveautés pour les utilisateurs dans [`NOUVEAUTES.md`](NOUVEAUTES.md).

Pas-à-pas pour ajouter une fonctionnalité : [`docs/developpeurs/ajouter-une-fonctionnalite.md`](docs/developpeurs/ajouter-une-fonctionnalite.md).

---

## 8. Versions et livraison

### 8.1 Chaque push sur `main`…

| Ce qui se passe | Automatique ? |
|---|---|
| La CI vérifie le code | Oui |
| Le robot (`version.yml`) calcule la version, met à jour `VERSION`, `CHANGELOG.md`, `frontend/src/config/versions.json` et `package.json`, vide `NOUVEAUTES.md`, crée l'étiquette `vX.Y.Z` et la Release GitHub | Oui |
| Vercel reconstruit et publie le **frontend** | Oui |
| Le **backend** est mis à jour sur le serveur | **Non** : lancer le script (§ 8.3) |

Après un push, faites `git pull` (ou *Fetch / Pull* dans GitHub Desktop) pour récupérer le commit `chore(version)` du robot avant de continuer à travailler.

Le niveau de version vient de la ligne `Niveau :` de `NOUVEAUTES.md` (`correctif`, `mineure` ou `majeure`), sinon des marqueurs `[mineure]` / `[majeure]` dans les messages de commit. Un commit `[sans version]` ne crée pas de version. Voir [`docs/developpeurs/versions.md`](docs/developpeurs/versions.md).

### 8.2 Frontend (Vercel)

- Projet Vercel relié au dépôt, dossier racine `frontend`.
- Commande de build : `npm run build:prod` (API de production de `api-cibles.json`) ou `npm run build:dev` (API définie par la variable Vercel `NEXT_PUBLIC_API_BASE_URL`).
- L'adresse de l'interface doit figurer dans `CORS_ALLOWED_ORIGINS` du backend.

### 8.3 Backend (serveur Linux)

**Première installation** sur un serveur neuf (Ubuntu 22.04 / 24.04 ou Bitnami) :

```bash
sudo git clone https://github.com/TenTee/istc-projects.git /opt/smartcampus
cd /opt/smartcampus
sudo bash outils/deploiement/deployer_backend.sh --domaine api.exemple.cm --frontend https://interface.exemple.cm
```

Le script installe tout :

- paquets et Python ;
- PostgreSQL **local** (sauf si vous fournissez une base distante avec `--bd`) ;
- le fichier `.env`, généré avec ses secrets ;
- l'environnement virtuel `back-istc/.venv`, puis migrations, fichiers statiques et super-administrateur (demandé) ;
- le service systemd `smartcampus-api` (Gunicorn) ;
- Nginx avec HTTPS Let's Encrypt, ou Apache sur Bitnami ;
- la sauvegarde quotidienne.

Les réponses sont mémorisées dans `/etc/smartcampus/deploiement.conf`.

**Chaque livraison suivante** : relancez **la même commande**, sans faire de `git pull` à la main.

```bash
sudo bash /opt/smartcampus/outils/deploiement/deployer_backend.sh
```

Le script récupère le code, met à jour les dépendances, fait une **sauvegarde avant migration**, applique les migrations et redémarre l'API. Il ne touche ni aux secrets ni aux données. Le journal de chaque livraison est écrit dans `/var/log/smartcampus/`.

Guides : [livraison automatique](docs/installation/deploiement-automatique.md), [installation manuelle d'un serveur](docs/installation/deploiement-serveur.md), [mise à jour](docs/installation/mise-a-jour.md).

---

## 9. Exploitation du serveur

Commandes à lancer sur le serveur, depuis `/opt/smartcampus/back-istc`. Le préfixe `sudo -u "$(stat -c %U .)"` exécute la commande avec le compte propriétaire du dossier, comme le service.

| Besoin | Commande |
|---|---|
| Créer un super-administrateur | `sudo -u "$(stat -c %U .)" .venv/bin/python manage.py creer_superadmin` |
| Changer le mot de passe d'un compte | `sudo -u "$(stat -c %U .)" .venv/bin/python manage.py changepassword <nom>` |
| Lister les droits effectifs | `sudo -u "$(stat -c %U .)" .venv/bin/python manage.py audit_droits` |
| État et redémarrage de l'API | `sudo systemctl status smartcampus-api` · `sudo systemctl restart smartcampus-api` |
| Journaux de l'API | `sudo journalctl -u smartcampus-api -f` |
| Sauvegarde manuelle de la base | `sudo -u "$(stat -c %U .)" bash scripts/backup_cron.sh` (fichiers dans `backups/postgres/`) |

- **Sauvegardes** : une tâche cron (`/etc/cron.d/smartcampus-sauvegarde`) sauvegarde la base chaque nuit à 2 h. Copiez régulièrement `backups/postgres/` **hors du serveur**, avec le dossier `media/` (fichiers envoyés). Voir [`docs/installation/sauvegardes.md`](docs/installation/sauvegardes.md).
- **Certificat HTTPS** : sur Ubuntu, Let's Encrypt (certbot) se renouvelle seul. Sur Bitnami, lancez `sudo /opt/bitnami/bncert-tool`, puis relancez le script de déploiement.
- **Commandes dangereuses**, à ne jamais lancer en production : `purge_except_superusers` (vide la base) et les scripts `scripts/populate_*.py` (données factices).
- **Pannes fréquentes** (CORS, 502, droits refusés, certificat) : [`docs/installation/depannage.md`](docs/installation/depannage.md).

---

## 10. Documentation

| Public | Où |
|---|---|
| Utilisateurs (administration, formateurs, étudiants, candidats) | [`docs/guide/`](docs/guide/index.md), avec les libellés exacts des écrans et des captures |
| Installation et exploitation | [`docs/installation/`](docs/installation/index.md) |
| Développeurs | [`docs/developpeurs/`](docs/developpeurs/index.md) |

```bash
pip install -r requirements-docs.txt
mkdocs serve            # http://127.0.0.1:8000
mkdocs build --strict   # site statique dans site/
```

- **Documentation Word** : `outils/doc-word/construire.sh` génère `docs/SmartCampus_Documentation_complete.docx`.
- **Captures d'écran** : voir `outils/demo/README.md`.
- **Site d'aide interactif** : il est généré par `construire_site.py` dans le dossier **séparé** `smartcampus-aide` (hors de ce dépôt), à partir de `docs/`. Relancez-le après chaque modification de la documentation.

---

## 11. Points d'attention et dette technique

### À traiter en priorité

- **Fichiers qui ne devraient pas être suivis par Git.** Le `.gitignore` empêche d'en ajouter de nouveaux, mais ceux-ci sont encore suivis :
  - `back-istc/.env` (secrets), `back-istc/db.sqlite3`, `back-istc/data.json` et `back-istc/media/` ;
  - les dossiers `__pycache__/` et les fichiers `.DS_Store` ;
  - à la racine : `.claude_sync.*`, `.claude_front.tgz`, `Claude outputs/` et des PDF d'exemple.

  Retirez-les du suivi **sans les effacer du disque** (procédure dans [`CONTRIBUTING.md` § 6](CONTRIBUTING.md)). Considérez ensuite comme divulgués la `SECRET_KEY`, le mot de passe de la base et la clé reCAPTCHA, et changez-les.

### Limites connues

- Changer les pourcentages CC / SN (paramètres globaux) recalcule toutes les notes, **y compris celles des années archivées**.
- Un échéancier créé par l'API `/api/paiements/plans/` sans classe est ignoré par le calcul des retards (`schedule_resolver.py`). Il est en revanche affiché sur la facture.
- Une **exclusion définitive** est inscrite au dossier mais ne désactive pas le compte de l'étudiant.
- `users/signals.py` (envoi des identifiants par e-mail) n'est pas branché : les identifiants sont transmis par copie, WhatsApp ou e-mail depuis l'interface.
- `admin_api/` est une ancienne API non branchée dans `smart_back/urls.py` : à supprimer.
- `users/management/commands/createsu.py` prend le mot de passe en argument (il reste dans l'historique du shell) : préférez `creer_superadmin`.
- Les modèles de relevé de notes et de certificat (`frontend/src/components/grades/`, `certificates/`) contiennent des coordonnées par défaut propres à un établissement. Elles sont utilisées quand la configuration de l'établissement est incomplète.
- Le frontend n'a pas de tests automatisés, et les jetons JWT sont stockés dans `localStorage`.
- Celery est installé mais presque inutilisé ; Redis n'est pas requis.

L'historique détaillé des évolutions se trouve dans [`CHANGELOG.md`](CHANGELOG.md).

---

## 12. Passation : accès à transmettre

Au départ d'un développeur, vérifiez que son successeur reçoit :

| Accès | Usage |
|---|---|
| Dépôt GitHub `TenTee/istc-projects` (droits admin) | Code, Actions (le robot de version a besoin de *Read and write permissions*), Releases |
| Projet **Vercel** du frontend | Variables d'environnement, commande de build, domaines |
| Serveur(s) de l'API : accès SSH avec `sudo` | Livraisons, journaux, sauvegardes |
| Fichier `back-istc/.env` du serveur et `/etc/smartcampus/deploiement.conf` | Secrets en place : à conserver lors d'une migration de serveur |
| Base PostgreSQL (locale ou distante) et ses sauvegardes | Restauration |
| Zone **DNS** des domaines (interface, API) | Nouveaux serveurs, certificats |
| Console **Google reCAPTCHA** | Clés publique et secrète (login, préinscription) |
| Compte super-administrateur de la plateforme | Création des rôles et des comptes |

**Premiers pas conseillés pour le nouveau développeur :**

1. Installer le projet en local (§ 3) et vérifier que les tests passent.
2. Lancer la démo et parcourir les trois espaces.
3. Lire [`CONTRIBUTING.md`](CONTRIBUTING.md), puis [`docs/developpeurs/`](docs/developpeurs/index.md) : architecture, permissions et tests.
4. Faire une première livraison accompagnée : modifier `NOUVEAUTES.md`, pousser, faire un *pull* du commit du robot, puis lancer le script de déploiement sur le serveur.
