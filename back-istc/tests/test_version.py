"""La version livrée est la même partout (VERSION, application, package.json, API)."""
import json

from django.conf import settings

RACINE = settings.BASE_DIR.parent


def test_versions_coherentes():
    version = (RACINE / "VERSION").read_text(encoding="utf-8").strip()
    historique = json.loads((RACINE / "frontend/src/config/versions.json").read_text(encoding="utf-8"))
    paquet = json.loads((RACINE / "frontend/package.json").read_text(encoding="utf-8"))
    assert historique["versions"][0]["version"] == version
    assert paquet["version"] == version
    assert settings.APP_VERSION == version
    assert settings.SPECTACULAR_SETTINGS["VERSION"] == version


def test_historique_bien_forme():
    historique = json.loads((RACINE / "frontend/src/config/versions.json").read_text(encoding="utf-8"))
    for v in historique["versions"]:
        assert set(v) >= {"version", "date", "changements"}
        assert v["changements"], f"version {v['version']} sans nouveauté"


def test_origine_cors_completee():
    from smart_back.settings import _origine_cors
    assert _origine_cors("ecole.cm") == "https://ecole.cm"
    assert _origine_cors(" https://ecole.cm/ ") == "https://ecole.cm"
    assert _origine_cors("http://localhost:3000/login") == "http://localhost:3000"
