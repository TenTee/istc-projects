# Discipline

Le menu **Discipline** regroupe les sanctions des étudiants : avertissements, blâmes, exclusions temporaires et définitives.

- **Consulter** : accès Étudiants, ou Pédagogie / Finance en lecture.
- **Enregistrer, corriger, lever, supprimer** : droit **Étudiants en écriture**.

## Vue d'ensemble

En haut de la page :

| Chiffre | Signification |
|---|---|
| Sanctions en cours | Sanctions ni levées ni terminées. |
| Étudiants concernés | Nombre d'étudiants ayant au moins une sanction en cours. |
| Exclusions en cours | Exclusions temporaires pas encore finies et exclusions définitives. |
| Sanctions levées | Sanctions levées (elles restent dans l'historique). |

Le tableau liste toutes les sanctions : Date, Étudiant (et matricule), Classe, Sanction, Motif, Période, État. Filtrez par texte (étudiant, matricule, classe, motif), par **Type** ou par **État** :

| État | Signification |
|---|---|
| **En cours** | La sanction s'applique. |
| **Terminée** | Exclusion temporaire dont le dernier jour est passé. |
| **Levée** | Sanction levée avant son terme ou pardonnée ; la date, le motif et l'auteur de la levée sont affichés sous le motif. |

## Enregistrer une sanction

1. **Nouvelle sanction** (ou, depuis la fiche de l'étudiant, *Discipline* → **Ajouter une sanction**).
2. Choisissez l'**étudiant** (tapez son nom ou son matricule).
3. Choisissez le **type de sanction** et la **date**.
4. Pour une **exclusion temporaire**, indiquez le **dernier jour d'exclusion** (inclus) : la durée est calculée (« 3 jours »).
5. Décrivez le **motif** (5 caractères au moins). Il est visible par l'étudiant dans son portail.
6. **Enregistrer**.

La date ne peut pas être dans le futur.

!!! warning "Exclusion définitive"
    Elle est inscrite au dossier mais ne ferme pas le compte de l'étudiant. Désactivez son compte (**Système** → *Utilisateurs*) ou supprimez l'étudiant si nécessaire.

## Prévenir le parent

Si le **WhatsApp du parent** est renseigné dans la fiche de l'étudiant, l'icône **WhatsApp** de la ligne ouvre une conversation avec lui. Le message est prêt : type de sanction, date, fin d'exclusion éventuelle et motif. Relisez-le avant de l'envoyer.

## Corriger, lever ou supprimer

| Action | Icône | Usage |
|---|---|---|
| **Corriger** | crayon | Changer le type, les dates ou le motif (faute de saisie, durée modifiée). L'étudiant ne peut pas être changé. |
| **Lever la sanction** | cadenas ouvert | La sanction cesse de s'appliquer (bon comportement, décision du conseil…). Motif de levée obligatoire ; la sanction reste dans l'historique. |
| **Annuler la levée** | flèche retour | Remet en cours une sanction levée par erreur. |
| **Supprimer** | corbeille | Efface la sanction. Réservé aux erreurs de saisie (mauvais étudiant, doublon). |

## Ce que voit l'étudiant

Dans son portail, menu **Discipline** : ses sanctions avec leur état. Une exclusion en cours est signalée en haut de la page avec sa date de fin. Voir [Portail étudiant](../portail-etudiant.md#discipline).
