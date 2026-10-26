# Mettre à jour la plateforme

À faire lorsqu'une nouvelle version du code est disponible. Prévoyez un créneau où peu de personnes utilisent la plateforme (le service est interrompu une à deux minutes).

## Procédure

```bash
cd /home/bitnami/istc-projects

# 1. Sauvegarder AVANT toute mise à jour
bash back-istc/scripts/backup_cron.sh

# 2. Récupérer le nouveau code
git pull

# 3. Backend
cd back-istc
source venv/bin/activate
pip install -r requirements.txt gunicorn
python manage.py migrate            # applique les changements de structure de la base
python manage.py collectstatic --noinput
python manage.py audit_droits      # vérifie les droits de chaque compte du personnel
python -m pytest -q                 # facultatif : vérifie que tout fonctionne (2 à 3 min)
sudo systemctl restart smartcampus-api

# 4. Frontend
cd ../frontend
npm ci
npm run build
sudo systemctl restart smartcampus-web
```

!!! danger "N'oubliez pas `migrate`"
    Si une mise à jour ajoute des tables (par exemple le module des heures des vacataires), oublier `python manage.py migrate` provoque des erreurs 500 sur les pages concernées.

## Vérifier après la mise à jour

- [ ] `sudo systemctl status smartcampus-api smartcampus-web` : les deux services sont « active (running) ».
- [ ] La page de connexion s'affiche et la connexion fonctionne.
- [ ] Le tableau de bord se charge.
- [ ] Le numéro affiché en bas du menu latéral est celui de la nouvelle version (voir `VERSION` à la racine du dépôt).

## Revenir en arrière

```bash
git log --oneline -5           # repérer la version précédente
git checkout <identifiant>     # revenir à cette version
```

Puis refaites les étapes 3 et 4. Si des migrations avaient été appliquées, restaurez la sauvegarde de l'étape 1 (voir [Sauvegardes](sauvegardes.md#restaurer)).
