"""
Fixtures pytest partagées par toutes les applications.

    def test_quelque_chose(monde, client_admin):
        etudiant = monde.nouvel_etudiant()
        res = client_admin.get("/api/etudiants/")
        assert res.status_code == 200
"""
import shutil
import tempfile

import pytest

from smart_back.testing import Monde, client_api


@pytest.fixture(autouse=True)
def _media_temporaire(settings):
    """Les fichiers envoyés pendant les tests vont dans un dossier jetable, pas dans media/."""
    dossier = tempfile.mkdtemp(prefix="smartcampus-tests-")
    settings.MEDIA_ROOT = dossier
    yield
    shutil.rmtree(dossier, ignore_errors=True)


@pytest.fixture(autouse=True)
def _sans_recaptcha(monkeypatch):
    """La vérification reCAPTCHA (réseau) est désactivée pendant les tests."""
    monkeypatch.delenv("RECAPTCHA_SECRET_KEY", raising=False)


@pytest.fixture
def monde(db):
    return Monde.creer()


@pytest.fixture
def client_admin(monde):
    return client_api(monde.admin)


@pytest.fixture
def client_anonyme():
    return client_api()
