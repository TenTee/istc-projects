#!/usr/bin/env bash
# =============================================================================
#  SmartCampus — livraison automatique du backend (API Django) sur un serveur
# =============================================================================
#
#  Première installation sur un serveur neuf (Ubuntu 22.04 / 24.04 ou Bitnami) :
#
#      git clone <adresse-du-dépôt> /opt/smartcampus      # ou /home/bitnami/istc-projects
#      cd /opt/smartcampus
#      sudo bash outils/deploiement/deployer_backend.sh
#
#  Le script pose quelques questions (domaine, base distante, adresse du frontend).
#  Il mémorise les réponses dans /etc/smartcampus/deploiement.conf.
#
#  Livraisons suivantes : relancez exactement la même commande. Le script :
#    - récupère le code (git pull) ;
#    - met à jour les dépendances ;
#    - applique les migrations ;
#    - redémarre l'API.
#  Il ne pose plus de questions et ne touche ni aux secrets ni aux données.
#
#  Base de données :
#    - sans --bd, PostgreSQL est installé SUR CE SERVEUR, avec une base et un
#      mot de passe générés automatiquement ;
#    - avec --bd postgresql://utilisateur:motdepasse@hote:5432/base, la base
#      distante est utilisée : la connexion est testée avant toute modification.
#
#  Options principales (toutes facultatives) :
#    --domaine api.ecole.cm       nom de domaine de l'API. Avec un domaine, le
#                                 certificat HTTPS Let's Encrypt est automatique.
#                                 Sans domaine, l'API répond en HTTP sur l'adresse IP.
#    --email admin@ecole.cm       e-mail pour Let's Encrypt (alertes d'expiration).
#    --bd <DATABASE_URL>          base PostgreSQL distante (sinon, base locale).
#    --bd-ssl                     la base distante exige SSL.
#    --frontend https://ecole.cm  adresse(s) de l'interface autorisées (CORS),
#                                 séparées par des virgules.
#    --branche main               branche Git à livrer (défaut : main).
#    --utilisateur smartcampus    compte système qui exécute l'API.
#    --port 8000                  port local de Gunicorn.
#    --superutilisateur admin:admin@ecole.cm
#                                 crée ce compte administrateur s'il n'existe pas.
#                                 Mot de passe : variable SMARTCAMPUS_ADMIN_PASSWORD,
#                                 sinon il est demandé.
#    --sans-https                 ne pas demander de certificat.
#    --sans-pull                  livrer le code tel qu'il est dans le dossier.
#    --oui                        aucune question (valeurs des options / du fichier de config).
#    --aide                       affiche cette aide.
#
#  Journal de chaque livraison : /var/log/smartcampus/deploiement-AAAAMMJJ-HHMMSS.log
# =============================================================================
set -Eeuo pipefail

# ----------------------------------------------------------------------------- valeurs par défaut
CONF_DIR="/etc/smartcampus"
CONF_FILE="$CONF_DIR/deploiement.conf"
LOG_DIR="/var/log/smartcampus"
SERVICE="smartcampus-api"

DOMAINE=""
EMAIL=""
BD_URL=""
BD_SSL="False"
FRONTEND=""
BRANCHE="main"
UTILISATEUR=""
PORT="8000"
SUPERUTILISATEUR=""
AVEC_HTTPS="oui"
AVEC_PULL="oui"
INTERACTIF="oui"

# ----------------------------------------------------------------------------- affichage
if [[ -t 1 ]]; then B=$'\e[1m'; V=$'\e[32m'; J=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B=""; V=""; J=""; R=""; N=""; fi
etape()  { printf '\n%s==> %s%s\n' "$B" "$*" "$N"; }
info()   { printf '    %s\n' "$*"; }
ok()     { printf '    %s✔ %s%s\n' "$V" "$*" "$N"; }
alerte() { printf '    %s⚠ %s%s\n' "$J" "$*" "$N"; }
erreur() { printf '\n%s✘ %s%s\n' "$R" "$*" "$N" >&2; exit 1; }
trap 'printf "\n%s✘ Échec à la ligne %s : %s%s\n" "$R" "$LINENO" "$BASH_COMMAND" "$N" >&2' ERR

aide() { awk 'NR > 1 && /^set -E/ { exit } NR > 1' "$0" | sed -e 's/^# \{0,1\}//' -e '/^=====/d'; exit 0; }

# ----------------------------------------------------------------------------- outils (testables)

# Génère une chaîne aléatoire sans caractère spécial (sûre dans une URL et dans .env).
# (lecture par blocs finis : pas de « tr | head » qui échouerait en SIGPIPE avec pipefail)
aleatoire() {
  local n="${1:-32}" s=""
  while (( ${#s} < n )); do s+="$(head -c 512 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9')"; done
  printf '%s' "${s:0:n}"
}

# Lit la valeur d'une clé dans un fichier .env (vide si absente).
lire_env() {
  local fichier="$1" cle="$2"
  [[ -f "$fichier" ]] || return 0
  { grep -E "^${cle}=" "$fichier" || true; } | tail -n1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'
}

# Écrit (ou remplace) une clé dans un fichier .env sans toucher aux autres lignes.
ecrire_env() {
  local fichier="$1" cle="$2" valeur="$3" tmp
  touch "$fichier"
  tmp="$(mktemp)"
  if grep -qE "^${cle}=" "$fichier"; then
    awk -v c="$cle" -v v="$valeur" 'BEGIN{FS=OFS="="} $1==c && !fait {print c "=" v; fait=1; next} {print}' "$fichier" >"$tmp"
  else
    cat "$fichier" >"$tmp"
    [[ -s "$tmp" && "$(tail -c1 "$tmp")" != "" ]] && echo >>"$tmp"
    printf '%s=%s\n' "$cle" "$valeur" >>"$tmp"
  fi
  cat "$tmp" >"$fichier"
  rm -f "$tmp"
}

# Écrit la clé seulement si elle est absente ou vide (n'écrase jamais un réglage existant).
completer_env() {
  local fichier="$1" cle="$2" valeur="$3"
  [[ -n "$(lire_env "$fichier" "$cle")" ]] || ecrire_env "$fichier" "$cle" "$valeur"
}

# Ajoute des éléments à une liste séparée par des virgules, sans doublon.
fusionner_liste() {
  local IFS=',' resultat=() vu=" " e tout="$1,$2"
  for e in $tout; do
    e="$(echo "$e" | xargs)"
    [[ -z "$e" || "$vu" == *" $e "* ]] && continue
    resultat+=("$e"); vu+="$e "
  done
  (IFS=','; echo "${resultat[*]}")
}

# Hôte d'une URL PostgreSQL (postgresql://u:p@hote:port/base → hote).
hote_bd() { echo "$1" | sed -E 's#^[a-z]+://([^@/]*@)?\[?([^]:/?]+)\]?.*#\2#'; }

est_locale() { case "$(hote_bd "$1")" in 127.0.0.1|localhost|::1) return 0 ;; *) return 1 ;; esac; }

# ----------------------------------------------------------------------------- lecture des options
lire_options() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --domaine) DOMAINE="$2"; shift ;;
      --email) EMAIL="$2"; shift ;;
      --bd) BD_URL="$2"; shift ;;
      --bd-ssl) BD_SSL="True" ;;
      --frontend) FRONTEND="$2"; shift ;;
      --branche) BRANCHE="$2"; shift ;;
      --utilisateur) UTILISATEUR="$2"; shift ;;
      --port) PORT="$2"; shift ;;
      --superutilisateur) SUPERUTILISATEUR="$2"; shift ;;
      --sans-https) AVEC_HTTPS="non" ;;
      --sans-pull) AVEC_PULL="non" ;;
      --oui|-y) INTERACTIF="non" ;;
      --aide|-h|--help) aide ;;
      *) erreur "Option inconnue : $1 (voir --aide)" ;;
    esac
    shift
  done
  [[ -t 0 ]] || INTERACTIF="non"
}

demander() {  # demander VARIABLE "Question" "défaut"
  local var="$1" question="$2" defaut="${3:-}" reponse
  [[ "$INTERACTIF" == "oui" ]] || return 0
  read -r -p "    $question${defaut:+ [$defaut]} : " reponse || true
  printf -v "$var" '%s' "${reponse:-$defaut}"
}

# ----------------------------------------------------------------------------- étapes
verifier_systeme() {
  etape "Vérification du serveur"
  [[ $EUID -eq 0 ]] || erreur "Lancez le script avec sudo : sudo bash $0"
  [[ -f /etc/os-release ]] || erreur "Système non reconnu (fichier /etc/os-release absent)."
  # shellcheck disable=SC1091
  . /etc/os-release
  BITNAMI="non"; [[ -d /opt/bitnami ]] && BITNAMI="oui"
  case "${ID:-}" in
    ubuntu|debian)
      local mention=""; [[ "$BITNAMI" == "oui" ]] && mention=" (image Bitnami)"
      ok "Système : ${PRETTY_NAME:-$ID}$mention" ;;
    *) erreur "Système non pris en charge : ${PRETTY_NAME:-inconnu}. Ubuntu 22.04/24.04 ou Bitnami (Debian) attendu." ;;
  esac
  command -v systemctl >/dev/null && [[ -d /run/systemd/system ]] && SYSTEMD="oui" || SYSTEMD="non"
  [[ "$SYSTEMD" == "oui" ]] || alerte "systemd absent : le service ne sera pas installé (environnement de test ?)."
  IP_PRIVEE="$(hostname -I 2>/dev/null | awk '{print $1}')"
  IP_PUBLIQUE="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  [[ "$IP_PUBLIQUE" =~ ^[0-9a-fA-F.:]+$ ]] || IP_PUBLIQUE="$IP_PRIVEE"
  DEPOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  BACKEND="$DEPOT/back-istc"
  VENV="$BACKEND/.venv"
  [[ -f "$BACKEND/manage.py" ]] || erreur "back-istc/manage.py introuvable : lancez le script depuis le dépôt cloné."
  ok "Dépôt : $DEPOT"
}

charger_configuration() {
  etape "Configuration de la livraison"
  if [[ -f "$CONF_FILE" ]]; then
    # Les options de la ligne de commande l'emportent sur les valeurs mémorisées.
    local d="$DOMAINE" e="$EMAIL" b="$BD_URL" f="$FRONTEND" u="$UTILISATEUR" p="$PORT" br="$BRANCHE"
    # shellcheck disable=SC1090
    . "$CONF_FILE"
    DOMAINE="${d:-$DOMAINE}"; EMAIL="${e:-$EMAIL}"; BD_URL="${b:-$BD_URL}"; FRONTEND="${f:-$FRONTEND}"
    UTILISATEUR="${u:-$UTILISATEUR}"; [[ "$p" != "8000" ]] && PORT="$p"; [[ "$br" != "main" ]] && BRANCHE="$br"
    PREMIERE="non"
    ok "Mise à jour d'une installation existante (réglages : $CONF_FILE)"
  else
    PREMIERE="oui"
    info "Première installation sur ce serveur. Laissez vide pour la valeur proposée."
    [[ -n "$DOMAINE" ]] || demander DOMAINE "Nom de domaine de l'API (vide = accès par l'adresse IP ${IP_PUBLIQUE:-du serveur})" ""
    if [[ -n "$DOMAINE" && "$AVEC_HTTPS" == "oui" && -z "$EMAIL" ]]; then
      demander EMAIL "E-mail pour le certificat HTTPS (Let's Encrypt)" ""
    fi
    [[ -n "$BD_URL" ]] || demander BD_URL "Adresse d'une base PostgreSQL distante (vide = base installée sur ce serveur)" ""
    [[ -n "$FRONTEND" ]] || demander FRONTEND "Adresse(s) de l'interface web, ex. https://ecole.cm (vide = à régler plus tard)" ""
  fi
  if [[ -z "$UTILISATEUR" ]]; then
    local proprietaire; proprietaire="$(stat -c %U "$DEPOT")"
    if [[ "$proprietaire" != "root" ]]; then UTILISATEUR="$proprietaire"; else UTILISATEUR="smartcampus"; fi
  fi
  # Serveur déjà configuré à la main avec une base distante : on la reprend plutôt que d'en créer une locale.
  if [[ -z "$BD_URL" ]]; then
    local url_env; url_env="$(lire_env "$BACKEND/.env" DATABASE_URL)"
    if [[ "$url_env" == postgres* ]] && ! est_locale "$url_env"; then BD_URL="$url_env"; fi
  fi
  if [[ -n "$BD_URL" ]] && ! est_locale "$BD_URL"; then MODE_BD="distante"; else MODE_BD="locale"; fi
  [[ "$BD_URL" == *sslmode=require* ]] && BD_SSL="True"
  info "Domaine        : ${DOMAINE:-aucun (adresse IP ${IP_PUBLIQUE:-?})}"
  info "Base           : $MODE_BD"
  info "Interface web  : ${FRONTEND:-non renseignée}"
  info "Compte système : $UTILISATEUR · branche $BRANCHE · port $PORT"
}

installer_paquets() {
  etape "Installation des paquets système"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  local paquets=(git curl ca-certificates build-essential libpq-dev postgresql-client cron)
  [[ "$MODE_BD" == "locale" ]] && paquets+=(postgresql)
  if [[ "$BITNAMI" == "non" ]]; then
    paquets+=(nginx)
    [[ -n "$DOMAINE" && "$AVEC_HTTPS" == "oui" ]] && paquets+=(certbot python3-certbot-nginx)
  fi
  # Python 3.11 au minimum (Django 5.2 + code SmartCampus)
  PYTHON="python3"
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PYTHON="python3.11"
    paquets+=(python3.11 python3.11-venv python3.11-dev)
  else
    local v; v="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
    paquets+=(python3 python3-venv python3-dev "python${v}-venv")
  fi
  apt-get install -y -qq "${paquets[@]}" >/dev/null || erreur "Installation des paquets impossible : ${paquets[*]}"
  command -v "$PYTHON" >/dev/null || erreur "$PYTHON introuvable après installation."
  ok "Paquets installés ($($PYTHON --version))"
}

preparer_utilisateur() {
  etape "Compte système et droits"
  if ! id "$UTILISATEUR" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "/home/$UTILISATEUR" --shell /bin/bash "$UTILISATEUR"
    ok "Compte « $UTILISATEUR » créé"
  fi
  chown -R "$UTILISATEUR":"$UTILISATEUR" "$DEPOT"
  # Git refuse un dépôt appartenant à un autre compte : on l'autorise explicitement.
  git config --system --get-all safe.directory 2>/dev/null | grep -qx "$DEPOT" || git config --system --add safe.directory "$DEPOT"
  mkdir -p "$BACKEND/media" "$BACKEND/staticfiles" "$BACKEND/backups/postgres" "$LOG_DIR"
  chown -R "$UTILISATEUR":"$UTILISATEUR" "$BACKEND/media" "$BACKEND/staticfiles" "$BACKEND/backups"
  ok "Le code appartient à « $UTILISATEUR »"
}

# Fichiers suivis par Git mais produits ou propres à chaque machine : Python les régénère (__pycache__),
# le script écrit le .env du serveur. On les remet à l'état du dépôt avant la mise à jour.
est_fichier_genere() {
  case "$1" in
    back-istc/.env|*__pycache__/*|*.pyc|back-istc/venv/*|*/db.sqlite3|back-istc/staticfiles/*) return 0 ;;
    *) return 1 ;;
  esac
}

sauver_env_serveur() {
  [[ -f "$BACKEND/.env" ]] || return 0
  mkdir -p "$CONF_DIR"
  cp -p "$BACKEND/.env" "$CONF_DIR/backend.env"
  chmod 600 "$CONF_DIR/backend.env"
}

# Remet le .env du serveur en place (même si le dépôt l'a modifié ou supprimé).
restaurer_env_serveur() {
  [[ -f "$CONF_DIR/backend.env" ]] || return 0
  cp -p "$CONF_DIR/backend.env" "$BACKEND/.env"
  chown "$UTILISATEUR":"$UTILISATEUR" "$BACKEND/.env"
  chmod 600 "$BACKEND/.env"
}

git_depot() { sudo -u "$UTILISATEUR" git -C "$DEPOT" "$@"; }

recuperer_code() {
  etape "Récupération du code"
  if [[ "$AVEC_PULL" == "non" ]]; then info "--sans-pull : code livré tel quel."; return; fi
  if [[ ! -d "$DEPOT/.git" ]]; then alerte "Pas un dépôt Git : code livré tel quel."; return; fi
  local avant apres f generes=() autres=()
  avant="$(git_depot rev-parse --short HEAD)"

  # 1. Le .env du serveur est mis de côté : il ne doit jamais être remplacé par celui du dépôt.
  sauver_env_serveur

  # 2. Fichiers modifiés sur le serveur : les fichiers générés sont remis à l'état du dépôt,
  #    une vraie modification de code arrête la livraison.
  while IFS= read -r f; do
    if est_fichier_genere "$f"; then generes+=("$f"); else autres+=("$f"); fi
  done < <(git_depot ls-files -m)
  if (( ${#autres[@]} )); then
    alerte "Fichiers de code modifiés directement sur le serveur :"
    printf '        %s\n' "${autres[@]:0:15}"
    (( ${#autres[@]} > 15 )) && info "    … et $(( ${#autres[@]} - 15 )) autre(s)"
    erreur "Livraison arrêtée pour ne pas perdre ces modifications. Pour les abandonner : sudo git -C $DEPOT checkout -- . puis relancez."
  fi
  if (( ${#generes[@]} )); then
    printf '%s\0' "${generes[@]}" | sudo -u "$UTILISATEUR" xargs -0 git -C "$DEPOT" checkout --
    info "${#generes[@]} fichier(s) généré(s) suivi(s) par Git remis à l'état du dépôt (.env du serveur conservé)."
  fi

  # 3. Mise à jour.
  if ! git_depot fetch --tags origin "$BRANCHE"; then
    restaurer_env_serveur
    erreur "git fetch impossible. Dépôt privé ? Ajoutez une clé de déploiement au compte $UTILISATEUR (voir la documentation)."
  fi
  git_depot checkout -q "$BRANCHE"
  if ! git_depot merge --ff-only -q "origin/$BRANCHE"; then
    restaurer_env_serveur
    erreur "Mise à jour impossible (historique divergent ?). Voir : sudo git -C $DEPOT status"
  fi
  restaurer_env_serveur

  apres="$(git_depot rev-parse --short HEAD)"
  if [[ "$avant" == "$apres" ]]; then ok "Code déjà à jour ($apres)"; return; fi
  ok "Code mis à jour : $avant → $apres"
  # Le script de livraison lui-même a changé : on relance la nouvelle version.
  if [[ "$(sha256sum "$SCRIPT" | cut -d' ' -f1)" != "$EMPREINTE_SCRIPT" ]]; then
    info "Nouvelle version du script de livraison : relance."
    exec bash "$SCRIPT" "${ARGUMENTS[@]}" --sans-pull
  fi
}

preparer_base() {
  etape "Base de données ($MODE_BD)"
  local fichier_env="$BACKEND/.env" url_existante
  url_existante="$(lire_env "$fichier_env" DATABASE_URL)"
  if [[ "$MODE_BD" == "distante" ]]; then
    PGCONNECT_TIMEOUT=10 psql "$BD_URL" -Atqc 'select 1' >/dev/null 2>&1 \
      || erreur "Connexion impossible à la base distante ($(hote_bd "$BD_URL")). Vérifiez l'adresse, le mot de passe et le pare-feu de la base."
    DATABASE_URL_FINALE="$BD_URL"
    ok "Connexion à la base distante réussie ($(hote_bd "$BD_URL"))"
    return
  fi
  if [[ "$SYSTEMD" == "oui" ]]; then systemctl enable --now postgresql >/dev/null 2>&1 || true
  else service postgresql start >/dev/null 2>&1 || true; fi
  local essai; for essai in 1 2 3 4 5 6 7 8 9 10; do
    sudo -u postgres psql -Atqc 'select 1' >/dev/null 2>&1 && break; sleep 2
  done
  sudo -u postgres psql -Atqc 'select 1' >/dev/null 2>&1 || erreur "PostgreSQL local ne démarre pas (voir : journalctl -u postgresql)."
  # Adresse locale donnée avec --bd : on l'utilise telle quelle si elle répond.
  if [[ -n "$BD_URL" ]] && psql "$BD_URL" -Atqc 'select 1' >/dev/null 2>&1; then
    DATABASE_URL_FINALE="$BD_URL"
    ok "Base locale indiquée avec --bd utilisée"
    return
  fi
  # Base déjà configurée et joignable : on n'y touche pas.
  if [[ -n "$url_existante" ]] && est_locale "$url_existante" && psql "$url_existante" -Atqc 'select 1' >/dev/null 2>&1; then
    DATABASE_URL_FINALE="$url_existante"
    ok "Base locale existante conservée"
    return
  fi
  local mdp; mdp="$(aleatoire 32)"
  if [[ "$(sudo -u postgres psql -Atqc "select 1 from pg_roles where rolname='smartcampus'")" == "1" ]]; then
    sudo -u postgres psql -qc "ALTER ROLE smartcampus WITH LOGIN PASSWORD '$mdp'" >/dev/null
  else
    sudo -u postgres psql -qc "CREATE ROLE smartcampus WITH LOGIN PASSWORD '$mdp'" >/dev/null
  fi
  if [[ "$(sudo -u postgres psql -Atqc "select 1 from pg_database where datname='smartcampus'")" != "1" ]]; then
    sudo -u postgres createdb -O smartcampus -E UTF8 smartcampus
    ok "Base « smartcampus » créée"
  fi
  DATABASE_URL_FINALE="postgresql://smartcampus:${mdp}@127.0.0.1:5432/smartcampus"
  psql "$DATABASE_URL_FINALE" -Atqc 'select 1' >/dev/null || erreur "Connexion à la base locale impossible."
  ok "Base locale prête (mot de passe généré, enregistré dans back-istc/.env)"
}

configurer_env() {
  etape "Fichier de configuration back-istc/.env"
  local f="$BACKEND/.env" hotes origines
  # Première installation avec un .env venu du dépôt Git (celui d'un autre poste) : on repart du modèle,
  # pour ne reprendre ni sa clé secrète ni ses réglages.
  if [[ "$PREMIERE" == "oui" && -f "$f" && -d "$DEPOT/.git" ]] \
     && git -C "$DEPOT" ls-files --error-unmatch back-istc/.env >/dev/null 2>&1 \
     && git -C "$DEPOT" diff --quiet -- back-istc/.env; then
    alerte "back-istc/.env vient du dépôt Git : nouveau .env créé pour ce serveur."
    rm -f "$f"
  fi
  if [[ ! -f "$f" ]]; then
    cp "$BACKEND/.env.example" "$f"
    ecrire_env "$f" SECRET_KEY "$(aleatoire 64)"
    ecrire_env "$f" ALLOWED_HOSTS ""          # les domaines d'exemple du modèle ne sont pas repris
    ecrire_env "$f" CELERY_BROKER_URL ""
    ecrire_env "$f" CELERY_RESULT_BACKEND ""
    ok ".env créé (clé secrète générée)"
  fi
  [[ "$(lire_env "$f" SECRET_KEY)" == "change-me" ]] && ecrire_env "$f" SECRET_KEY "$(aleatoire 64)"
  ecrire_env "$f" DEBUG False
  ecrire_env "$f" DATABASE_URL "$DATABASE_URL_FINALE"
  [[ "$MODE_BD" == "distante" ]] && ecrire_env "$f" DB_SSL_REQUIRE "$BD_SSL"
  hotes="$(fusionner_liste "$(lire_env "$f" ALLOWED_HOSTS)" "localhost,127.0.0.1,${IP_PRIVEE},${IP_PUBLIQUE},${DOMAINE}")"
  ecrire_env "$f" ALLOWED_HOSTS "$hotes"
  if [[ -n "$FRONTEND" ]]; then
    origines="$(fusionner_liste "$(lire_env "$f" CORS_ALLOWED_ORIGINS)" "$(echo "$FRONTEND" | sed 's#/*$##; s#/,#,#g')")"
    ecrire_env "$f" CORS_ALLOWED_ORIGINS "$origines"
  fi
  completer_env "$f" CONTROLE_DROITS_PERSONNEL True
  chown "$UTILISATEUR":"$UTILISATEUR" "$f"; chmod 600 "$f"
  sauver_env_serveur      # copie de référence : /etc/smartcampus/backend.env
  ok "ALLOWED_HOSTS = $hotes"
  [[ -n "$(lire_env "$f" CORS_ALLOWED_ORIGINS)" ]] || alerte "CORS_ALLOWED_ORIGINS vide : renseignez l'adresse de l'interface (option --frontend)."
}

installer_python() {
  etape "Environnement Python et dépendances"
  # Le dossier back-istc/venv/ peut avoir été envoyé dans Git depuis un autre poste (liens cassés ici) :
  # le serveur utilise son propre environnement back-istc/.venv, ignoré par Git.
  if [[ -e "$VENV" ]] && ! "$VENV/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    alerte "Environnement Python absent, cassé ou < 3.11 : recréation."
    rm -rf "$VENV"
  fi
  if [[ ! -e "$VENV" ]]; then
    sudo -u "$UTILISATEUR" "$PYTHON" -m venv "$VENV" || erreur "Création de l'environnement Python impossible ($PYTHON -m venv)."
  fi
  sudo -u "$UTILISATEUR" "$VENV/bin/python" -m pip install -q --upgrade pip wheel
  sudo -u "$UTILISATEUR" "$VENV/bin/python" -m pip install -q -r "$BACKEND/requirements.txt" gunicorn
  ok "Dépendances installées dans back-istc/.venv ($("$VENV/bin/python" --version))"
  if [[ -d "$DEPOT/.git" ]] && git -C "$DEPOT" ls-files --error-unmatch back-istc/venv/bin/activate >/dev/null 2>&1; then
    alerte "Le dossier back-istc/venv/ est suivi par Git : retirez-le du dépôt (git rm -r --cached back-istc/venv)."
  fi
}

django() { (cd "$BACKEND" && sudo -u "$UTILISATEUR" env PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" manage.py "$@"); }

sauvegarde_avant_migration() {
  [[ "$PREMIERE" == "oui" ]] && return
  etape "Sauvegarde de sécurité avant migration"
  if sudo -u "$UTILISATEUR" bash "$BACKEND/scripts/backup_cron.sh" >/dev/null 2>&1; then
    ok "Sauvegarde créée dans back-istc/backups/postgres/"
  else
    alerte "Sauvegarde impossible (voir bash back-istc/scripts/backup_cron.sh) : la livraison continue."
  fi
}

mettre_a_jour_django() {
  etape "Mise à jour de l'application"
  django check >/dev/null
  django migrate --noinput
  django collectstatic --noinput >/dev/null
  ok "Migrations appliquées, fichiers statiques collectés"
  if [[ -n "$SUPERUTILISATEUR" ]]; then
    local nom="${SUPERUTILISATEUR%%:*}" mail="${SUPERUTILISATEUR#*:}"
    [[ "$mail" == "$SUPERUTILISATEUR" ]] && mail=""
    if django shell -c "from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.filter(username='$nom').exists() else 1)" 2>/dev/null; then
      info "Compte administrateur « $nom » déjà présent."
    else
      local mdp="${SMARTCAMPUS_ADMIN_PASSWORD:-}"
      if [[ -z "$mdp" && "$INTERACTIF" == "oui" ]]; then read -r -s -p "    Mot de passe du compte « $nom » : " mdp; echo; fi
      [[ -n "$mdp" ]] || erreur "Mot de passe administrateur manquant (variable SMARTCAMPUS_ADMIN_PASSWORD)."
      (cd "$BACKEND" && sudo -u "$UTILISATEUR" env PYTHONDONTWRITEBYTECODE=1 DJANGO_SUPERUSER_USERNAME="$nom" DJANGO_SUPERUSER_EMAIL="$mail" \
        DJANGO_SUPERUSER_PASSWORD="$mdp" "$VENV/bin/python" manage.py createsuperuser --noinput >/dev/null)
      ok "Compte administrateur « $nom » créé"
    fi
  elif [[ "$PREMIERE" == "oui" ]]; then
    if ! django shell -c "from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
      if [[ "$INTERACTIF" == "oui" ]]; then
        info "Création du premier compte administrateur :"
        django createsuperuser
      else
        alerte "Aucun administrateur : créez-en un avec « cd $BACKEND && sudo -u $UTILISATEUR .venv/bin/python manage.py createsuperuser »."
      fi
    fi
  fi
}

installer_service() {
  etape "Service de l'API ($SERVICE)"
  [[ "$SYSTEMD" == "oui" ]] || { alerte "systemd absent : service non installé."; return; }
  local workers; workers=$(( $(nproc) * 2 + 1 )); (( workers > 9 )) && workers=9
  cat >"/etc/systemd/system/$SERVICE.service" <<EOF
# Généré par outils/deploiement/deployer_backend.sh — relancez le script plutôt que de modifier ce fichier.
[Unit]
Description=SmartCampus API (Django / Gunicorn)
After=network.target postgresql.service

[Service]
User=$UTILISATEUR
Group=$UTILISATEUR
WorkingDirectory=$BACKEND
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=$VENV/bin/gunicorn smart_back.wsgi:application --bind 127.0.0.1:$PORT --workers $workers --timeout 120 --access-logfile - --error-logfile -
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable "$SERVICE" >/dev/null 2>&1
  systemctl restart "$SERVICE"
  local essai; for essai in $(seq 1 15); do
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/admin/login/" && break; sleep 1
  done
  curl -fsS -o /dev/null "http://127.0.0.1:$PORT/admin/login/" \
    || erreur "L'API ne répond pas. Journal : journalctl -u $SERVICE -n 50 --no-pager"
  ok "API démarrée ($workers processus Gunicorn sur 127.0.0.1:$PORT)"
}

configurer_nginx() {
  etape "Serveur web Nginx"
  local site="/etc/nginx/sites-available/$SERVICE" nom="${DOMAINE:-_}"
  cat >"$site" <<EOF
# Généré par outils/deploiement/deployer_backend.sh
server {
    listen 80;
    listen [::]:80;
    server_name $nom;

    client_max_body_size 25M;

    location /static/ { alias $BACKEND/staticfiles/; expires 7d; }
    location /media/  { alias $BACKEND/media/; }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
  ln -sf "$site" "/etc/nginx/sites-enabled/$SERVICE"
  # Sans domaine, l'API devient le site par défaut de l'adresse IP.
  [[ -z "$DOMAINE" ]] && rm -f /etc/nginx/sites-enabled/default
  # Nginx (compte www-data) doit pouvoir lire les fichiers statiques et les médias.
  local d="$BACKEND"; while [[ "$d" != "/" ]]; do chmod o+x "$d" 2>/dev/null || true; d="$(dirname "$d")"; done
  chmod -R o+rX "$BACKEND/staticfiles" "$BACKEND/media"
  if ! nginx -t >/dev/null 2>&1; then nginx -t || true; erreur "Configuration Nginx invalide."; fi
  if [[ "$SYSTEMD" == "oui" ]]; then systemctl enable --now nginx >/dev/null 2>&1; systemctl reload nginx; fi
  local cible="$DOMAINE"; [[ -n "$cible" ]] || cible="l'adresse IP"
  ok "Nginx relaie $cible vers l'API"
  if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow 'Nginx Full' >/dev/null; ok "Pare-feu : ports 80 et 443 ouverts"
  fi
  if [[ -n "$DOMAINE" && "$AVEC_HTTPS" == "oui" ]]; then
    local opts=(--nginx -d "$DOMAINE" --non-interactive --agree-tos --redirect)
    if [[ -n "$EMAIL" ]]; then opts+=(-m "$EMAIL"); else opts+=(--register-unsafely-without-email); fi
    if certbot "${opts[@]}" >/dev/null 2>&1; then
      ok "HTTPS actif : https://$DOMAINE (renouvellement automatique)"
    else
      alerte "Certificat HTTPS non obtenu. Le domaine $DOMAINE pointe-t-il bien vers ${IP_PUBLIQUE:-ce serveur} ? Relancez le script une fois le DNS à jour."
    fi
  fi
}

configurer_apache_bitnami() {
  etape "Serveur web Apache (Bitnami)"
  local dossier="/opt/bitnami/apache/conf/vhosts" nom="${DOMAINE:-$IP_PUBLIQUE}"
  [[ -d "$dossier" ]] || { alerte "Dossier $dossier absent : configurez le serveur web à la main (voir la documentation)."; return; }
  cat >"$dossier/$SERVICE-vhost.conf" <<EOF
# Généré par outils/deploiement/deployer_backend.sh
<VirtualHost 127.0.0.1:80 _default_:80>
  ServerName $nom
  LimitRequestBody 26214400
  ProxyPreserveHost On
  Alias /static/ "$BACKEND/staticfiles/"
  Alias /media/ "$BACKEND/media/"
  <Directory "$BACKEND/staticfiles">
    Require all granted
  </Directory>
  <Directory "$BACKEND/media">
    Require all granted
  </Directory>
  ProxyPass /static/ !
  ProxyPass /media/ !
  ProxyPass / http://127.0.0.1:$PORT/ timeout=120
  ProxyPassReverse / http://127.0.0.1:$PORT/
</VirtualHost>
EOF
  local d="$BACKEND"; while [[ "$d" != "/" ]]; do chmod o+x "$d" 2>/dev/null || true; d="$(dirname "$d")"; done
  chmod -R o+rX "$BACKEND/staticfiles" "$BACKEND/media"
  /opt/bitnami/ctlscript.sh restart apache >/dev/null 2>&1 || alerte "Redémarrage d'Apache impossible : sudo /opt/bitnami/ctlscript.sh restart apache"
  ok "Apache relaie ${nom:-le serveur} vers l'API"
  if [[ -n "$DOMAINE" && "$AVEC_HTTPS" == "oui" ]]; then
    alerte "HTTPS sur Bitnami : lancez « sudo /opt/bitnami/bncert-tool » et indiquez $DOMAINE (outil interactif de Bitnami)."
  fi
}

planifier_sauvegardes() {
  etape "Sauvegardes automatiques"
  cat >/etc/cron.d/smartcampus-sauvegarde <<EOF
# Généré par outils/deploiement/deployer_backend.sh : sauvegarde de la base chaque nuit à 2 h (30 jours conservés)
0 2 * * * $UTILISATEUR /bin/bash $BACKEND/scripts/backup_cron.sh >> $LOG_DIR/sauvegarde.log 2>&1
EOF
  chmod 644 /etc/cron.d/smartcampus-sauvegarde
  touch "$LOG_DIR/sauvegarde.log"; chown "$UTILISATEUR":"$UTILISATEUR" "$LOG_DIR/sauvegarde.log"
  [[ "$SYSTEMD" == "oui" ]] && systemctl enable --now cron >/dev/null 2>&1 || true
  ok "Chaque nuit à 2 h → back-istc/backups/postgres/ (pensez à copier ce dossier hors du serveur)"
}

memoriser_configuration() {
  mkdir -p "$CONF_DIR"
  {
    echo "# Réglages de livraison SmartCampus (relus à chaque exécution de deployer_backend.sh)"
    printf 'DOMAINE=%q\nEMAIL=%q\nFRONTEND=%q\nBRANCHE=%q\nUTILISATEUR=%q\nPORT=%q\nAVEC_HTTPS=%q\n' \
      "$DOMAINE" "$EMAIL" "$FRONTEND" "$BRANCHE" "$UTILISATEUR" "$PORT" "$AVEC_HTTPS"
    [[ "$MODE_BD" == "distante" ]] && printf 'BD_URL=%q\nBD_SSL=%q\n' "$BD_URL" "$BD_SSL"
  } >"$CONF_FILE"
  chmod 600 "$CONF_FILE"
}

resume() {
  local version adresse
  version="$(cat "$DEPOT/VERSION" 2>/dev/null || echo "?")"
  if [[ -n "$DOMAINE" ]]; then
    if [[ "$AVEC_HTTPS" == "oui" ]]; then adresse="https://$DOMAINE"; else adresse="http://$DOMAINE"; fi
  else
    adresse="http://${IP_PUBLIQUE:-<adresse-du-serveur>}"
  fi
  etape "Livraison terminée — SmartCampus $version"
  info "API              : $adresse  (administration technique : $adresse/admin/)"
  info "Base de données  : $MODE_BD"
  info "Configuration    : $BACKEND/.env"
  info "Journaux de l'API: journalctl -u $SERVICE -f"
  info "Journal livraison: $JOURNAL"
  echo
  info "Côté interface (frontend), renseignez : NEXT_PUBLIC_API_BASE_URL=$adresse"
  info "Prochaine livraison : sudo bash $DEPOT/outils/deploiement/deployer_backend.sh"
}

main() {
  ARGUMENTS=("$@")
  SCRIPT="$(readlink -f "${BASH_SOURCE[0]}")"
  EMPREINTE_SCRIPT="$(sha256sum "$SCRIPT" | cut -d' ' -f1)"
  lire_options "$@"
  mkdir -p "$LOG_DIR" 2>/dev/null || true
  JOURNAL="$LOG_DIR/deploiement-$(date +%Y%m%d-%H%M%S).log"
  if [[ -w "$LOG_DIR" ]]; then exec > >(tee -a "$JOURNAL") 2>&1; fi
  verifier_systeme
  charger_configuration
  installer_paquets
  preparer_utilisateur
  recuperer_code
  preparer_base
  configurer_env
  installer_python
  sauvegarde_avant_migration
  mettre_a_jour_django
  installer_service
  if [[ "$BITNAMI" == "oui" ]]; then configurer_apache_bitnami; else configurer_nginx; fi
  planifier_sauvegardes
  memoriser_configuration
  django audit_droits >/dev/null 2>&1 && info "Droits du personnel vérifiés (python manage.py audit_droits pour le détail)." || true
  resume
}

# Permet de charger les fonctions sans lancer la livraison (tests).
# (« exit » sur la même ligne : bash ne relit pas ce fichier s'il a été modifié par git pull.)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; exit $?; fi
