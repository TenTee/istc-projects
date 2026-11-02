"""
Crée un compte super-administrateur (accès complet, rôle « superadmin »).

    python manage.py creer_superadmin                      # questions : nom, e-mail, mot de passe
    python manage.py creer_superadmin --nom admin --email admin@ecole.cm
    SMARTCAMPUS_ADMIN_PASSWORD=… python manage.py creer_superadmin --nom admin --email … --sans-question

Le mot de passe n'est jamais passé en argument (il resterait dans l'historique du shell) :
il est demandé sans écho, ou lu dans la variable SMARTCAMPUS_ADMIN_PASSWORD.
À la différence de `createsuperuser`, le compte reçoit le rôle « superadmin »
(sinon il garde le rôle par défaut du modèle).
"""
import os
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from users.utils import erreur_nom_utilisateur, erreurs_mot_de_passe


class Command(BaseCommand):
    help = "Crée un compte super-administrateur (rôle superadmin). Mot de passe demandé sans écho."

    def add_arguments(self, parser):
        parser.add_argument("--nom", help="Nom d'utilisateur (connexion)")
        parser.add_argument("--email", help="Adresse e-mail (unique)")
        parser.add_argument("--noms", default="", help="Nom affiché")
        parser.add_argument("--prenoms", default="", help="Prénoms affichés")
        parser.add_argument("--sans-question", action="store_true",
                            help="Aucune question : --nom, --email et SMARTCAMPUS_ADMIN_PASSWORD sont requis")

    def _demander(self, invite, valeur, interactif):
        while not valeur:
            if not interactif:
                raise CommandError(f"Valeur manquante : {invite.strip(' :')}.")
            valeur = input(invite).strip()
        return valeur

    def handle(self, *args, **options):
        User = get_user_model()
        interactif = not options["sans_question"]

        nom = self._demander("Nom d'utilisateur : ", (options["nom"] or "").strip(), interactif)
        erreur = erreur_nom_utilisateur(nom)
        if erreur:
            raise CommandError(f"Nom d'utilisateur « {nom} » refusé : {erreur}")

        email = self._demander("E-mail : ", (options["email"] or "").strip(), interactif)
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"L'e-mail {email} est déjà utilisé par un autre compte.")

        mdp = os.environ.get("SMARTCAMPUS_ADMIN_PASSWORD", "")
        if not mdp:
            if not interactif:
                raise CommandError("Définissez SMARTCAMPUS_ADMIN_PASSWORD (mode --sans-question).")
            while True:
                mdp = getpass("Mot de passe : ")
                if mdp != getpass("Confirmez le mot de passe : "):
                    self.stderr.write("Les deux saisies sont différentes, recommencez.")
                    continue
                problemes = erreurs_mot_de_passe(mdp)
                if problemes:
                    self.stderr.write("Mot de passe refusé : " + " ".join(problemes))
                    continue
                break
        else:
            problemes = erreurs_mot_de_passe(mdp)
            if problemes:
                raise CommandError("Mot de passe refusé : " + " ".join(problemes))

        user = User.objects.create_superuser(username=nom, email=email, password=mdp)
        user.role = "superadmin"
        user.noms = options["noms"] or user.noms or nom
        user.prenoms = options["prenoms"] or user.prenoms or ""
        user.is_active = True
        user.save(update_fields=["role", "noms", "prenoms", "is_active"])
        self.stdout.write(self.style.SUCCESS(f"Super-administrateur « {nom} » créé. Connectez-vous avec ce nom."))
