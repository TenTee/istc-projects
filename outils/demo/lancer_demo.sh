#!/usr/bin/env bash
# Lance SmartCampus en mode DÉMONSTRATION (données fictives) sur ce poste.
#   Interface : http://localhost:3001 (l'API Django, sur le port 8001, est relayée par l'interface)
# Comptes (mot de passe Demo2026!) : admin.demo, formateur.demo, etudiant.demo
# La base de démo est créée au premier lancement ; « --reset » la recrée.
# Votre base habituelle et votre dossier media/ ne sont pas touchés.
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
DEMO="$RACINE/outils/demo"

export DATABASE_URL="sqlite:///$DEMO/demo.sqlite3"
export MEDIA_ROOT="$DEMO/media"
export DEBUG=True DB_SSL_REQUIRE=False RECAPTCHA_SECRET_KEY=
export ALLOWED_HOSTS="localhost,127.0.0.1"
export USE_X_FORWARDED_HOST=True
export CORS_ALLOWED_ORIGINS="http://localhost:3001,http://127.0.0.1:3001"

cd "$RACINE/back-istc"
PY=python3
[ -x venv/bin/python ] && PY=venv/bin/python
if [ ! -f "$DEMO/demo.sqlite3" ] || [ "${1:-}" = "--reset" ]; then
  rm -f "$DEMO/demo.sqlite3"
  echo "Création de la base de démonstration…"
  "$PY" manage.py migrate --noinput -v0
  "$PY" manage.py seed_demo
fi

"$PY" manage.py runserver 127.0.0.1:8001 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

cd "$RACINE/frontend"
echo "Interface de démonstration : http://localhost:3001  (Ctrl+C pour arrêter)"
NEXT_PUBLIC_API_BASE_URL=http://localhost:3001 \
DEMO_API_PROXY=http://127.0.0.1:8001 \
NEXT_PUBLIC_RECAPTCHA_SITE_KEY= \
DEMO_CAPTURE_DIR="$RACINE/docs/images/captures" \
  npx next dev -p 3001
