# Questions fréquentes

## Connexion et comptes

??? question "J'ai oublié mon mot de passe."
    Demandez une réinitialisation à l'administration : **Système** → *Utilisateurs* (personnel), **Enseignants** → **Réinitialiser le mot de passe** (formateurs) ou **Étudiants** → *Voir détails* → **Réinitialiser le mot de passe** (étudiants). Le nouveau mot de passe provisoire vous est envoyé par WhatsApp, e-mail ou copie ; changez-le ensuite dans **Mon profil**.

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
    Oui : avatar en haut à droite → **Mon profil**. Vous pouvez y changer votre mot de passe et votre nom d'utilisateur ; votre mot de passe actuel est demandé. Voir [Mon profil](premiers-pas.md#mon-profil-changer-son-nom-dutilisateur-ou-son-mot-de-passe).

## Étudiants et inscriptions

??? question "Le candidat dit avoir envoyé sa préinscription mais je ne la vois pas."
    Vérifiez l'année sélectionnée en haut (la préinscription est rattachée à l'année active). Demandez au candidat s'il a vu le message « Pré-inscription envoyée » ; sinon, il doit recommencer.

??? question "Comment transmettre ses identifiants à un nouvel étudiant ?"
    **Étudiants** → icône *Voir détails* → rubrique *Accès Portail Étudiant*.

??? question "Un étudiant change de classe."
    Modifiez sa fiche (**Étudiants** → crayon) en choisissant la nouvelle filière / classe, ou utilisez **Scolarité** → **Nouvelle inscription** pour une nouvelle année. Les frais de la nouvelle classe s'appliquent.

??? question "Comment saisir une sanction disciplinaire ?"
    Menu **Discipline** → **Nouvelle sanction**, ou fiche de l'étudiant → *Discipline* → **Ajouter une sanction** (droit Étudiants en écriture). L'étudiant la voit dans son portail (« Discipline »). Voir [Discipline](administration/discipline.md).

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
    **Scolarité** → *Suivi des paiements* → **Détails & Reçus** → icône crayon (corriger) ou corbeille (supprimer), avec un motif obligatoire. Il faut le droit Finance en écriture. Les soldes sont recalculés et l'opération est inscrite au journal. Voir [Corriger ou supprimer un paiement](administration/scolarite.md#corriger-ou-supprimer-un-paiement).

??? question "Comment imprimer un reçu ou une facture ?"
    **Détails & Reçus** : icône PDF ou imprimante sur la ligne du paiement, bouton **Facture PDF** en haut. L'étudiant les télécharge aussi depuis « Ma Situation Financière » dans son portail.

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
