# Documentation développeurs

Cette partie s'adresse à l'équipe qui maintient et fait évoluer SmartCampus.

| Page | Contenu |
|---|---|
| [Architecture](architecture.md) | Vue d'ensemble backend / frontend, flux d'une requête, année académique |
| [Carte des applications](applications.md) | À quoi sert chaque app Django et chaque dossier du frontend |
| [Permissions et cloisonnement](permissions.md) | Rôles, `PORTAL_RULES`, années archivées — **à lire avant d'ajouter une route** |
| [Tests automatisés](tests.md) | Lancer les tests, fabriques `Monde`, écrire un test de flux |
| [Ajouter une fonctionnalité](ajouter-une-fonctionnalite.md) | Recette pas à pas (modèle → API → droits → écran → tests → doc) |
| [Conventions de code](conventions.md) | Style, nommage, Git, revue |
| [Référence API](api.md) | Swagger, authentification, en-têtes, principaux endpoints |

## Démarrage rapide

```bash
# Backend
cd back-istc && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # DEBUG=True, DATABASE_URL vide (SQLite)
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver      # http://127.0.0.1:8000/api/docs/

# Frontend
cd frontend && npm install && cp .env.example .env.local && npm run dev   # http://localhost:3000

# Tests et lint (à lancer avant chaque push)
cd back-istc && python -m pytest -q
cd frontend && npm run lint

# Documentation
pip install -r requirements-docs.txt && mkdocs serve   # http://127.0.0.1:8000
```

Voir aussi `CONTRIBUTING.md` à la racine du dépôt.
