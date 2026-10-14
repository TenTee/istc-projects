"""
Contrôle d'accès du PERSONNEL aux routes de l'API, selon les droits de son rôle.

Chaque rôle (modèle `users.Role`) donne, pour cinq domaines, un niveau « none », « lecture »
ou « ecriture ». Ce module associe chaque route de l'API à un ou plusieurs domaines :

- lecture (GET, HEAD, OPTIONS) : autorisée si le rôle a au moins « lecture » sur UN des
  domaines de lecture de la route ;
- écriture (POST, PUT, PATCH, DELETE) : autorisée si le rôle a « ecriture » sur UN des
  domaines d'écriture de la route.

Les administrateurs (super-utilisateurs, rôles `admin` / `superadmin`) ne sont pas concernés,
les comptes portail (étudiant, formateur) non plus : ils sont gérés par `PortalAccessMiddleware`.

Pour AJOUTER une route : ajoutez une règle à `REGLES` (la première règle qui correspond
s'applique). Une route d'API qui ne correspond à aucune règle est réservée à l'administration.
Les tests `tests/test_flux_droits_personnel.py` vérifient cette matrice.

Interrupteur d'urgence : `CONTROLE_DROITS_PERSONNEL=False` dans le `.env` désactive ce contrôle
(retour au comportement antérieur) sans redéploiement du code.
"""
import os
import re

from django.http import JsonResponse

ET = "can_manage_etudiants"
PEDA = "can_manage_pedagogie"
FIN = "can_manage_finance"
LOG = "can_manage_logistique"
RH = "can_manage_rh"
DOMAINES = (ET, PEDA, FIN, LOG, RH)

TOUS = "tout_le_personnel"  # tout compte du personnel, quels que soient ses droits
ADMIN = "administration"     # administrateurs uniquement

LIBELLES = {ET: "Étudiants", PEDA: "Pédagogie", FIN: "Finances", LOG: "Logistique / Inventaire",
            RH: "Ressources Humaines"}

SAFE = {"GET", "HEAD", "OPTIONS"}

# (motif d'URL, domaines autorisés en lecture, domaines autorisés en écriture)
REGLES = [
    # --- Routes gérées ailleurs ------------------------------------------------------------
    (r"^/api/auth/", TOUS, TOUS),                      # comptes et rôles : contrôlés par les vues
    (r"^/api/(docs|schema|redoc)/", TOUS, ADMIN),      # documentation de l'API
    (r"^/api/$", TOUS, ADMIN),

    # --- Référentiels lus par tous les écrans ------------------------------------------------
    (r"^/api/v2/(filieres|specialites|cycles|levels|niveaux|classes|semestres|departements|domaines|"
     r"facultes|universites-tutelles|courses)(/|$)", TOUS, (PEDA,)),
    (r"^/api/v2/annees-academiques(/|$)", TOUS, (PEDA,)),
    (r"^/api/v2/(parametres-globaux|cycles-globaux|configuration-etablissement)(/|$)", TOUS, ADMIN),
    (r"^/api/(modules|salles)(/|$)", TOUS, (PEDA,)),
    (r"^/api/(emploi-du-temps|emploi-du-temps-documents)(/|$)", TOUS, (PEDA,)),
    (r"^/api/v2/(emplois-du-temps|affectations)(/|$)", TOUS, (PEDA,)),

    # --- Étudiants -----------------------------------------------------------------------------
    (r"^/api/etudiants(/|$)", (ET, PEDA, FIN), (ET,)),
    (r"^/api/(v2/)?inscriptions(/|$)", (ET, PEDA, FIN), (ET, FIN)),
    (r"^/api/v2/pre-inscriptions(/|$)", (FIN, ET), (FIN, ET)),

    # --- Pédagogie -----------------------------------------------------------------------------
    (r"^/api/(v2/)?notes(/|$)", (PEDA, ET), (PEDA,)),
    (r"^/api/v2/evaluations(/|$)", (PEDA, ET), (PEDA,)),
    (r"^/api/assiduite(/|$)", (PEDA, ET), (PEDA,)),
    (r"^/api/v2/epreuves(/|$)", (PEDA,), (PEDA,)),
    (r"^/api/vacations/coordinations(/|$)", (PEDA, FIN), (PEDA,)),
    (r"^/api/vacations/recaps(/|$)", (FIN, PEDA), (FIN,)),
    (r"^/api/vacations/", (PEDA, FIN), (PEDA,)),

    # --- Finances ------------------------------------------------------------------------------
    (r"^/api/paiements/(plans|student-schedule)(/|$)", (FIN, ET), (FIN, ET)),
    (r"^/api/paiements(/|$)", (FIN, ET), (FIN,)),
    (r"^/api/v2/(paiements|frais)(/|$)", (FIN, ET), (FIN,)),
    (r"^/api/(bourses|reductions-etudiants)(/|$)", (FIN, ET), (FIN,)),
    (r"^/api/(revenus|depenses)(/|$)", (FIN,), (FIN,)),
    (r"^/api/paie(/|$)", (FIN, RH), (FIN,)),

    # --- Ressources humaines ---------------------------------------------------------------------
    (r"^/api/formateurs(/|$)", (RH, PEDA, FIN, LOG), (RH,)),
    (r"^/api/personnels(/|$)", (RH, FIN, LOG), (RH,)),
    (r"^/api/conges(/|$)", (RH,), (RH,)),

    # --- Logistique ------------------------------------------------------------------------------
    (r"^/api/(inventaires|demandes|demandeurs)(/|$)", (LOG, RH), (LOG,)),

    # --- Divers ----------------------------------------------------------------------------------
    (r"^/api/communication(/|$)", TOUS, ADMIN),
    (r"^/api/files(/|$)", TOUS, TOUS),
    (r"^/api/logs(/|$)", ADMIN, ADMIN),
]
_REGLES = [(re.compile(m), lecture, ecriture) for m, lecture, ecriture in REGLES]


def controle_actif():
    return os.getenv("CONTROLE_DROITS_PERSONNEL", "True").strip().lower() not in {"0", "false", "no", "off", "non"}


def regle_pour(path):
    for motif, lecture, ecriture in _REGLES:
        if motif.search(path):
            return lecture, ecriture
    return ADMIN, ADMIN


def niveaux_du_role(user):
    """{domaine: niveau} pour le rôle du compte ; tout « none » si le rôle n'existe pas."""
    from users.models import Role
    role = Role.objects.filter(code=getattr(user, "role", "")).first()
    return {d: (getattr(role, d, "none") or "none") if role else "none" for d in DOMAINES}


def acces_autorise(niveaux, method, path):
    lecture, ecriture = regle_pour(path)
    if method in SAFE:
        domaines, attendus = lecture, ("lecture", "ecriture")
    else:
        domaines, attendus = ecriture, ("ecriture",)
    if domaines == TOUS:
        return True, None
    if domaines == ADMIN:
        return False, None
    return any(niveaux.get(d) in attendus for d in domaines), domaines


class StaffAccessMiddleware:
    """Applique la matrice `REGLES` aux comptes du personnel (hors administrateurs et portails)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith("/api/") and controle_actif():
            from users.middleware import jwt_user, portal_type
            from users.permissions import is_admin_user

            user = jwt_user(request)
            if user and user.is_active and not is_admin_user(user) and portal_type(user) is None:
                ok, domaines = acces_autorise(niveaux_du_role(user), request.method, path)
                if not ok:
                    if domaines:
                        besoin = " ou ".join(LIBELLES[d] for d in domaines)
                        niveau = "en lecture" if request.method in SAFE else "en écriture"
                        detail = f"Accès refusé : votre rôle n'a pas le droit {besoin} {niveau}."
                    else:
                        detail = "Accès refusé : cette action est réservée à l'administration."
                    return JsonResponse({"detail": detail, "error": detail}, status=403)
        return self.get_response(request)
