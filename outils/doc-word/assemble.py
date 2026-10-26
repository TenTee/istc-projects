"""Assemble la documentation MkDocs (docs/) en un seul Markdown pour pandoc → Word."""
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
IMG = os.path.join(OUT, "img")
# Chromium pour mmdc (facultatif) : export PUPPETEER_CONFIG=/chemin/config.json
PUPPETEER = ["-p", os.environ["PUPPETEER_CONFIG"]] if os.environ.get("PUPPETEER_CONFIG") else []
os.makedirs(OUT, exist_ok=True)
os.makedirs(IMG, exist_ok=True)

PARTIES = [
    ("Partie 1 — Guide d'utilisation", [
        "guide/index.md", "guide/premiers-pas.md", "guide/roles-et-acces.md",
        "guide/demarrer-une-annee.md", "guide/preinscription-candidat.md",
        "guide/administration/index.md",
        "guide/administration/tableau-de-bord.md", "guide/administration/structure-academique.md",
        "guide/administration/cours.md", "guide/administration/etudiants.md",
        "guide/administration/enseignants.md", "guide/administration/emploi-du-temps.md",
        "guide/administration/notes.md", "guide/administration/banque-epreuves.md",
        "guide/administration/assiduite.md", "guide/administration/coordonnateurs.md",
        "guide/administration/preinscriptions.md", "guide/administration/scolarite.md",
        "guide/administration/apercu-financier.md", "guide/administration/salaires.md",
        "guide/administration/heures-vacataires.md", "guide/administration/inventaire.md",
        "guide/administration/personnel-conges.md", "guide/administration/systeme.md",
        "guide/portail-formateur.md", "guide/coordonnateur.md", "guide/portail-etudiant.md",
        "guide/faq.md", "guide/glossaire.md",
    ]),
    ("Partie 2 — Installation et configuration", [
        "installation/index.md", "installation/prerequis.md", "installation/installation-locale.md",
        "installation/deploiement-serveur.md", "installation/configuration.md",
        "installation/sauvegardes.md", "installation/mise-a-jour.md", "installation/depannage.md",
    ]),
    ("Partie 3 — Documentation développeurs", [
        "developpeurs/index.md", "developpeurs/architecture.md", "developpeurs/applications.md",
        "developpeurs/permissions.md", "developpeurs/tests.md",
        "developpeurs/ajouter-une-fonctionnalite.md", "developpeurs/conventions.md",
        "developpeurs/api.md", "../CONTRIBUTING.md",
    ]),
]

STYLES = {"tip": "Encadre Conseil", "info": "Encadre Info", "note": "Encadre Info",
          "warning": "Encadre Attention", "danger": "Encadre Danger", "success": "Encadre Succes"}
TITRES = {"tip": "Conseil", "info": "Information", "note": "Remarque", "warning": "Attention",
          "danger": "Important", "success": "Bon à savoir"}
KEYS = {"ctrl": "Ctrl", "enter": "Entrée", "f5": "F5", "caps-lock": "Verr. Maj", "cmd": "Cmd",
        "f12": "F12", "shift": "Maj"}

mermaid_n = [0]


def keys(m):
    return "**" + "+".join(KEYS.get(k, k.upper()) for k in m.group(1).split("+")) + "**"


def render_mermaid(code):
    mermaid_n[0] += 1
    base = os.path.join(IMG, f"diagramme_{mermaid_n[0]:02d}")
    with open(base + ".mmd", "w") as f:
        f.write(code)
    if not os.path.exists(base + ".png"):
        subprocess.run(["mmdc", "-i", base + ".mmd", "-o", base + ".png", *PUPPETEER,
                        "-s", "3", "-b", "white", "-c", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mermaid.json")],
                       check=True, capture_output=True, timeout=120)
    return base + ".png"


def convertir(texte, page):
    lignes = texte.split("\n")
    out = []
    i = 0
    while i < len(lignes):
        l = lignes[i]
        # Diagrammes Mermaid
        if l.strip() == "```mermaid":
            ind = l[: len(l) - len(l.lstrip())]
            code = []
            i += 1
            while lignes[i].strip() != "```":
                code.append(lignes[i][len(ind):])
                i += 1
            png = render_mermaid("\n".join(code))
            try:
                from PIL import Image
                w, h = Image.open(png).size
                largeur = min(15.0, 11.0 * w / h)  # hauteur maximale ≈ 11 cm
            except Exception:
                largeur = 15.0
            out.append(f"{ind}![]({png}){{width={largeur:.1f}cm}}")
            i += 1
            continue
        # Encadrés  !!! type "titre"   /  ??? question "titre"
        m = re.match(r'^(\s*)(!!!|\?\?\?\+?)\s+(\w+)(?:\s+"(.*)")?\s*$', l)
        if m:
            ind, kind, typ, titre = m.group(1), m.group(2), m.group(3), m.group(4)
            corps = []
            i += 1
            while i < len(lignes) and (not lignes[i].strip() or lignes[i].startswith(ind + "    ")):
                corps.append(lignes[i][len(ind) + 4:] if lignes[i].strip() else "")
                i += 1
            while corps and not corps[-1]:
                corps.pop()
            corps_txt = convertir("\n".join(corps), page)
            if kind.startswith("???"):  # FAQ : question en gras puis réponse
                out += [f"{ind}::: {{custom-style=\"Question FAQ\"}}", f"{ind}{titre}", f"{ind}:::", ""]
                out += [ind + c if c else "" for c in corps_txt.split("\n")]
                out.append("")
                continue
            style = STYLES.get(typ, "Encadre Info")
            titre = titre or TITRES.get(typ, "Remarque")
            out += [f"{ind}::: {{custom-style=\"{style}\"}}", f"{ind}**{titre}**", ""]
            out += [ind + c if c else "" for c in corps_txt.split("\n")]
            out += [f"{ind}:::", "", f"{ind}```{{=openxml}}", f'{ind}<w:p><w:pPr><w:spacing w:before="0" w:after="60"/><w:rPr><w:sz w:val="8"/></w:rPr></w:pPr></w:p>', f"{ind}```", ""]
            continue
        # Onglets === "Mac / Linux"
        m = re.match(r'^(\s*)===\s+"(.*)"\s*$', l)
        if m:
            ind = m.group(1)
            out += [f"{ind}**{m.group(2)}**", ""]
            i += 1
            while i < len(lignes) and (not lignes[i].strip() or lignes[i].startswith(ind + "    ")):
                out.append(lignes[i][len(ind) + 4:] if lignes[i].strip() else "")
                i += 1
            continue
        out.append(l)
        i += 1
    texte = "\n".join(out)
    # Hors blocs de code : liens internes → texte, touches, cases à cocher
    morceaux = re.split(r"(```.*?```)", texte, flags=re.S)
    for k in range(0, len(morceaux), 2):
        t = morceaux[k]
        # Images (captures d'écran) : chemin absolu + largeur adaptée à la page A4
        t = re.sub(r"!\[([^\]]*)\]\((?!https?:|/)([^)\s]+)\)",
                   lambda m: f"![{m.group(1)}]({os.path.normpath(os.path.join(DOCS, os.path.dirname(page), m.group(2)))}){{width=16.5cm}}",
                   t)
        # Liens internes → simple texte (le document Word n'a pas de navigation par fichier)
        t = re.sub(r"(?<!!)\[([^\]]+)\]\((?!https?:)[^)\s]+\)", r"\1", t)
        t = re.sub(r"\+\+([a-z0-9+-]+)\+\+", keys, t)
        t = re.sub(r"^(\s*)- \[ \] ", r"\1- ☐ ", t, flags=re.M)
        t = re.sub(r"<(https?://[^>]+)>", r"\1", t)
        morceaux[k] = t
    return "".join(morceaux)


def page_md(chemin):
    p = os.path.normpath(os.path.join(DOCS, chemin))
    txt = open(p, encoding="utf-8").read()
    txt = convertir(txt, chemin)
    # Décaler les titres d'un niveau (le titre de page devient niveau 2)
    blocs = re.split(r"(```.*?```)", txt, flags=re.S)
    for k in range(0, len(blocs), 2):
        blocs[k] = re.sub(r"^(#{1,5}) ", lambda m: "#" + m.group(1) + " ", blocs[k], flags=re.M)
    txt = "".join(blocs)
    if chemin.startswith("guide/administration/") and not chemin.endswith("index.md"):
        txt = re.sub(r"^## ", "## Administration — ", txt, count=1, flags=re.M)
    return txt


SAUT = '\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'

doc = ["---\ntitle: \"SmartCampus\"\nsubtitle: \"Documentation complète : guide d'utilisation, installation et développement\"\nauthor: \"Plateforme SmartCampus\"\ndate: \"Version d'octobre 2026\"\ntoc-title: \"Sommaire\"\nlang: fr-FR\n---\n"]
intro = open(os.path.join(DOCS, "index.md"), encoding="utf-8").read()
intro = re.sub(r'!!! info "Version Word".*?\n\n', "", intro, flags=re.S)
intro = convertir(intro, "index.md")
intro = re.sub(r"^# SmartCampus\s*\n", "# Présentation de SmartCampus\n", intro)
intro = re.sub(r"^## ", "### ", intro, flags=re.M)
doc.append(intro)
for titre, pages in PARTIES:
    pass
    doc.append(f"# {titre}\n")
    for p in pages:
        doc.append(page_md(p))
        doc.append("\n")
open(os.path.join(OUT, "documentation.md"), "w", encoding="utf-8").write("\n".join(doc))
print("diagrammes:", mermaid_n[0])
