# Export Word de la documentation

`./construire.sh` assemble toutes les pages de `docs/` (dans l'ordre du menu de `mkdocs.yml`) en un seul fichier Word :
`docs/SmartCampus_Documentation_complete.docx` (page de titre, sommaire, diagrammes, encadrés, pied de page numéroté).

Relancez-le après chaque modification de la documentation. Si une page est ajoutée, ajoutez-la aussi à la liste `PARTIES` de `assemble.py`.

Prérequis : `python3`, `pandoc` ≥ 3, `mmdc` (`npm install -g @mermaid-js/mermaid-cli`), LibreOffice (`soffice` et le module Python `uno`).
Le style (polices, couleurs, tableaux, encadrés) est défini dans `reference.docx`.
