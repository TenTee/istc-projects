# Rôles et droits d'accès

SmartCampus distingue **trois espaces** totalement séparés :

| Espace | Pour qui | Ce qu'on y voit |
|---|---|---|
| **Administration** | Personnel de l'établissement | Les modules autorisés par le rôle de la personne |
| **Portail formateur** | Comptes de type *formateur* | Uniquement ses classes, ses cours, ses notes, ses heures |
| **Portail étudiant** | Comptes de type *étudiant* | Uniquement son propre dossier |

!!! success "Cloisonnement garanti"
    Un étudiant ou un formateur **ne peut pas** accéder à l'administration, même en tapant directement une adresse : le serveur refuse la demande. Un étudiant ne voit jamais les notes ou paiements d'un autre étudiant.

## Les droits d'un rôle d'administration

Chaque rôle (par exemple « Secrétaire », « Comptable », « Responsable pédagogique ») possède **cinq domaines** de droits. Pour chacun, trois niveaux :

| Niveau | Signification |
|---|---|
| **Aucun** | Le menu correspondant n'apparaît pas. |
| **Lecture** | Le menu apparaît, on peut consulter et exporter, mais pas créer, modifier ni supprimer. |
| **Écriture** | Accès complet : consultation, création, modification, suppression. |

### Quels menus pour quel domaine ?

| Domaine (dans l'écran Rôles) | Menus concernés |
|---|---|
| **Étudiants** | Étudiants ; Notes (en complément de Pédagogie) |
| **Pédagogie (Notes, Cours)** | Pédagogie : Structure Académique, Cours, Notes, Emploi du temps, Banque d'épreuves, Assiduité, Coordonnateurs |
| **Finances** | Finances : Aperçu global, Préinscriptions, Scolarité, Salaires Personnel, Salaires Formateurs, Heures vacataires |
| **Logistique / Inventaire** | Inventaire |
| **Ressources Humaines** | Enseignants ; Personnel : Liste du personnel, Congés et absences |

Le **Tableau de bord** est visible par tout le personnel.

!!! success "Droits appliqués par le serveur"
    Les droits ne masquent pas seulement les menus : le serveur **refuse** toute consultation ou modification hors des droits du rôle (message « Accès refusé : votre rôle n'a pas le droit … »). Seuls les **référentiels** (années, filières, classes, cours, salles, emploi du temps) restent lisibles par tout le personnel, car tous les écrans en ont besoin.

### Lectures croisées utiles aux écrans

Certains écrans affichent des informations d'un autre domaine. Le droit de **lecture** est alors accordé, jamais celui de modification :

| Avec le droit… | on peut aussi consulter… | pour |
|---|---|---|
| Finances | la liste des étudiants, leurs inscriptions, le personnel et les formateurs | encaisser les paiements, préparer la paie |
| Étudiants | les paiements, échéanciers et notes des étudiants | la fiche complète de l'étudiant |
| Pédagogie | les étudiants et les formateurs | saisir les notes, construire l'emploi du temps |
| Logistique | le personnel et les formateurs | choisir le demandeur d'une demande de matériel |
| Ressources Humaines | les demandes de matériel et la paie | onglet *Demandes* des congés, suivi des salaires |

### Rôles d'administration générale

Les rôles dont le code est `admin` ou `superadmin` (et les comptes « super-utilisateur ») voient **tous** les menus, y compris **Système** (paramètres, utilisateurs, rôles, apparence). Le menu Système n'est jamais visible pour les autres rôles.

| Action réservée | Qui peut la faire |
|---|---|
| Créer / modifier des comptes utilisateurs et des rôles | Administrateurs (`admin`, `superadmin`) |
| Valider / dévalider les notes (les rendre visibles aux étudiants) | Administrateurs, ou rôle avec Pédagogie en **Écriture** |
| Modifier les paramètres globaux, cycles et apparence de l'établissement | Administrateurs |
| Créer, activer, supprimer une année académique | Administrateurs, ou rôle avec **Gérer les années académiques** |
| Consulter ou modifier une année académique archivée | Administrateurs, ou rôle avec le droit **Années archivées** |

## Années académiques et archives {#annees-academiques-et-archives}

Deux droits du rôle, en plus des domaines, se règlent dans **Système** → *Rôles* (rubrique *Années académiques*).

| Droit | Valeurs | Effet |
|---|---|---|
| **Gérer les années académiques** | oui / non | Menu **Pédagogie** → **Années académiques** : créer une année, la modifier, **l'activer** (l'ancienne est archivée), supprimer une année vide. |
| **Années archivées** | Aucun accès / Consultation seule / Consultation et modification | Choisir une année *(Archivée)* dans le sélecteur en haut de l'écran, puis la consulter, ou la consulter et la modifier. |

- Le droit **Années archivées** n'ajoute aucun domaine : un comptable avec « Consultation seule » voit les finances des années passées, mais pas les notes s'il n'a pas la Pédagogie.
- En **consultation seule**, l'étiquette « Archives : consultation seule » s'affiche à côté du sélecteur d'année, et toute modification est refusée.
- Sans ce droit, les années archivées apparaissent grisées dans le sélecteur.
- Les administrateurs (`admin`, `superadmin`) ont tous ces droits. Les portails étudiant et formateur ne voient que l'année active.

## Exemples de rôles

| Rôle | Étudiants | Pédagogie | Finances | Logistique | RH |
|---|---|---|---|---|---|
| Secrétaire | Écriture | Lecture | Lecture | Aucun | Aucun |
| Comptable | Lecture | Aucun | Écriture | Aucun | Lecture |
| Responsable pédagogique | Lecture | Écriture | Aucun | Aucun | Aucun |
| Logisticien | Aucun | Aucun | Aucun | Écriture | Aucun |
| Ressources humaines | Aucun | Aucun | Lecture | Aucun | Écriture |

La création de rôles est expliquée dans [Système → Rôles](administration/systeme.md#creer-un-role).

## Le cas des formateurs et des coordonnateurs

- Un **formateur** reçoit un compte depuis **Enseignants** → **Générer un compte portail**. Il ne voit que le portail formateur.
- Un **coordonnateur de filière** est un formateur désigné dans **Pédagogie** → **Coordonnateurs**. Il voit en plus le menu **Coordination** dans son portail (pointage des heures des vacataires de sa filière).

## Le cas des étudiants

Le compte est créé automatiquement quand l'étudiant est ajouté (préinscription approuvée ou ajout direct). Il n'a pas besoin d'être configuré.
