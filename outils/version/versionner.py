#!/usr/bin/env python3
"""Versionnage automatique de SmartCampus.

Lancé par la GitHub Action `.github/workflows/version.yml` à chaque push sur `main`.
On peut aussi le lancer à la main :

    python3 outils/version/versionner.py --depuis v0.1.0 --simulation

Ce que fait le script :
1. Lit les commits depuis la dernière livraison (`--depuis`, sinon la dernière étiquette `v*`).
2. Choisit le niveau :
   - `Niveau : majeure | mineure | correctif` dans NOUVEAUTES.md, s'il est indiqué ;
   - sinon `[majeure]` ou `[mineure]` dans un message de commit ;
   - sinon correctif.
3. Prend les nouveautés dans NOUVEAUTES.md (lignes « - … »), à défaut dans les messages de commit.
4. Met à jour :
   - `frontend/src/config/versions.json`, lu par l'application (barre latérale → « Nouveautés ») ;
   - `VERSION` ;
   - `CHANGELOG.md` ;
   - la version de `frontend/package.json` et de `package-lock.json`.
5. Vide NOUVEAUTES.md pour la livraison suivante.

Rien n'est publié si aucun commit n'a été fait depuis la dernière livraison, ou si un commit contient
`[sans version]` et que NOUVEAUTES.md est vide.
Le script ne fait ni commit ni étiquette : la GitHub Action s'en charge.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
NIVEAUX = ("correctif", "mineure", "majeure")
MARQUEURS = {
    "majeure": re.compile(r"\[(majeure|major|breaking)\]|BREAKING CHANGE", re.I),
    "mineure": re.compile(r"\[(mineure|minor|fonctionnalit[ée])\]", re.I),
}
SANS_VERSION = re.compile(r"\[(sans version|skip version)\]", re.I)
COMMIT_DE_VERSION = re.compile(r"^chore\(version\)")
MESSAGE_PAR_DEFAUT = "Améliorations et corrections diverses."
ENTETE_NOUVEAUTES = """# Nouveautés de la prochaine livraison

<!--
Décrivez ici, pour les utilisateurs, ce que contient la prochaine livraison.
Une ligne commençant par « - » par nouveauté. À chaque push sur main, ces lignes
deviennent les « Nouveautés » de la nouvelle version, puis le fichier est vidé.
Facultatif : indiquez le niveau (correctif, mineure ou majeure) sur la ligne « Niveau ».
Sans aucune ligne « - », les messages de commit sont utilisés.
-->

Niveau : correctif

"""


# --------------------------------------------------------------------------- git

def git(*args: str, racine: Path = RACINE) -> str:
    res = subprocess.run(["git", *args], cwd=racine, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip())
    return res.stdout


def reference_valide(ref: str | None, racine: Path) -> bool:
    if not ref or set(ref) == {"0"}:
        return False
    try:
        git("rev-parse", "--verify", "--quiet", ref + "^{commit}", racine=racine)
        return True
    except RuntimeError:
        return False


def derniere_etiquette(racine: Path) -> str | None:
    try:
        return git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", racine=racine).strip() or None
    except RuntimeError:
        return None


def commits_depuis(depuis: str | None, racine: Path) -> list[str]:
    """Messages complets des commits de `depuis` (exclu) à HEAD, du plus ancien au plus récent."""
    plage = f"{depuis}..HEAD" if depuis else "HEAD"
    sortie = git("log", "--no-merges", "--reverse", "--format=%B%x1e", plage, racine=racine)
    messages = [m.strip() for m in sortie.split("\x1e") if m.strip()]
    return [m for m in messages if not COMMIT_DE_VERSION.match(m)]


# --------------------------------------------------------------------------- règles

def incrementer(version: str, niveau: str) -> str:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version.strip())
    if not m:
        raise ValueError(f"Version invalide : {version!r} (attendu : X.Y.Z)")
    maj, mineure, corr = map(int, m.groups())
    if niveau == "majeure":
        return f"{maj + 1}.0.0"
    if niveau == "mineure":
        return f"{maj}.{mineure + 1}.0"
    return f"{maj}.{mineure}.{corr + 1}"


def lire_nouveautes(texte: str) -> tuple[str | None, list[str]]:
    """Retourne (niveau indiqué ou None, lignes de nouveautés)."""
    texte = re.sub(r"<!--.*?-->", "", texte, flags=re.S)
    niveau = None
    m = re.search(r"^\s*Niveau\s*:\s*(\w+)", texte, re.M | re.I)
    if m:
        valeur = m.group(1).lower().replace("é", "e")
        niveau = {"correctif": "correctif", "patch": "correctif", "mineure": "mineure", "minor": "mineure",
                  "majeure": "majeure", "major": "majeure"}.get(valeur)
    lignes = [re.sub(r"^\s*[-*]\s+", "", l).strip() for l in texte.splitlines() if re.match(r"^\s*[-*]\s+\S", l)]
    return niveau, lignes


def niveau_des_commits(messages: list[str]) -> str:
    texte = "\n".join(messages)
    if MARQUEURS["majeure"].search(texte):
        return "majeure"
    if MARQUEURS["mineure"].search(texte):
        return "mineure"
    return "correctif"


def nettoyer_sujet(message: str) -> str | None:
    """Sujet de commit lisible pour un utilisateur, ou None s'il n'apporte rien."""
    sujet = message.splitlines()[0]
    sujet = re.sub(r"\[[^\]]*\]", "", sujet)                       # marqueurs [mineure], [skip ci]…
    sujet = re.sub(r"^(feat|fix|chore|docs|refactor|style|test|perf)(\([^)]*\))?!?:\s*", "", sujet, flags=re.I)
    sujet = re.sub(r"\s+", " ", sujet).strip(" .-")
    if len(sujet.split()) < 3:                                      # « commit », « new changes », « correctif »…
        return None
    return sujet[0].upper() + sujet[1:] + ("" if sujet.endswith(("!", "?")) else ".")


def changements_des_commits(messages: list[str]) -> list[str]:
    vus, resultat = set(), []
    for m in messages:
        s = nettoyer_sujet(m)
        if s and s.lower() not in vus:
            vus.add(s.lower())
            resultat.append(s)
    return resultat or [MESSAGE_PAR_DEFAUT]


# --------------------------------------------------------------------------- fichiers

def ecrire_changelog(versions: list[dict], chemin: Path) -> None:
    lignes = ["# Journal des modifications", "",
              "Généré automatiquement à chaque livraison (`outils/version/versionner.py`). Ne pas modifier à la main :",
              "écrivez les nouveautés de la prochaine livraison dans `NOUVEAUTES.md`.", ""]
    for v in versions:
        date = dt.date.fromisoformat(v["date"]).strftime("%d/%m/%Y")
        lignes += [f"## {v['version']} — {date}", ""] + [f"- {c}" for c in v["changements"]] + [""]
    chemin.write_text("\n".join(lignes), encoding="utf-8")


def maj_version_npm(chemin: Path, version: str) -> None:
    if not chemin.exists():
        return
    texte = chemin.read_text(encoding="utf-8")
    nouveau, n = re.subn(r'("name": "smart-front",\s*"version": ")[^"]+(")', rf"\g<1>{version}\g<2>", texte)
    if n:
        chemin.write_text(nouveau, encoding="utf-8")


def versionner(racine: Path, depuis: str | None = None, niveau_force: str | None = None,
               date: str | None = None, simulation: bool = False) -> dict | None:
    fichier_versions = racine / "frontend/src/config/versions.json"
    donnees = json.loads(fichier_versions.read_text(encoding="utf-8"))
    versions = donnees["versions"]
    actuelle = versions[0]["version"]

    if not reference_valide(depuis, racine):
        depuis = derniere_etiquette(racine)
    messages = commits_depuis(depuis, racine)
    fichier_nouveautes = racine / "NOUVEAUTES.md"
    niveau_fichier, lignes = lire_nouveautes(fichier_nouveautes.read_text(encoding="utf-8")) if fichier_nouveautes.exists() else (None, [])

    if not messages and not lignes:
        print("Aucun commit depuis la dernière livraison : pas de nouvelle version.")
        return None
    if not lignes and any(SANS_VERSION.search(m) for m in messages):
        print("Commit marqué [sans version] : pas de nouvelle version.")
        return None

    niveau = niveau_force or niveau_fichier or niveau_des_commits(messages)
    if niveau_fichier == "correctif" and not niveau_force:
        # la ligne « Niveau : correctif » du modèle n'empêche pas un [mineure]/[majeure] dans un commit
        niveau = max(niveau_fichier, niveau_des_commits(messages), key=NIVEAUX.index)
    nouvelle = incrementer(actuelle, niveau)
    entree = {
        "version": nouvelle,
        "date": date or dt.date.today().isoformat(),
        "niveau": niveau,
        "changements": lignes or changements_des_commits(messages),
    }
    if simulation:
        print(json.dumps(entree, ensure_ascii=False, indent=2))
        return entree

    donnees["versions"] = [entree] + versions
    fichier_versions.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (racine / "VERSION").write_text(nouvelle + "\n", encoding="utf-8")
    ecrire_changelog(donnees["versions"], racine / "CHANGELOG.md")
    maj_version_npm(racine / "frontend/package.json", nouvelle)
    maj_version_npm(racine / "frontend/package-lock.json", nouvelle)
    fichier_nouveautes.write_text(ENTETE_NOUVEAUTES, encoding="utf-8")
    print(f"Nouvelle version : {actuelle} → {nouvelle} ({niveau})")
    return entree


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--depuis", help="commit ou étiquette de la livraison précédente (défaut : dernière étiquette v*)")
    ap.add_argument("--niveau", choices=NIVEAUX, help="imposer le niveau d'incrément")
    ap.add_argument("--date", help="date de la version (AAAA-MM-JJ, défaut : aujourd'hui)")
    ap.add_argument("--simulation", action="store_true", help="afficher la version calculée sans rien écrire")
    args = ap.parse_args()
    entree = versionner(RACINE, args.depuis, args.niveau, args.date, args.simulation)
    sortie = os.environ.get("GITHUB_OUTPUT")
    if sortie:
        with open(sortie, "a", encoding="utf-8") as f:
            f.write(f"version={entree['version'] if entree and not args.simulation else ''}\n")
            if entree and not args.simulation:
                notes = "\n".join(f"- {c}" for c in entree["changements"])
                f.write(f"notes<<FIN_NOTES\n{notes}\nFIN_NOTES\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
