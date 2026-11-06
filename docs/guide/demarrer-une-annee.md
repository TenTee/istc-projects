# Démarrer une nouvelle année académique

Cette procédure sert à la **première mise en service** et au **passage d'une année à la suivante** (par exemple de 2025-2026 à 2026-2027). Elle est faite par un administrateur.

## Liste de contrôle

- [ ] 1. Créer la nouvelle année académique et la rendre active
- [ ] 2. Vérifier les classes générées automatiquement
- [ ] 3. Vérifier / mettre à jour les cours (modules) et les rattacher aux classes
- [ ] 4. Configurer les frais et échéanciers de chaque classe
- [ ] 5. Créer les codes de bourse éventuels
- [ ] 6. Vérifier les coordonnateurs de filière
- [ ] 7. Saisir l'emploi du temps
- [ ] 8. Réinscrire les anciens étudiants et traiter les préinscriptions

## 1. Créer l'année académique

Il faut être administrateur, ou avoir un rôle avec le droit **Gérer les années académiques** (voir [Rôles et droits d'accès](roles-et-acces.md#annees-academiques-et-archives)).

1. Menu **Pédagogie** → **Années académiques** (ou **Structure Académique**, onglet *Années Académiques*).
2. Cliquez sur **Nouvelle année**.
3. Remplissez :
    - « Libellé » : `2026-2027` (format `AAAA-AAAA`) ;
    - « Début » et « Fin » ;
    - activez **En faire l'année active maintenant** si l'année commence maintenant. Sinon, faites-le plus tard avec le bouton **Activer** de sa ligne.
4. Cliquez sur **Enregistrer**.

Ce qui se passe automatiquement :

- **Une seule année est active** : activer la nouvelle année archive l'ancienne. Une confirmation le rappelle. L'année active ne se désactive pas seule : activez celle qui la remplace.
- Les **classes de l'année précédente sont recopiées** pour la nouvelle année (même filière, spécialité, cycle et niveau). Les étudiants, notes et paiements, eux, restent rattachés à l'ancienne année.

!!! warning "Après le changement d'année"
    Demandez à chacun de recharger la page et de vérifier que le sélecteur en haut affiche bien la nouvelle année *(Active)*. Les anciennes années, marquées *(Archivée)*, restent accessibles aux administrateurs et aux rôles qui ont le droit **Années archivées**.

## 2. Vérifier les classes

Onglet *Classes* de la Structure Académique : chaque classe de la nouvelle année doit apparaître. Ajoutez celles qui manquent (nouvelle filière, nouveau niveau…). Voir [Structure académique](administration/structure-academique.md).

## 3. Les cours

Menu **Pédagogie** → **Cours** : vérifiez que chaque cours est rattaché aux classes de la nouvelle année (« Classes rattachées »), avec le bon « Coefficient » et le bon « Semestre ». Voir [Cours et modules](administration/cours.md).

## 4. Les frais

Menu **Finances** → **Scolarité**, onglet *Configuration des Frais*, bouton **Config. Rapide** pour chaque classe : frais d'inscription, total de la scolarité et tranches avec dates d'échéance. Voir [Scolarité](administration/scolarite.md#configurer-les-frais-dune-classe).

## 5. Les bourses

Onglet *Gestion des Bourses* → **Créer une Bourse** pour chaque bourse accordée. Le code sera saisi lors de l'approbation de la préinscription du bénéficiaire.

## 6. Les coordonnateurs

Menu **Pédagogie** → **Coordonnateurs** : le message « Filière(s) sans coordonnateur actif » liste les filières à pourvoir. Voir [Coordonnateurs](administration/coordonnateurs.md).

## 7. L'emploi du temps

Menu **Pédagogie** → **Emploi du temps** → **Nouveau Créneau**. Voir [Emploi du temps](administration/emploi-du-temps.md). L'emploi du temps sert aussi au pointage des heures des vacataires : il doit être à jour.

## 8. Les étudiants

- **Nouveaux étudiants** : traitez les préinscriptions (**Finances** → **Préinscriptions**).
- **Anciens étudiants** passant en année supérieure : **Finances** → **Scolarité** → **Nouvelle inscription** (fenêtre « Créer une inscription » : Étudiant, Niveau, Année académique). Voir [Scolarité](administration/scolarite.md#reinscrire-un-ancien-etudiant).
