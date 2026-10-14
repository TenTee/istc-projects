# Mise en ligne sur un serveur

Ce guide décrit une installation complète sur un serveur **Linux (Ubuntu ou Bitnami)** avec :

- **PostgreSQL** pour la base de données ;
- **Gunicorn** pour faire tourner le backend Django ;
- **Nginx** en frontal (HTTPS, fichiers statiques et fichiers déposés) ;
- le frontend **Next.js** sur le même serveur (ou sur Vercel, voir la fin).

Les exemples utilisent :

| Élément | Valeur d'exemple — à remplacer |
|---|---|
| Utilisateur Linux | `bitnami` |
| Dossier de l'application | `/home/bitnami/istc-projects` |
| Adresse de l'interface | `https://istc.exemple.cm` |
| Adresse de l'API | `https://api.istc.exemple.cm` |
| Base de données / utilisateur | `smartcampus` / `smartcampus` |

!!! tip "Une seule adresse ?"
    Vous pouvez aussi servir l'interface et l'API sur le même domaine (l'API sous `/api/`). Il suffit alors que `NEXT_PUBLIC_API_BASE_URL` soit l'adresse du domaine (voir l'étape 6).

## 1. Paquets système

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git postgresql postgresql-contrib nginx
# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

!!! note "Bitnami"
    Sur une image Bitnami, Apache occupe déjà les ports 80/443. Soit vous utilisez Apache comme frontal (même principe que Nginx ci-dessous : proxy vers Gunicorn et Next.js), soit vous désactivez Apache. Le certificat HTTPS se crée alors avec `sudo /opt/bitnami/bncert-tool`.

## 2. Base de données PostgreSQL

```bash
sudo -u postgres psql
```

Puis, dans l'invite `postgres=#` (choisissez un **mot de passe fort**) :

```sql
CREATE USER smartcampus WITH PASSWORD 'MotDePasseFort';
CREATE DATABASE smartcampus OWNER smartcampus;
\q
```

## 3. Code et backend

```bash
cd /home/bitnami
git clone <adresse-du-dépôt> istc-projects
cd istc-projects/back-istc
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env
nano .env
```

Renseignez au minimum (détails dans [Configuration](configuration.md)) :

```ini
SECRET_KEY=<une longue chaîne aléatoire>
DEBUG=False
ALLOWED_HOSTS=api.istc.exemple.cm,istc.exemple.cm
DATABASE_URL=postgresql://smartcampus:MotDePasseFort@127.0.0.1:5432/smartcampus
CORS_ALLOWED_ORIGINS=https://istc.exemple.cm
RECAPTCHA_SECRET_KEY=<clé secrète reCAPTCHA, ou vide>
```

Générer une `SECRET_KEY` :

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Enregistrez (++ctrl+o++, ++enter++, ++ctrl+x++ dans `nano`), puis :

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py check --deploy
```

## 4. Service Gunicorn (démarrage automatique de l'API)

Créez `/etc/systemd/system/smartcampus-api.service` :

```ini
[Unit]
Description=SmartCampus API (Django/Gunicorn)
After=network.target postgresql.service

[Service]
User=bitnami
WorkingDirectory=/home/bitnami/istc-projects/back-istc
EnvironmentFile=/home/bitnami/istc-projects/back-istc/.env
ExecStart=/home/bitnami/istc-projects/back-istc/venv/bin/gunicorn smart_back.wsgi:application \
          --bind 127.0.0.1:8000 --workers 3 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smartcampus-api
sudo systemctl status smartcampus-api    # doit afficher « active (running) »
```

## 5. Frontend (interface)

```bash
cd /home/bitnami/istc-projects/frontend
cp .env.example .env.local
nano .env.local
```

```ini
NEXT_PUBLIC_API_BASE_URL=https://api.istc.exemple.cm
NEXT_PUBLIC_RECAPTCHA_SITE_KEY=<clé du site reCAPTCHA, ou vide>
```

```bash
npm ci
npm run build
```

!!! warning "Reconstruire après chaque changement de .env.local"
    Les variables `NEXT_PUBLIC_*` sont intégrées au moment du `npm run build`.

Service `/etc/systemd/system/smartcampus-web.service` :

```ini
[Unit]
Description=SmartCampus Web (Next.js)
After=network.target

[Service]
User=bitnami
WorkingDirectory=/home/bitnami/istc-projects/frontend
Environment=NODE_ENV=production PORT=3000
ExecStart=/usr/bin/npm start
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now smartcampus-web
```

## 6. Nginx (adresses publiques et HTTPS)

Créez `/etc/nginx/sites-available/smartcampus` :

```nginx
# API
server {
    server_name api.istc.exemple.cm;
    client_max_body_size 25M;   # taille max des fichiers déposés

    location /static/ { alias /home/bitnami/istc-projects/back-istc/staticfiles/; }
    location /media/  { alias /home/bitnami/istc-projects/back-istc/media/; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Interface
server {
    server_name istc.exemple.cm;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

!!! warning "Fichiers déposés (`/media/`)"
    Avec `DEBUG=False`, Django ne sert plus les photos, justificatifs, documents de cours, etc. C'est le bloc `location /media/` de Nginx qui les sert : sans lui, ces fichiers renvoient une erreur 404.

Activez et ajoutez HTTPS :

```bash
sudo ln -s /etc/nginx/sites-available/smartcampus /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d istc.exemple.cm -d api.istc.exemple.cm
```

Vérifiez que le dossier `media/` est lisible par Nginx (`sudo chmod o+x /home/bitnami /home/bitnami/istc-projects /home/bitnami/istc-projects/back-istc`).

## 7. Vérifications finales

- [ ] <https://api.istc.exemple.cm/api/docs/> affiche la documentation de l'API.
- [ ] <https://istc.exemple.cm> affiche la page de connexion.
- [ ] La connexion avec le super-administrateur fonctionne.
- [ ] Une photo déposée (logo dans **Système** → *Apparence & École*) s'affiche.
- [ ] La [sauvegarde automatique](sauvegardes.md) est en place.

## Variante : frontend sur Vercel

1. Importez le dépôt sur <https://vercel.com>, dossier racine `frontend`.
2. Dans *Settings → Environment Variables*, ajoutez `NEXT_PUBLIC_API_BASE_URL` et `NEXT_PUBLIC_RECAPTCHA_SITE_KEY`.
3. Ajoutez l'adresse Vercel (ex. `https://istc-smartcampus.vercel.app`) dans `CORS_ALLOWED_ORIGINS` du backend, puis redémarrez l'API (`sudo systemctl restart smartcampus-api`).
