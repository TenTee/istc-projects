"""Commande `creer_superadmin` : compte complet (rôle superadmin), mot de passe jamais en argument."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from smart_back.testing import client_api

pytestmark = pytest.mark.django_db
MDP = "Chef-Etablissement-2026"


def test_creation_sans_question(monkeypatch):
    monkeypatch.setenv("SMARTCAMPUS_ADMIN_PASSWORD", MDP)
    call_command("creer_superadmin", "--nom", "direction", "--email", "direction@ecole.cm", "--sans-question")
    user = get_user_model().objects.get(username="direction")
    assert user.is_superuser and user.is_staff and user.is_active and user.role == "superadmin"
    assert user.check_password(MDP)
    res = client_api().post("/api/auth/login/", {"username": "direction", "password": MDP}, format="json")
    assert res.status_code == 200


def test_creation_interactive(monkeypatch):
    reponses = iter(["chef.scolarite", "chef@ecole.cm"])
    monkeypatch.setattr("builtins.input", lambda invite: next(reponses))
    mdps = iter(["court", "court", MDP, MDP])
    monkeypatch.setattr("users.management.commands.creer_superadmin.getpass", lambda invite: next(mdps))
    monkeypatch.delenv("SMARTCAMPUS_ADMIN_PASSWORD", raising=False)
    call_command("creer_superadmin")
    assert get_user_model().objects.get(username="chef.scolarite").check_password(MDP)


def test_refus(monkeypatch):
    monkeypatch.setenv("SMARTCAMPUS_ADMIN_PASSWORD", MDP)
    call_command("creer_superadmin", "--nom", "direction", "--email", "direction@ecole.cm", "--sans-question")
    with pytest.raises(CommandError, match="déjà utilisé"):
        call_command("creer_superadmin", "--nom", "DIRECTION", "--email", "autre@ecole.cm", "--sans-question")
    with pytest.raises(CommandError, match="déjà utilisé"):
        call_command("creer_superadmin", "--nom", "autre", "--email", "direction@ecole.cm", "--sans-question")
    with pytest.raises(CommandError, match="refusé"):
        call_command("creer_superadmin", "--nom", "avec espace", "--email", "x@ecole.cm", "--sans-question")
    monkeypatch.setenv("SMARTCAMPUS_ADMIN_PASSWORD", "123")
    with pytest.raises(CommandError, match="Mot de passe refusé"):
        call_command("creer_superadmin", "--nom", "autre", "--email", "y@ecole.cm", "--sans-question")
    monkeypatch.delenv("SMARTCAMPUS_ADMIN_PASSWORD")
    with pytest.raises(CommandError, match="SMARTCAMPUS_ADMIN_PASSWORD"):
        call_command("creer_superadmin", "--nom", "autre", "--email", "y@ecole.cm", "--sans-question")
