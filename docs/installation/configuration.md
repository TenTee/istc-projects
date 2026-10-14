# Fichier de configuration (.env)

Les réglages propres à chaque installation (mots de passe, adresses) ne sont **pas** dans le code : ils sont dans des fichiers `.env`, à créer à partir des modèles fournis. **Ne partagez jamais ces fichiers** et ne les envoyez pas dans Git (ils sont déjà exclus).

Après toute modification :

- backend : redémarrez l'API (`sudo systemctl restart smartcampus-api`) ;
- frontend : reconstruisez (`npm run build`) puis redémarrez (`sudo systemctl restart smartcampus-web`).

## Backend — `back-istc/.env`

Modèle : `back-istc/.env.example`.

| Variable | Obligatoire en production | Exemple | Rôle |
|---|---|---|---|
| `SECRET_KEY` | **Oui** | `k3J…` (50 caractères aléatoires) | Clé de chiffrement des sessions et jetons. Unique par installation, à ne jamais divulguer. La changer déconnecte tout le monde. |
| `DEBUG` | **Oui** (`False`) | `False` | `True` uniquement sur un poste de test : affiche le détail des erreurs (dangereux en ligne). |
| `ALLOWED_HOSTS` | **Oui** | `api.istc.exemple.cm,istc.exemple.cm` | Noms de domaine autorisés pour joindre l'API, séparés par des virgules, **sans** `https://`. Si la variable est absente, une liste par défaut (localhost, istc.tenteeglobal.com, smart.tenteeglobal.com) est utilisée ; si elle est présente, **elle remplace** cette liste. Les origines HTTPS de confiance (CSRF) en sont déduites automatiquement. |
| `DATABASE_URL` | **Oui** | `postgresql://utilisateur:motdepasse@127.0.0.1:5432/smartcampus` | Connexion à PostgreSQL. Vide = base SQLite locale (`db.sqlite3`), réservée aux essais. |
| `DB_SSL_REQUIRE` | Non | `False` | `True` si la base est hébergée chez un fournisseur exigeant SSL. |
| `CORS_ALLOWED_ORIGINS` | Selon le cas | `https://istc.exemple.cm` | Adresses **complètes** (avec `https://`) des interfaces autorisées à appeler l'API, séparées par des virgules. Elles **s'ajoutent** aux adresses déjà autorisées dans le code (localhost:3000, istc.tenteeglobal.com, smart.tenteeglobal.com, istc-smartcampus.vercel.app). |
| `RECAPTCHA_SECRET_KEY` | Recommandé | `6Lc…` | Clé **secrète** reCAPTCHA v2. Si renseignée, la connexion et la préinscription exigent le reCAPTCHA. Vide = pas de vérification. |
| `CONTROLE_DROITS_PERSONNEL` | Non | `True` | Contrôle des droits du personnel par le serveur (activé par défaut). `False` le désactive temporairement en cas de blocage après une mise à jour, le temps de corriger les rôles. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Non | `redis://127.0.0.1:6379/0` | Tâches en arrière-plan (facultatif, non nécessaire au fonctionnement courant). |

!!! danger "Erreur « Hôte interdit » / DisallowedHost"
    Si le domaine utilisé par les navigateurs n'est pas dans `ALLOWED_HOSTS`, toutes les requêtes échouent (« Invalid HTTP_HOST header »). Ajoutez le domaine, sans `https://` ni `/`, puis redémarrez l'API. Voir [Dépannage](depannage.md#hote-interdit-disallowedhost).

## Frontend — `frontend/.env.local`

Modèle : `frontend/.env.example`.

| Variable | Exemple | Rôle |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://api.istc.exemple.cm` | Adresse de l'API, **sans** `/api` et sans `/` final. |
| `NEXT_PUBLIC_RECAPTCHA_SITE_KEY` | `6Lc…` | Clé **du site** (publique) reCAPTCHA v2. Doit correspondre à la clé secrète du backend. Vide = reCAPTCHA masqué. |

!!! warning "reCAPTCHA : les deux clés vont ensemble"
    Si `RECAPTCHA_SECRET_KEY` est renseignée côté backend mais que `NEXT_PUBLIC_RECAPTCHA_SITE_KEY` est vide côté frontend, **personne ne peut plus se connecter** (la case n'est pas affichée mais le serveur l'exige). Renseignez les deux, ou aucune.

## Réglages faits dans l'application (pas dans .env)

Ces réglages se font par un administrateur dans l'interface, sans toucher au serveur :

| Réglage | Où |
|---|---|
| Nom, logos, couleurs, coordonnées, directeur, signature | **Système** → *Apparence & École* |
| Horaires de journée et de pause par cycle | **Système** → *Paramètres Globaux* → Cycles Globaux |
| Pourcentages CC / SN | **Système** → *Paramètres Globaux* → Calcul des Notes |
| Rôles et droits | **Système** → *Rôles* |
| Année académique active | **Pédagogie** → Structure Académique → *Années Académiques* |

## Durée des sessions

Définie dans `back-istc/smart_back/settings.py` (`SIMPLE_JWT`) : jeton d'accès valable **16 heures**, renouvelable pendant **1 jour**. Au-delà, l'utilisateur doit se reconnecter.
