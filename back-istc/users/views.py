from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction

from rest_framework_simplejwt.views import TokenObtainPairView
from .models import CustomUser, Role
from .permissions import RolePermission, UserAccountPermission
from .recaptcha import verify_recaptcha
from .serializers import UserSerializer, RoleSerializer, MyTokenObtainPairSerializer
from .utils import erreur_nom_utilisateur, erreurs_mot_de_passe, identifiants, reinitialiser_mot_de_passe


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD sur les rôles : lecture pour tous les connectés, écriture réservée à l'administration."""
    queryset = Role.objects.all().order_by("libelle")
    serializer_class = RoleSerializer
    permission_classes = [RolePermission]


class UserViewSet(viewsets.ModelViewSet):
    """Gestion des comptes : réservée à l'administration (chacun peut lire sa propre fiche)."""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [UserAccountPermission]

    # Le modèle génère lui-même username et mot de passe (exposé une fois via `raw_password`).

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        if user.is_superuser and not request.user.is_superuser:
            return Response({"detail": "Seul un super-administrateur peut réinitialiser ce compte."},
                            status=status.HTTP_403_FORBIDDEN)
        mot_de_passe = reinitialiser_mot_de_passe(user)
        donnees = identifiants(user, mot_de_passe)
        donnees["new_password"] = mot_de_passe  # ancien nom du champ, gardé pour compatibilité
        return Response(donnees, status=status.HTTP_200_OK)


class MonCompteView(APIView):
    """Le compte de l'utilisateur connecté (« Mon profil ») : lecture et changement du nom d'utilisateur.

    Ouvert à tous les comptes connectés, portails compris (voir PORTAL_RULES).
    """
    permission_classes = [IsAuthenticated]

    def _donnees(self, user):
        role_libelle = Role.objects.filter(code=user.role).values_list("libelle", flat=True).first()
        if user.is_superuser and not role_libelle:
            role_libelle = "Super-administrateur"
        return {
            "id": user.id,
            "username": user.username,
            "noms": user.noms,
            "prenoms": user.prenoms,
            "email": user.email,
            "role": user.role,
            "role_libelle": role_libelle or user.role,
            "derniere_connexion": user.last_login,
        }

    def get(self, request):
        return Response(self._donnees(request.user))

    def patch(self, request):
        user = request.user
        nouveau = (request.data.get("username") or "").strip()
        if not nouveau:
            return Response({"username": ["Indiquez le nouveau nom d'utilisateur."]}, status=400)
        if nouveau != user.username:
            erreur = erreur_nom_utilisateur(nouveau, user=user)
            if erreur:
                return Response({"username": [erreur]}, status=400)
            if not user.check_password(request.data.get("mot_de_passe_actuel") or ""):
                return Response({"mot_de_passe_actuel": ["Mot de passe actuel incorrect."]}, status=400)
            user.username = nouveau
            user.save(update_fields=["username"])
        return Response(self._donnees(user))


class ChangerMotDePasseView(APIView):
    """Changement de son propre mot de passe : l'ancien est exigé, le nouveau doit passer les validateurs."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        actuel = request.data.get("mot_de_passe_actuel") or ""
        nouveau = request.data.get("nouveau_mot_de_passe") or ""
        confirmation = request.data.get("confirmation")
        if not user.check_password(actuel):
            return Response({"mot_de_passe_actuel": ["Mot de passe actuel incorrect."]}, status=400)
        if confirmation is not None and confirmation != nouveau:
            return Response({"confirmation": ["Les deux saisies du nouveau mot de passe sont différentes."]}, status=400)
        if nouveau == actuel:
            return Response({"nouveau_mot_de_passe": ["Le nouveau mot de passe doit être différent de l'actuel."]}, status=400)
        erreurs = erreurs_mot_de_passe(nouveau, user=user)
        if erreurs:
            return Response({"nouveau_mot_de_passe": erreurs}, status=400)
        user.set_password(nouveau)
        user.save(update_fields=["password"])
        # Le mot de passe provisoire d'un étudiant n'est plus valable : on ne le garde pas en clair.
        from etudiants.models import Etudiant
        Etudiant.objects.filter(user=user).exclude(initial_password__isnull=True).update(initial_password=None)
        return Response({"detail": "Mot de passe modifié."})


class MyTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        verify_recaptcha(request)
        return super().post(request, *args, **kwargs)
