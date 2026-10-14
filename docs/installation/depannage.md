# Dépannage

## Où regarder en premier

| Commande | Ce qu'elle montre |
|---|---|
| `sudo systemctl status smartcampus-api` | L'API tourne-t-elle ? |
| `sudo journalctl -u smartcampus-api -n 100 --no-pager` | Les 100 dernières lignes du journal de l'API (erreurs Python) |
| `sudo journalctl -u smartcampus-web -n 100 --no-pager` | Journal du frontend |
| `sudo tail -n 50 /var/log/nginx/error.log` | Erreurs du serveur web |
| Navigateur : ++f12++ → onglet *Console* / *Réseau* | L'erreur exacte renvoyée à l'écran (code 400, 401, 403, 404, 500) |

## Erreurs fréquentes

### Hôte interdit (DisallowedHost)

**Symptôme :** « Invalid HTTP_HOST header: 'istc.exemple.cm' » dans le journal, ou erreur 400 sur toutes les requêtes.

**Cause :** le domaine n'est pas dans `ALLOWED_HOSTS`.

**Solution :** dans `back-istc/.env`, ajoutez le domaine **sans** `https://` :

```ini
ALLOWED_HOSTS=istc.exemple.cm,api.istc.exemple.cm,localhost,127.0.0.1
```

puis `sudo systemctl restart smartcampus-api`.

### Erreur CORS dans la console du navigateur

**Symptôme :** « blocked by CORS policy » ; la page de connexion ne réagit pas.

**Cause :** l'adresse de l'interface n'est pas autorisée par l'API.

**Solution :** `CORS_ALLOWED_ORIGINS=https://istc.exemple.cm` (avec `https://`, sans `/` final) dans `back-istc/.env`, puis redémarrer l'API.

### Impossible de se connecter alors que le mot de passe est bon

1. Le message parle de reCAPTCHA ? Vérifiez que **les deux clés** sont cohérentes ([Configuration](configuration.md#frontend-frontendenvlocal)) et que le serveur peut joindre `www.google.com` (sinon « Vérification reCAPTCHA indisponible »).
2. L'interface appelle-t-elle la bonne API ? Vérifiez `NEXT_PUBLIC_API_BASE_URL` puis **reconstruisez** le frontend.
3. Le compte est-il actif ? (**Système** → *Utilisateurs*.)

### La page tourne indéfiniment après la connexion

- Videz les données du site : ++f12++ → *Application* → *Stockage* → « Effacer les données du site », puis reconnectez-vous.
- Vérifiez que l'année active existe (**Structure Académique** → *Années Académiques*, une année cochée « Est Active »).
- Consultez le journal de l'API à la recherche d'une erreur 500.

### Erreur 500 sur une page après une mise à jour

Presque toujours une migration oubliée :

```bash
cd back-istc && source venv/bin/activate && python manage.py migrate
sudo systemctl restart smartcampus-api
```

### Les photos, logos ou justificatifs ne s'affichent pas (404)

Avec `DEBUG=False`, ces fichiers sont servis par Nginx : vérifiez le bloc `location /media/` ([Mise en ligne](deploiement-serveur.md#6-nginx-adresses-publiques-et-https)) et les droits de lecture du dossier `media/`.

### « Request Entity Too Large » (413) en déposant un fichier

Augmentez `client_max_body_size` dans la configuration Nginx (ex. `25M`), puis `sudo systemctl reload nginx`.

### Les utilisateurs voient des pages vides après le changement d'année

Les années non actives ne sont accessibles qu'au super-administrateur. Demandez aux utilisateurs de choisir l'année *(Active)* dans le sélecteur du haut et de recharger la page.

### « Accès refusé : votre rôle n'a pas le droit … »

Le serveur applique les droits du rôle. Vérifiez le rôle de la personne (**Système** → *Rôles*) et donnez-lui le droit **Lecture** ou **Écriture** sur le domaine indiqué dans le message, puis demandez-lui de se reconnecter.

`python manage.py audit_droits` liste tous les comptes du personnel avec leurs droits et signale ceux qui n'en ont aucun.

En cas de blocage général juste après une mise à jour : `CONTROLE_DROITS_PERSONNEL=False` dans `back-istc/.env`, redémarrer l'API, corriger les rôles, puis remettre `True`.

### Un utilisateur ne voit pas un menu

Ce n'est pas une panne : son rôle n'a pas le droit correspondant. Voir [Rôles et droits d'accès](../guide/roles-et-acces.md).

## Commandes utiles

```bash
cd /home/bitnami/istc-projects/back-istc && source venv/bin/activate

python manage.py check --deploy          # contrôle de la configuration de production
python manage.py createsuperuser         # créer un nouveau super-administrateur
python manage.py changepassword <nom>    # changer le mot de passe d'un compte
python manage.py showmigrations | grep "\[ \]"   # migrations non appliquées
python -m pytest -q                      # lancer les tests automatiques
```

## Interface d'administration technique

`https://api.istc.exemple.cm/admin/` donne accès, pour le **super-administrateur**, à toutes les tables (corrections exceptionnelles, sanctions disciplinaires, paiements). À utiliser avec prudence : les contrôles de l'application n'y sont pas tous appliqués.
