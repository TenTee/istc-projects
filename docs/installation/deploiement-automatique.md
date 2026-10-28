# Livraison automatique du backend

Le script `outils/deploiement/deployer_backend.sh` installe l'API SmartCampus sur un **serveur neuf** et la met à jour lors des livraisons suivantes. Une seule commande suffit, et le script affiche un résumé à la fin.

Systèmes pris en charge : **Ubuntu 22.04 / 24.04** et les **images Bitnami** (Debian).

## Ce que fait le script

| Étape | Première installation | Livraisons suivantes |
|---|---|---|
| Paquets système (Python ≥ 3.11, Git, Nginx, client PostgreSQL…) | installés | vérifiés |
| Compte système qui exécute l'API | créé si besoin (`smartcampus`, ou le propriétaire du dossier cloné) | — |
| Code | `git pull` de la branche `main` | `git pull` (relance automatique si le script a changé) |
| Base de données | **sur le serveur** si aucune adresse n'est donnée, sinon base distante testée | conservée |
| `back-istc/.env` | créé : clé secrète générée, `DEBUG=False`, hôtes, base, CORS | complété, jamais écrasé |
| Dépendances Python (+ Gunicorn) | installées dans `back-istc/.venv` (le dossier `venv/` du dépôt n'est pas utilisé) | mises à jour |
| Sauvegarde de sécurité | — | **avant** les migrations |
| `migrate`, `collectstatic` | oui | oui |
| Compte administrateur | demandé s'il n'en existe aucun | — |
| Service `smartcampus-api` (Gunicorn, démarrage automatique) | créé et démarré | redémarré |
| Serveur web | Nginx (Ubuntu) ou Apache (Bitnami) | régénéré |
| HTTPS | certificat Let's Encrypt automatique si un domaine est donné (Ubuntu) | renouvellement automatique |
| Sauvegarde de la base chaque nuit à 2 h | planifiée | — |

## Première installation

1. Faites pointer le domaine de l'API vers l'adresse du serveur (enregistrement DNS de type A, par exemple `api.ecole.cm`). Sans domaine, l'API sera joignable par l'adresse IP, en HTTP.
2. Connectez-vous au serveur en SSH, puis :

    ```bash
    sudo git clone <adresse-du-dépôt> /opt/smartcampus     # Bitnami : /home/bitnami/istc-projects
    cd /opt/smartcampus
    sudo bash outils/deploiement/deployer_backend.sh
    ```

3. Répondez aux questions. Appuyez sur ++enter++ pour laisser vide.

| Question | Si vous laissez vide |
|---|---|
| Nom de domaine de l'API | accès par l'adresse IP, sans HTTPS |
| E-mail pour le certificat HTTPS | certificat sans e-mail d'alerte |
| Adresse d'une base PostgreSQL distante | **PostgreSQL est installé sur ce serveur**, avec une base et un mot de passe générés |
| Adresse(s) de l'interface web | à renseigner plus tard (`CORS_ALLOWED_ORIGINS` dans `.env`) |

Les réponses sont mémorisées dans `/etc/smartcampus/deploiement.conf`.

!!! tip "Sans aucune question"
    ```bash
    sudo SMARTCAMPUS_ADMIN_PASSWORD='MotDePasseFort' bash outils/deploiement/deployer_backend.sh --oui \
         --domaine api.ecole.cm --email admin@ecole.cm \
         --frontend https://ecole.cm \
         --superutilisateur admin:admin@ecole.cm
    ```
    Ajoutez `--bd postgresql://utilisateur:motdepasse@hote:5432/base` pour une base distante, et `--bd-ssl` si elle exige SSL. `sudo bash outils/deploiement/deployer_backend.sh --aide` liste toutes les options.

## Livraisons suivantes

Après un push sur `main`, relancez simplement :

```bash
cd /opt/smartcampus && sudo bash outils/deploiement/deployer_backend.sh
```

Le script ne pose plus de questions. Il ne modifie ni les secrets ni la base : il sauvegarde, met à jour le code et les dépendances, migre, puis redémarre. La version livrée s'affiche dans le résumé.

## Base de données locale ou distante

- **Locale (par défaut)** :
    - PostgreSQL est installé sur le serveur ;
    - le rôle et la base `smartcampus` sont créés, avec un mot de passe aléatoire de 32 caractères ;
    - l'adresse complète est enregistrée dans `back-istc/.env` (`DATABASE_URL`, fichier lisible seulement par le compte de l'API).
- **Distante** (`--bd …`, ou réponse à la question) :
    - la connexion est testée **avant** toute modification, et le script s'arrête si la base est injoignable ;
    - la base distante doit déjà exister, et son pare-feu doit accepter l'adresse du serveur.

!!! warning "Sauvegardes"
    La sauvegarde nocturne reste sur le serveur (`back-istc/backups/postgres/`, 30 jours). Copiez régulièrement ce dossier ailleurs (voir [Sauvegardes](sauvegardes.md)). Pour une base distante, le client `pg_dump` du serveur doit être d'une version égale ou supérieure à celle de la base.

## Dépôt privé

Le compte de l'API (`smartcampus` ou le propriétaire du dossier) doit pouvoir faire `git fetch` :

- **Clé de déploiement** :
    - générez la clé sur le serveur : `sudo -u smartcampus ssh-keygen -t ed25519` ;
    - ajoutez le contenu de `/home/smartcampus/.ssh/id_ed25519.pub` dans GitHub → *Settings → Deploy keys* ;
    - clonez avec l'adresse SSH `git@github.com:…`.
- **Jeton d'accès en lecture**, dans l'adresse de clonage : `https://<jeton>@github.com/…`.

## Bitnami

- Apache occupe déjà les ports 80 et 443. Le script crée l'hôte virtuel `/opt/bitnami/apache/conf/vhosts/smartcampus-api-vhost.conf`.
- Le HTTPS se configure ensuite avec l'outil Bitnami : `sudo /opt/bitnami/bncert-tool`. Le script le rappelle à la fin.

## En cas de problème

| Message | Cause probable |
|---|---|
| « Connexion impossible à la base distante » | Adresse, mot de passe, ou pare-feu de la base |
| « git fetch impossible » | Dépôt privé sans clé de déploiement (voir plus haut) |
| « Des modifications locales empêchent la mise à jour » | Un fichier du dépôt a été modifié sur le serveur : `git -C /opt/smartcampus status` |
| « L'API ne répond pas » | Voir `journalctl -u smartcampus-api -n 50 --no-pager` |
| « Certificat HTTPS non obtenu » | Le domaine ne pointe pas encore vers le serveur : relancer le script une fois le DNS propagé |

Le journal complet de chaque livraison est dans `/var/log/smartcampus/`. Pour l'interface (frontend), voir [Mise en ligne sur un serveur](deploiement-serveur.md#5-frontend-interface) : son `NEXT_PUBLIC_API_BASE_URL` doit être l'adresse affichée dans le résumé.
