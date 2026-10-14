# Notes et relevés

**Menu :** Pédagogie → Notes — **Accès :** domaine *Pédagogie* (ou *Étudiants*). Écriture nécessaire pour saisir.

## Comment une note est calculée

Chaque note d'un étudiant dans un cours comprend :

| Composante | Saisie sur | Exemple (réglage par défaut 30 / 70) |
|---|---|---|
| **CC** — contrôle continu | le pourcentage CC | sur 30 |
| **SN** — session normale (examen) | le pourcentage SN | sur 70 |
| **Rattrapage** (facultatif) | le pourcentage SN | sur 70 ; **remplace** la note SN |

**Note finale (sur 100) = CC + SN** (ou CC + Rattrapage si un rattrapage est saisi). Elle est calculée automatiquement.

Exemple : CC = 22/30, SN = 41/70 → note finale = **63/100** (soit 12,6/20).

!!! info "Réglage des pourcentages"
    Les pourcentages CC / SN se règlent dans **Système** → *Paramètres Globaux* → « Calcul des Notes » (leur somme doit faire 100). S'ils sont modifiés, les notes déjà saisies sont **converties automatiquement** à la nouvelle échelle.

Une note supérieure au maximum (par exemple 35 en CC alors que le CC est sur 30) est refusée avec le message « La note CC ne peut pas dépasser la configuration de 30 ».

## Validation : quand l'étudiant voit-il ses notes ?

!!! warning "Les notes sont masquées tant qu'elles ne sont pas validées"
    Une note enregistrée (par l'administration ou par un formateur) **n'est pas visible** sur le portail étudiant tant qu'un administrateur ne l'a pas **validée**. Toute modification ultérieure d'une note par un utilisateur sans droit de validation la masque à nouveau jusqu'à une nouvelle validation.

Peuvent valider : les administrateurs et les rôles ayant le droit *Pédagogie* en **Écriture**.

## Les onglets de la page « Gestion des Notes »

La page comporte quatre onglets : *Saisie par Cours*, *Relevés par Étudiant*, *Récapitulatif par Classe* et *Rattrapages*.

### *Saisie par Cours* — saisir les notes d'une classe

![Saisie par cours : (1) Enregistrer tout, (2) Valider les notes](../../images/captures/15_notes_saisie_par_cours.jpg)

C'est la méthode recommandée.

1. Dans « Sélection du Cours », choisissez la « Classe » puis le « Module / Matière ».
2. Cliquez sur **Charger la Liste** : tous les étudiants inscrits dans la classe apparaissent, avec leurs notes existantes.
3. Tapez les notes CC, SN (et Rattrapage s'il y a lieu) de chaque étudiant. La note finale se calcule à l'écran.
4. Cliquez sur **Enregistrer tout**.
5. Une fois les notes vérifiées, cliquez sur **Valider les notes** pour les publier aux étudiants.

Autres boutons :

- **Dévalider** : masque de nouveau les notes de ce cours aux étudiants (correction en cours, par exemple) ;
- **Exporter par Module** : fichier Excel des notes du cours.

!!! note "Lecture seule"
    Avec le droit *Lecture*, le message « Vous avez un accès en lecture seule sur ce module… » s'affiche : vous pouvez consulter et exporter, pas modifier.

### *Relevés par Étudiant* — relevé de notes

![Le relevé de notes généré](../../images/captures/16_notes_releve.jpg)

1. Choisissez la « Filière », le « Cycle », la « Classe », l'« Étudiant » et le « Semestre ».
2. Cliquez sur **Générer le Relevé** : le relevé s'affiche (cours, coefficients, notes, moyenne).
3. **Télécharger PDF** pour l'imprimer ou l'envoyer.

### *Récapitulatif par Classe* — procès-verbal

![Le récapitulatif des notes d'une classe](../../images/captures/17_notes_recapitulatif.jpg)

1. Dans « Sélection de la classe », choisissez la classe (et le semestre).
2. Le tableau « Récapitulatif des Notes » présente tous les étudiants et tous les cours.
3. **Télécharger le Récapitulatif (PDF)** ou **Exporter (Excel)**.

### *Rattrapages* — étudiants à convoquer

![La liste des étudiants en rattrapage](../../images/captures/18_notes_rattrapages.jpg)

Liste des « Étudiants en rattrapage » : toutes les notes finales **inférieures à 50/100** (10/20), avec la salle habituelle du cours. Filtrez par classe et semestre, puis **Télécharger le PDF** pour l'affichage ou la convocation.

Pour saisir la note de rattrapage : onglet *Saisie par Cours*, colonne Rattrapage, puis **Enregistrer tout** et **Valider les notes**.

## Saisie par les formateurs

Les formateurs saisissent eux-mêmes les notes de leurs cours depuis leur portail (voir [Portail formateur](../portail-formateur.md#saisie-des-notes)). Ces notes arrivent **non validées** : l'administration les contrôle puis clique sur **Valider les notes**.
