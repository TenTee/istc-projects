# Installation sur un poste (test)

Cette installation sert à **essayer** SmartCampus, à former les utilisateurs ou à développer. Elle utilise une base SQLite (un simple fichier), sans configuration.

## 1. Récupérer le code

```bash
git clone <adresse-du-dépôt> istc-projects
cd istc-projects
```

## 2. Démarrer le backend (API)

=== "Mac / Linux"

    ```bash
    cd back-istc
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    ```

=== "Windows"

    ```powershell
    cd back-istc
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env
    ```

Ouvrez le fichier `.env` avec un éditeur de texte et, pour un essai, mettez :

```ini
DEBUG=True
DATABASE_URL=
RECAPTCHA_SECRET_KEY=
```

(`DATABASE_URL` vide = base SQLite `db.sqlite3` créée automatiquement.)

Créez la base et le premier administrateur :

```bash
python manage.py migrate
python manage.py createsuperuser
```

Répondez aux questions (nom d'utilisateur, email, mot de passe). **Ce compte est le super-administrateur** : il a accès à tout, y compris aux années archivées.

Lancez le serveur :

```bash
python manage.py runserver
```

Laissez cette fenêtre ouverte. Vérifiez <http://127.0.0.1:8000/api/docs/> : la documentation de l'API doit s'afficher.

## 3. Démarrer le frontend (interface)

Dans une **deuxième** fenêtre de terminal :

```bash
cd frontend
npm install
cp .env.example .env.local      # Windows : copy .env.example .env.local
npm run dev
```

Vérifiez que `.env.local` contient `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.

Ouvrez <http://localhost:3000> et connectez-vous avec le super-administrateur créé plus haut.

## 4. Premiers réglages

Suivez [l'ordre de mise en service](../guide/index.md#ordre-conseille-pour-une-premiere-mise-en-service) du guide d'utilisation.

!!! tip "Données de démonstration"
    Le dossier `back-istc/scripts/` contient des scripts de remplissage (`populate_dummy_data.py`, `populate_finances.py`, `populate_trainers.py`). Ne les utilisez **jamais** sur la base de production : certains effacent des données existantes.

## Arrêter / relancer

- Arrêter : ++ctrl+c++ dans chaque fenêtre de terminal.
- Relancer : refaire `source venv/bin/activate` (ou `venv\Scripts\activate`) puis `python manage.py runserver` dans `back-istc`, et `npm run dev` dans `frontend`.
