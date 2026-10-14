# SmartCampus ISTC

Plateforme de gestion d'établissement de formation : préinscriptions en ligne, dossiers étudiants, structure académique, emplois du temps, notes et relevés, scolarité et paiements, paie du personnel et des formateurs, pointage des heures des vacataires, inventaire, congés. Trois espaces : **administration**, **portail formateur**, **portail étudiant**.

| Dossier | Contenu |
|---|---|
| [`back-istc/`](back-istc/) | API — Django 5.2 / Django REST Framework / JWT |
| [`frontend/`](frontend/) | Interface — Next.js 16 / React 19 / MUI |
| [`docs/`](docs/) | Documentation complète (site MkDocs) : guide d'utilisation, installation, développeurs |

## Documentation

La documentation se lit directement dans `docs/` ou sous forme de site :

```bash
pip install -r requirements-docs.txt
mkdocs serve          # http://127.0.0.1:8000
mkdocs build          # site statique dans site/ (à publier sur n'importe quel hébergeur)
```

| Je suis… | Je lis |
|---|---|
| Utilisateur (administration, formateur, étudiant, candidat) | [`docs/guide/`](docs/guide/index.md) |
| Responsable de l'installation | [`docs/installation/`](docs/installation/index.md) |
| Développeur | [`docs/developpeurs/`](docs/developpeurs/index.md) et [`CONTRIBUTING.md`](CONTRIBUTING.md) |

## Démarrage rapide (développement)

```bash
# API
cd back-istc
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # DEBUG=True et DATABASE_URL vide pour SQLite
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver          # http://127.0.0.1:8000/api/docs/

# Interface (autre terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                         # http://localhost:3000
```

## Qualité

```bash
cd back-istc && python -m pytest -q     # tests de flux + tests unitaires
cd frontend && npm run lint && npm run build
```

La CI GitHub Actions (`.github/workflows/ci.yml`) exécute ces contrôles et la construction de la documentation à chaque push.
