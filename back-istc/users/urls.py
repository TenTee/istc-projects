# users/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import UserViewSet, RoleViewSet, MonCompteView, ChangerMotDePasseView

router = DefaultRouter()
router.register(r"roles", RoleViewSet, basename="role")  # /api/users/roles/
router.register(r"", UserViewSet, basename="user")       # /api/users/

urlpatterns = [
    # « Mon profil » : avant le routeur, sinon « me » serait lu comme l'identifiant d'un compte.
    path("me/", MonCompteView.as_view(), name="mon-compte"),
    path("me/mot-de-passe/", ChangerMotDePasseView.as_view(), name="mon-mot-de-passe"),
] + router.urls