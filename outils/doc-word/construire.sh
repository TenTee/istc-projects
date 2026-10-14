#!/usr/bin/env bash
# Génère docs/SmartCampus_ISTC_Documentation_complete.docx à partir des pages Markdown de docs/.
# Prérequis : python3, pandoc (>= 3), mermaid-cli (mmdc), LibreOffice (pour le sommaire).
set -euo pipefail
cd "$(dirname "$0")"
python3 assemble.py
pandoc build/documentation.md -f markdown+pipe_tables+definition_lists+fenced_divs+raw_attribute \
  -o build/brut.docx --reference-doc=reference.docx --toc --toc-depth=2 --resource-path=build
python3 postprocess.py build/brut.docx build/etape2.docx
python3 maj_sommaire.py build/etape2.docx ../../docs/SmartCampus_ISTC_Documentation_complete.docx
echo "OK : docs/SmartCampus_ISTC_Documentation_complete.docx"
