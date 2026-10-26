"""Tests du versionnage automatique : python -m pytest outils/version -q"""
import json
import subprocess
from pathlib import Path

import pytest

import versionner as v


def test_incrementer():
    assert v.incrementer("1.4.2", "correctif") == "1.4.3"
    assert v.incrementer("1.4.2", "mineure") == "1.5.0"
    assert v.incrementer("1.4.2", "majeure") == "2.0.0"
    with pytest.raises(ValueError):
        v.incrementer("1.4", "correctif")


def test_lire_nouveautes_ignore_le_commentaire_du_modele():
    niveau, lignes = v.lire_nouveautes(v.ENTETE_NOUVEAUTES)
    assert niveau == "correctif"
    assert lignes == []
    niveau, lignes = v.lire_nouveautes("Niveau : Mineure\n\n- Export PDF des reçus\n* Correction du filtre\n")
    assert niveau == "mineure"
    assert lignes == ["Export PDF des reçus", "Correction du filtre"]


def test_niveau_des_commits():
    assert v.niveau_des_commits(["corrige le filtre des classes"]) == "correctif"
    assert v.niveau_des_commits(["ajoute les reçus [mineure]"]) == "mineure"
    assert v.niveau_des_commits(["[mineure] a", "refonte des droits [majeure]"]) == "majeure"


def test_sujets_vides_de_sens_ecartes():
    assert v.nettoyer_sujet("commit") is None
    assert v.nettoyer_sujet("new changes") is None
    assert v.nettoyer_sujet("fix(notes): arrondi de la note finale [mineure]") == "Arrondi de la note finale."
    assert v.changements_des_commits(["commit", "wip"]) == [v.MESSAGE_PAR_DEFAUT]


# --------------------------------------------------------------------------- dépôt de test

def git(depot, *args):
    subprocess.run(["git", *args], cwd=depot, check=True, capture_output=True)


@pytest.fixture
def depot(tmp_path: Path):
    (tmp_path / "frontend/src/config").mkdir(parents=True)
    (tmp_path / "frontend/src/config/versions.json").write_text(json.dumps(
        {"versions": [{"version": "0.1.0", "date": "2026-10-13", "niveau": "mineure", "changements": ["Départ."]}]}))
    (tmp_path / "frontend/package.json").write_text('{\n  "name": "smart-front",\n  "version": "0.1.0",\n  "private": true\n}\n')
    (tmp_path / "frontend/package-lock.json").write_text(
        '{\n  "name": "smart-front",\n  "version": "0.1.0",\n  "packages": {\n    "": {\n      "name": "smart-front",\n'
        '      "version": "0.1.0"\n    },\n    "node_modules/x": {\n      "version": "9.9.9"\n    }\n  }\n}\n')
    (tmp_path / "NOUVEAUTES.md").write_text(v.ENTETE_NOUVEAUTES)
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "tag", "v0.1.0")
    return tmp_path


def commit(depot, message, fichier="a.txt"):
    (depot / fichier).write_text(message)
    git(depot, "add", "-A")
    git(depot, "commit", "-qm", message)


def test_livraison_corrective_depuis_les_commits(depot):
    commit(depot, "corrige le calcul du solde des congés")
    entree = v.versionner(depot, date="2026-10-24")
    assert entree["version"] == "0.1.1"
    assert entree["changements"] == ["Corrige le calcul du solde des congés."]
    donnees = json.loads((depot / "frontend/src/config/versions.json").read_text())
    assert [x["version"] for x in donnees["versions"]] == ["0.1.1", "0.1.0"]
    assert (depot / "VERSION").read_text().strip() == "0.1.1"
    assert '"version": "0.1.1"' in (depot / "frontend/package.json").read_text()
    lock = (depot / "frontend/package-lock.json").read_text()
    assert lock.count('"version": "0.1.1"') == 2 and '"version": "9.9.9"' in lock   # dépendances intactes
    assert "## 0.1.1 — 24/10/2026" in (depot / "CHANGELOG.md").read_text()


def test_nouveautes_md_prioritaire_puis_vide(depot):
    (depot / "NOUVEAUTES.md").write_text("Niveau : mineure\n\n- Reçus de paiement en PDF\n")
    commit(depot, "commit")
    entree = v.versionner(depot)
    assert entree["version"] == "0.2.0"
    assert entree["changements"] == ["Reçus de paiement en PDF"]
    assert v.lire_nouveautes((depot / "NOUVEAUTES.md").read_text()) == ("correctif", [])


def test_marqueur_de_commit_l_emporte_sur_le_niveau_par_defaut(depot):
    commit(depot, "nouveau module de délibérations [majeure]")
    assert v.versionner(depot, simulation=True)["version"] == "1.0.0"


def test_pas_de_version_sans_commit_ni_avec_sans_version(depot):
    assert v.versionner(depot) is None
    commit(depot, "faute de frappe dans la doc [sans version]")
    assert v.versionner(depot) is None
    assert (depot / "frontend/src/config/versions.json").read_text().count('"version"') == 1


def test_le_commit_du_robot_n_est_pas_compte(depot):
    commit(depot, "ajoute le filtre par filière")
    v.versionner(depot)
    git(depot, "add", "-A")
    git(depot, "commit", "-qm", "chore(version): v0.1.1 [skip ci]")
    git(depot, "tag", "v0.1.1")
    assert v.versionner(depot) is None


def test_reference_depuis_invalide_retombe_sur_l_etiquette(depot):
    commit(depot, "ajoute le filtre par filière")
    entree = v.versionner(depot, depuis="0000000000000000000000000000000000000000", simulation=True)
    assert entree["changements"] == ["Ajoute le filtre par filière."]
