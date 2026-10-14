# Questions fréquentes

## Connexion et comptes

??? question "J'ai oublié mon mot de passe."
    Demandez une réinitialisation à l'administration : **Système** → *Utilisateurs* (personnel) ou **Enseignants** → **Réinitialiser le mot de passe** (formateurs). Pour un étudiant, l'administration consulte son mot de passe initial dans sa fiche ou le fait réinitialiser par un administrateur.

??? question "Je me connecte mais la page tourne sans fin / reste blanche."
    1. Rechargez la page (++f5++).
    2. Déconnectez-vous puis reconnectez-vous.
    3. Vérifiez dans le sélecteur du haut que l'année **(Active)** est choisie.
    4. Si le problème persiste pour tout le monde, le serveur est peut-être arrêté : prévenez le responsable informatique ([Dépannage](../installation/depannage.md)).

??? question "Un menu a disparu / je ne vois pas un module."
    Votre rôle n'a pas accès à ce domaine. Demandez à un administrateur de vérifier votre rôle (**Système** → *Rôles*), puis déconnectez-vous et reconnectez-vous.

??? question "J'ai le message « Accès refusé » en enregistrant."
    Votre rôle a seulement le droit **Lecture** sur ce domaine. Un administrateur doit lui donner le droit **Écriture**.

??? question "Puis-je changer moi-même mon mot de passe ?"
    Pas depuis l'interface pour l'instant : le menu « Mon profil » affiche votre nom et votre rôle. Demandez un nouveau mot de passe à l'administration si nécessaire.

## Étudiants et inscriptions

??? question "Le candidat dit avoir envoyé sa préinscription mais je ne la vois pas."
    Vérifiez l'année sélectionnée en haut (la préinscription est rattachée à l'année active). Demandez au candidat s'il a vu le message « Pré-inscription envoyée » ; sinon, il doit recommencer.

??? question "Comment transmettre ses identifiants à un nouvel étudiant ?"
    **Étudiants** → icône *Voir détails* → rubrique *Accès Portail Étudiant*.

??? question "Un étudiant change de classe."
    Modifiez sa fiche (**Étudiants** → crayon) en choisissant la nouvelle filière / classe, ou utilisez **Scolarité** → **Nouvelle inscription** pour une nouvelle année. Les frais de la nouvelle classe s'appliquent.

??? question "Comment saisir une sanction disciplinaire ?"
    Les sanctions sont consultables par l'étudiant dans son portail (« Discipline »). Leur saisie se fait aujourd'hui depuis l'interface d'administration technique (`/admin/` du serveur, rubrique *Sanctions disciplinaires*), réservée au super-administrateur.

## Notes

??? question "Les étudiants ne voient pas leurs notes."
    Les notes doivent être **validées** : **Notes** → *Saisie par Cours* → choisir la classe et le cours → **Charger la Liste** → **Valider les notes**.

??? question "Ma note est refusée : « ne peut pas dépasser la configuration de 30 »."
    Le CC se saisit sur 30 et l'examen sur 70 (réglage par défaut). Convertissez votre note : un CC noté 15/20 se saisit 22,5 (15 × 30 ÷ 20).

??? question "Qui est convoqué au rattrapage ?"
    Tout étudiant dont la note finale d'un cours est inférieure à 50/100 (10/20). Liste dans **Notes** → *Rattrapages*.

## Paiements

??? question "Le solde d'un étudiant me paraît faux."
    Vérifiez dans l'ordre : 1) les frais de sa classe (*Configuration des Frais*), 2) la présence du mot « inscription » dans le libellé des frais d'inscription, 3) ses réductions / bourse, 4) ses paiements (**Détails & Reçus**) : un paiement enregistré avec le mauvais type (inscription au lieu de formation) fausse les deux soldes.

??? question "Je me suis trompé dans un paiement."
    L'écran Scolarité ne permet pas encore de modifier ou supprimer un paiement (pour garantir la traçabilité). Demandez au super-administrateur de le corriger depuis l'interface d'administration technique (`/admin/` du serveur, rubrique *Paiements*), en conservant le justificatif.

## Paie et vacataires

??? question "Un vacataire n'apparaît pas dans la campagne de paie."
    Ses heures du mois ne sont pas **validées** (récap non clôturé par le coordonnateur, ou non validé par la finance), ou son taux horaire est à 0. Voir [Heures des vacataires](administration/heures-vacataires.md). Supprimez la campagne (si elle n'est pas payée), régularisez, puis régénérez-la.

??? question "Je ne peux pas générer la campagne : « déjà existante »."
    Une seule campagne par mois et par type est autorisée. Ouvrez celle qui existe, ou supprimez-la si elle n'est pas encore payée.

??? question "Le coordonnateur ne peut pas clôturer le mois."
    La clôture n'est possible qu'à partir du **dernier jour du mois**.

## Divers

??? question "Peut-on utiliser SmartCampus sur téléphone ?"
    Oui, dans le navigateur du téléphone. Le menu s'ouvre avec l'icône ☰. Pour la saisie de grandes listes (notes, emploi du temps), un ordinateur reste plus confortable.

??? question "Mes données sont-elles sauvegardées ?"
    Oui si le responsable informatique a mis en place la sauvegarde automatique décrite dans [Sauvegardes](../installation/sauvegardes.md).
