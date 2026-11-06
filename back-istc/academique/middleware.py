import contextvars
from django.http import JsonResponse

# Variable globale pour stocker l'année académique courante pour le thread/contexte actuel
_current_academic_year_id = contextvars.ContextVar('current_academic_year_id', default=None)

class AcademicYearMiddleware:
    """
    Middleware qui capture le header 'X-Academic-Year' et le stocke 
    dans un ContextVar pour qu'il soit accessible partout dans le code.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        academic_year_id = request.headers.get('X-Academic-Year')
        
        # Stockage de l'ID
        token = _current_academic_year_id.set(academic_year_id)
        
        try:
            response = self.get_response(request)
        finally:
            # Nettoyage après la réponse
            _current_academic_year_id.reset(token)
            
        return response


class ArchiveAcademicYearMiddleware:
    """
    Contrôle l'accès aux années académiques archivées (non actives), choisies par l'en-tête
    X-Academic-Year.

    - Administrateurs (super-utilisateurs, rôles admin) : accès complet.
    - Personnel : selon le droit « Années archivées » de son rôle (`Role.acces_annees_archivees`) :
      « none » = refusé, « lecture » = consultation seule (GET), « ecriture » = consultation et
      modification. Les droits par domaine (StaffAccessMiddleware) s'appliquent ensuite.
    - Comptes portail (étudiant, formateur) : pas de rôle, donc pas d'accès aux archives.

    Le jeton JWT est lu directement (`request.user` ne connaît que la session à ce stade).
    Une année inconnue est ignorée ; la liste des années reste accessible pour que le frontend
    puisse corriger une sélection périmée.
    """

    EXEMPT_PREFIXES = ("/api/auth/", "/api/v2/annees-academiques/", "/api/v2/configuration-etablissement/", "/admin/")
    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        academic_year_id = request.headers.get('X-Academic-Year')

        if not academic_year_id or request.path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)

        try:
            year_id = int(academic_year_id)
        except (TypeError, ValueError):
            return self.get_response(request)

        from users.middleware import jwt_user
        user = jwt_user(request)
        if not user or user.is_superuser:
            return self.get_response(request)

        from .models import AnneeAcademique

        year = AnneeAcademique.objects.filter(pk=year_id).only("est_active", "libelle").first()
        if year is None or year.est_active:
            return self.get_response(request)

        from users.acces_personnel import niveau_annees_archivees

        niveau = niveau_annees_archivees(user)
        if niveau == "ecriture" or (niveau == "lecture" and request.method in self.SAFE_METHODS):
            return self.get_response(request)
        if niveau == "lecture":
            detail = (f"L'année {year.libelle} est archivée : votre rôle peut la consulter mais pas la modifier.")
        else:
            detail = (f"L'année {year.libelle} est archivée : votre rôle n'y a pas accès. "
                      "Demandez à l'administrateur le droit « Années archivées ».")
        return JsonResponse({'detail': detail, 'error': detail}, status=403)


def get_current_academic_year_id():
    val = _current_academic_year_id.get()
    if not val:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
