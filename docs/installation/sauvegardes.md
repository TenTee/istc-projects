# Sauvegardes et restauration

Deux éléments doivent être sauvegardés :

1. **La base de données** (étudiants, notes, paiements, paie…) ;
2. **Le dossier `back-istc/media/`** (photos, justificatifs de paiement, documents de cours, épreuves, logos).

Sans l'un ou l'autre, une restauration est incomplète.

## Sauvegarde automatique de la base (PostgreSQL)

Le projet fournit deux scripts :

| Script | Rôle |
|---|---|
| `back-istc/scripts/postgres_backup.sh` | Crée une copie compressée de la base (`smartcampus_AAAAMMJJ_HHMMSS.dump`, format PostgreSQL « custom ») dans `back-istc/backups/postgres/` et supprime les copies de plus de 30 jours (réglable avec `BACKUP_RETENTION_DAYS`). |
| `back-istc/scripts/backup_cron.sh` | Charge `.env` (donc `DATABASE_URL`) puis lance le script précédent. C'est lui qu'on planifie. |

Tester une fois à la main :

```bash
cd /home/bitnami/istc-projects/back-istc
bash scripts/backup_cron.sh
ls -lh backups/postgres/
```

Planifier chaque nuit à 2 h :

```bash
crontab -e
```

Ajoutez la ligne :

```cron
0 2 * * * /bin/bash /home/bitnami/istc-projects/back-istc/scripts/backup_cron.sh >> /home/bitnami/backup.log 2>&1
```

## Sauvegarde des fichiers déposés

```bash
cd /home/bitnami/istc-projects/back-istc
tar czf backups/media_$(date +%Y%m%d).tar.gz media/
```

À planifier de la même façon (par exemple chaque nuit à 2 h 30).

!!! danger "Copiez les sauvegardes hors du serveur"
    Une sauvegarde restée sur le serveur disparaît avec lui (panne disque, piratage). Copiez régulièrement le dossier `backups/` vers un autre emplacement : un autre serveur (`rsync`), un stockage en ligne, ou au minimum un disque externe chaque semaine.

## Restaurer

!!! warning
    La restauration **remplace** les données actuelles. Arrêtez l'API pendant l'opération et faites d'abord une sauvegarde de l'état actuel.

```bash
sudo systemctl stop smartcampus-api

# Base de données (adapter le nom du fichier)
set -a; source .env; set +a
pg_restore --clean --if-exists --no-owner -d "$DATABASE_URL" backups/postgres/smartcampus_<date>.dump

# Fichiers
tar xzf backups/media_<date>.tar.gz

sudo systemctl start smartcampus-api
```

**Testez la restauration** au moins une fois sur un serveur de test : une sauvegarde jamais testée n'est pas une sauvegarde.
