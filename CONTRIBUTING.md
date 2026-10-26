# Contribuer à SmartCampus

Merci de lire ce guide avant votre première contribution. La documentation détaillée est dans [`docs/developpeurs/`](docs/developpeurs/index.md).

## 1. Préparer son poste

Suivez [l'installation locale](docs/installation/installation-locale.md). Vérifiez que tout est vert avant de commencer :

```bash
cd back-istc && python -m pytest -q
cd frontend && npm run lint
```

## 2. Travailler sur une branche

```bash
git checkout -b feature/<sujet>      # ou fix/<sujet>
```

## 3. Règles essentielles

1. **Les droits se vérifient côté serveur.** Le masquage d'un bouton n'est pas une sécurité. Toute nouvelle route d'API reçoit sa règle dans `REGLES` (`back-istc/users/acces_personnel.py`) ; sans règle, elle est réservée aux administrateurs.
2. **Toute route utilisée par un portail** (étudiant / formateur) doit être ajoutée à `PORTAL_RULES` (`back-istc/users/middleware.py`) **et** filtrer les données sur l'utilisateur connecté. Voir [Permissions](docs/developpeurs/permissions.md).
3. **Une règle métier = un seul endroit** (modèle ou service). Les calculs de scolarité passent par `paiements/finance.py`.
4. **Montants en `Decimal`**, opérations multi-tables dans `transaction.atomic()`.
5. **Chaque changement de modèle** est livré avec sa migration (`python manage.py makemigrations`).
6. **Chaque correction de bug** est livrée avec un test qui échouait avant.
7. **Chaque changement visible** par les utilisateurs met à jour le guide (`docs/guide/`) avec les libellés exacts de l'écran.
8. Ne committez jamais `.env`, `db.sqlite3`, `media/`, `venv/`, `node_modules/`.

## 4. Avant d'ouvrir une pull request

- [ ] `python -m pytest -q` passe
- [ ] `python manage.py makemigrations --check --dry-run` ne signale rien
- [ ] `npm run lint` et `npm run build` passent
- [ ] Tests ajoutés (voir [Tests](docs/developpeurs/tests.md))
- [ ] Documentation mise à jour (`mkdocs build --strict` passe)
- [ ] Description de la PR : contexte, captures d'écran, migrations, nouvelles variables `.env`

## 5. Versions et déploiement

Chaque push sur `main` crée automatiquement une nouvelle version (X.Y.Z). Elle est affichée en bas du menu latéral avec ses nouveautés. Avant de pousser, décrivez ce que voient les utilisateurs dans [`NOUVEAUTES.md`](NOUVEAUTES.md). Après le push, faites `git pull` pour récupérer le commit de version du robot. Pour livrer le backend sur un serveur : `sudo bash outils/deploiement/deployer_backend.sh` (voir [Livraison automatique](docs/installation/deploiement-automatique.md)). Détails : [Versions et livraisons](docs/developpeurs/versions.md).

Après fusion, la mise en production suit [Mettre à jour la plateforme](docs/installation/mise-a-jour.md) : sauvegarde, `git pull`, `migrate`, `collectstatic`, `npm run build`, redémarrage des services.

## 6. Nettoyage du dépôt (à faire une fois)

Des fichiers qui ne devraient pas être versionnés sont encore suivis par Git (`back-istc/.env` avec ses secrets, `back-istc/db.sqlite3`, `back-istc/media/`, les dossiers `__pycache__/`, `.DS_Store`). Le `.gitignore` empêche d'en ajouter de nouveaux ; pour retirer ceux déjà suivis **sans les supprimer du disque** :

```bash
git rm -r --cached back-istc/.env back-istc/db.sqlite3 back-istc/media .DS_Store
git rm -r --cached $(git ls-files | grep -E '__pycache__|\.pyc$|\.DS_Store$')
git commit -m "Retire du suivi Git les secrets, la base locale et les fichiers générés"
```

Si le dépôt a déjà été partagé, considérez les valeurs de `back-istc/.env` comme divulguées : changez la `SECRET_KEY`, le mot de passe de la base et la clé reCAPTCHA.
