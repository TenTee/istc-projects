# Journal des modifications

Généré automatiquement à chaque livraison (`outils/version/versionner.py`). Ne pas modifier à la main :
écrivez les nouveautés de la prochaine livraison dans `NOUVEAUTES.md`.

## 0.4.0 — 06/11/2026

- Rôles : nouveau droit « Gérer les années académiques » (créer, activer, supprimer une année vide) et droit « Années archivées » (aucun accès, consultation seule, ou consultation et modification).
- Nouveau menu Pédagogie → Années académiques, avec un bouton « Activer » ; les années archivées sont signalées dans le sélecteur d'année.
- Une année contenant des données ne peut plus être supprimée par erreur.
- Correction : une sanction enregistrée sans date provoquait une erreur.

## 0.3.1 — 02/11/2026

- Améliorations et corrections diverses.

## 0.3.0 — 02/11/2026

- Mon profil (menu de l'avatar) : chacun peut changer son mot de passe et son nom d'utilisateur.
- Après la création d'un compte (utilisateur, formateur, étudiant, pré-inscription approuvée), un message prêt à envoyer avec les identifiants : copie, WhatsApp ou e-mail.
- Réinitialisation du mot de passe des étudiants depuis leur fiche et des formateurs par les RH, avec envoi du nouveau mot de passe.
- Mots de passe provisoires plus lisibles (sans 0/O ni 1/l/I).
- Reçus de paiement en PDF, numérotés (REC-AAAA-NNNNNN), à télécharger ou imprimer ; facture PDF de l'étudiant (frais, réductions, paiements, échéancier).
- Les étudiants téléchargent leurs reçus et leur facture depuis leur portail.
- Correction et suppression d'un paiement (droit Finance en écriture), avec motif obligatoire, recalcul des soldes et des tranches, et journal des opérations.
- Nouveau menu Discipline : enregistrer, corriger, lever ou supprimer une sanction (avertissement, blâme, exclusions), prévenir le parent sur WhatsApp ; les sanctions apparaissent aussi dans la fiche de l'étudiant.

## 0.2.13 — 30/10/2026

- Améliorations et corrections diverses.

## 0.2.12 — 29/10/2026

- Améliorations et corrections diverses.

## 0.2.11 — 29/10/2026

- Améliorations et corrections diverses.

## 0.2.10 — 29/10/2026

- Améliorations et corrections diverses.

## 0.2.9 — 29/10/2026

- Améliorations et corrections diverses.

## 0.2.8 — 29/10/2026

- Améliorations et corrections diverses.

## 0.2.7 — 29/10/2026

- Améliorations et corrections diverses.

## 0.2.6 — 28/10/2026

- Améliorations et corrections diverses.

## 0.2.5 — 28/10/2026

- Améliorations et corrections diverses.

## 0.2.4 — 28/10/2026

- Améliorations et corrections diverses.

## 0.2.3 — 28/10/2026

- Améliorations et corrections diverses.

## 0.2.2 — 28/10/2026

- Améliorations et corrections diverses.

## 0.2.1 — 28/10/2026

- Améliorations et corrections diverses.

## 0.2.0 — 26/10/2026

- Les droits des rôles du personnel sont désormais appliqués par le serveur : un compte sans droit sur un domaine ne peut plus consulter ni modifier ses données.
- Toutes les pages de l'administration et des portails s'adaptent au téléphone et à la tablette.
- Les longs formulaires s'ouvrent en plein écran sur téléphone, et les tableaux larges défilent dans leur cadre.
- Le numéro de version et les nouveautés sont affichés en bas du menu latéral.

## 0.1.0 — 13/10/2026

- Version de référence de la plateforme : administration, portail étudiant, portail formateur et préinscription en ligne.
- Audit complet : cloisonnement des portails, années archivées en lecture seule, corrections des notes, des paiements, de la paie et des congés.
- Gestion des heures des vacataires par les coordonnateurs de filière, reprise automatique dans la paie.
