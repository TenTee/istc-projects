"""
Affiche les droits effectifs de chaque compte du personnel.

    python manage.py audit_droits

À lancer après une mise à jour et après toute modification des rôles : repère les comptes
sans aucun droit (ils ne voient que le tableau de bord) et les rôles inexistants.
"""
from django.core.management.base import BaseCommand

from users.acces_personnel import DOMAINES, LIBELLES, niveaux_du_role
from users.models import CustomUser, Role
from users.permissions import is_admin_user

COURT = {"none": "-", "lecture": "L", "ecriture": "E"}


class Command(BaseCommand):
    help = "Liste les droits effectifs des comptes du personnel (contrôle d'accès serveur)."

    def handle(self, *args, **options):
        codes = set(Role.objects.values_list("code", flat=True))
        entete = ["Compte", "Rôle"] + [LIBELLES[d][:12] for d in DOMAINES]
        self.stdout.write(" | ".join(f"{c:<14}" for c in entete))
        alertes = 0
        for u in CustomUser.objects.filter(is_active=True).order_by("role", "username"):
            if u.role in ("etudiant", "formateur"):
                continue
            if is_admin_user(u):
                droits = ["E"] * len(DOMAINES)
            else:
                n = niveaux_du_role(u)
                droits = [COURT[n[d]] for d in DOMAINES]
            ligne = [u.username[:14], u.role[:14]] + droits
            remarque = ""
            if not is_admin_user(u) and u.role not in codes:
                remarque, alertes = "  ← rôle inexistant : aucun droit", alertes + 1
            elif not is_admin_user(u) and set(droits) == {"-"}:
                remarque, alertes = "  ← aucun droit", alertes + 1
            self.stdout.write(" | ".join(f"{c:<14}" for c in ligne) + remarque)
        self.stdout.write("")
        self.stdout.write("E = écriture, L = lecture, - = aucun. Réglage : Système → Rôles.")
        if alertes:
            self.stdout.write(self.style.WARNING(f"{alertes} compte(s) sans aucun droit à vérifier."))
        else:
            self.stdout.write(self.style.SUCCESS("Tous les comptes du personnel ont au moins un droit."))
