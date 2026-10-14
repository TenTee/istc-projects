"""
Crée un rôle (`users.Role`) pour chaque code de rôle utilisé par un compte mais encore absent
de la table des rôles.

Depuis la mise en place du contrôle des droits du personnel côté serveur
(`users/acces_personnel.py`), un compte dont le rôle n'existe pas n'aurait plus accès qu'au
tableau de bord. Pour ne bloquer personne lors de la mise à jour, les codes connus reçoivent
des droits cohérents avec leur nom ; les autres sont créés sans droit et devront être réglés
par un administrateur (Système → Rôles). Les rôles existants ne sont jamais modifiés.
"""
from django.db import migrations

EXCLUS = {"admin", "superadmin", "etudiant", "formateur", ""}

DEFAUTS = {
    # code: (libellé, droits)
    "responsableRh": ("Responsable RH", {"can_manage_rh": "ecriture"}),
    "responsablePedagogique": ("Responsable pédagogique",
                               {"can_manage_pedagogie": "ecriture", "can_manage_etudiants": "lecture"}),
    "responsableLogistique": ("Responsable logistique", {"can_manage_logistique": "ecriture"}),
    "responsableMarketing": ("Responsable marketing", {"can_manage_etudiants": "lecture"}),
    "secretaire": ("Secrétaire", {"can_manage_etudiants": "ecriture", "can_manage_pedagogie": "ecriture",
                                  "can_manage_finance": "ecriture"}),
    "comptable": ("Comptable", {"can_manage_finance": "ecriture", "can_manage_etudiants": "lecture",
                                "can_manage_rh": "lecture"}),
}


def creer_roles_manquants(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    CustomUser = apps.get_model("users", "CustomUser")
    existants = set(Role.objects.values_list("code", flat=True))
    codes = set(CustomUser.objects.values_list("role", flat=True).distinct())
    for code in sorted(c for c in codes if c not in existants and c not in EXCLUS):
        libelle, droits = DEFAUTS.get(code, (code, {}))
        if "secretaire" in code.lower() and code not in DEFAUTS:
            libelle, droits = code, DEFAUTS["secretaire"][1]
        Role.objects.create(code=code, libelle=libelle, **droits)


class Migration(migrations.Migration):
    dependencies = [("users", "0002_change_permissions_to_access_levels")]
    operations = [migrations.RunPython(creer_roles_manquants, migrations.RunPython.noop)]
