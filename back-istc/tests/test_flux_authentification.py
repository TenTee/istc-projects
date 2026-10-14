"""
Flux : connexion à la plateforme.

Couvre : connexion réussie (personnel, étudiant, formateur), refus (mauvais mot de passe,
compte désactivé, compte formateur orphelin), rafraîchissement du jeton, reCAPTCHA.
"""
import json
from unittest import mock

import pytest
from django.contrib.auth import get_user_model

from smart_back.testing import client_api, creer_utilisateur

User = get_user_model()
LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"

pytestmark = pytest.mark.django_db


def _compte(role="admin", mot_de_passe="MotDePasse123", **kwargs):
    user = creer_utilisateur(role=role, **kwargs)
    user.set_password(mot_de_passe)
    user.save()
    return user


def test_connexion_reussie_renvoie_jetons_et_profil(client_anonyme):
    user = _compte()
    res = client_anonyme.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json")
    assert res.status_code == 200, res.data
    assert {"access", "refresh", "user"} <= set(res.data)
    assert res.data["user"]["role"] == "admin"
    assert res.data["user"]["is_formateur"] is False


def test_mauvais_mot_de_passe_refuse(client_anonyme):
    user = _compte()
    res = client_anonyme.post(LOGIN, {"username": user.username, "password": "faux"}, format="json")
    assert res.status_code == 401


def test_compte_desactive_refuse(client_anonyme):
    user = _compte(is_active=False)
    res = client_anonyme.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json")
    assert res.status_code == 401


def test_compte_formateur_sans_profil_refuse(client_anonyme):
    """Un formateur supprimé ne doit plus pouvoir se connecter avec son ancien compte."""
    user = _compte(role="formateur")
    res = client_anonyme.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json")
    assert res.status_code == 401


def test_jeton_contient_les_droits_du_role(client_anonyme):
    from users.models import Role
    Role.objects.create(code="comptable", libelle="Comptable", can_manage_finance="ecriture")
    user = _compte(role="comptable")
    res = client_anonyme.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json")
    from rest_framework_simplejwt.tokens import AccessToken
    jeton = AccessToken(res.data["access"])
    assert jeton["permissions"]["can_manage_finance"] == "ecriture"
    assert jeton["permissions"]["can_manage_rh"] == "none"


def test_connexion_possible_meme_avec_un_ancien_jeton_invalide():
    """Un jeton périmé resté dans le navigateur ne doit pas bloquer la connexion."""
    user = _compte()
    client = client_api()
    client.credentials(HTTP_AUTHORIZATION="Bearer jeton.invalide.ancien")
    res = client.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json")
    assert res.status_code == 200


def test_rafraichissement_du_jeton(client_anonyme):
    user = _compte()
    jetons = client_anonyme.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json").data
    res = client_anonyme.post(REFRESH, {"refresh": jetons["refresh"]}, format="json")
    assert res.status_code == 200
    assert "access" in res.data


def test_connexion_etudiant_avec_identifiants_generes(monde):
    """Le compte d'un étudiant est créé automatiquement avec un mot de passe initial."""
    etudiant = monde.nouvel_etudiant()
    assert etudiant.user is not None and etudiant.user.role == "etudiant"
    assert etudiant.initial_password
    res = client_api().post(
        LOGIN, {"username": etudiant.user.username, "password": etudiant.initial_password}, format="json"
    )
    assert res.status_code == 200
    assert res.data["user"]["role"] == "etudiant"


def test_connexion_formateur_apres_generation_du_compte(monde, client_admin):
    formateur = monde.nouveau_formateur(avec_compte=False)
    res = client_admin.post(f"/api/formateurs/{formateur.id}/generate-account/")
    assert res.status_code == 200, res.data
    res = client_api().post(LOGIN, {"username": res.data["username"], "password": res.data["password"]}, format="json")
    assert res.status_code == 200
    assert res.data["user"]["is_formateur"] is True


class TestRecaptcha:
    def test_exige_le_jeton_quand_la_cle_est_configuree(self, monkeypatch, client_anonyme):
        monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "secret")
        user = _compte()
        res = client_anonyme.post(LOGIN, {"username": user.username, "password": "MotDePasse123"}, format="json")
        assert res.status_code == 400
        assert "recaptcha" in res.data

    def test_accepte_un_jeton_valide(self, monkeypatch, client_anonyme):
        monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "secret")
        user = _compte()
        reponse_google = mock.MagicMock()
        reponse_google.read.return_value = json.dumps({"success": True}).encode()
        reponse_google.__enter__.return_value = reponse_google
        with mock.patch("users.recaptcha.urllib.request.urlopen", return_value=reponse_google):
            res = client_anonyme.post(
                LOGIN, {"username": user.username, "password": "MotDePasse123", "recaptcha_token": "ok"}, format="json"
            )
        assert res.status_code == 200

    def test_refuse_un_jeton_invalide(self, monkeypatch, client_anonyme):
        monkeypatch.setenv("RECAPTCHA_SECRET_KEY", "secret")
        user = _compte()
        reponse_google = mock.MagicMock()
        reponse_google.read.return_value = json.dumps({"success": False}).encode()
        reponse_google.__enter__.return_value = reponse_google
        with mock.patch("users.recaptcha.urllib.request.urlopen", return_value=reponse_google):
            res = client_anonyme.post(
                LOGIN, {"username": user.username, "password": "MotDePasse123", "recaptcha_token": "ko"}, format="json"
            )
        assert res.status_code == 400
