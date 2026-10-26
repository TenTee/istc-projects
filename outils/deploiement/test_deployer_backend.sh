#!/usr/bin/env bash
# Tests des fonctions utilitaires du script de livraison : bash outils/deploiement/test_deployer_backend.sh
set -uo pipefail
ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$ICI/deployer_backend.sh"
set +e; trap - ERR

echecs=0
verifier() {  # verifier "description" attendu obtenu
  if [[ "$2" == "$3" ]]; then printf '  ok   %s\n' "$1"; else printf '  ÉCHEC %s\n       attendu : %q\n       obtenu  : %q\n' "$1" "$2" "$3"; echecs=$((echecs + 1)); fi
}

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
F="$T/.env"
printf 'SECRET_KEY=change-me\nDEBUG=True\n# commentaire\nALLOWED_HOSTS=a.cm,b.cm\nDATABASE_URL="postgresql://u:p@h:5432/b"\n' >"$F"

verifier "lire_env simple" "True" "$(lire_env "$F" DEBUG)"
verifier "lire_env enlève les guillemets" "postgresql://u:p@h:5432/b" "$(lire_env "$F" DATABASE_URL)"
verifier "lire_env clé absente" "" "$(lire_env "$F" ABSENTE)"
ecrire_env "$F" DEBUG False
verifier "ecrire_env remplace" "False" "$(lire_env "$F" DEBUG)"
verifier "ecrire_env garde les commentaires" "1" "$(grep -c '^# commentaire' "$F")"
ecrire_env "$F" NOUVELLE "x=y"
verifier "ecrire_env ajoute (valeur avec =)" "x=y" "$(lire_env "$F" NOUVELLE)"
verifier "une seule ligne DEBUG" "1" "$(grep -c '^DEBUG=' "$F")"
completer_env "$F" DEBUG True
verifier "completer_env n'écrase pas" "False" "$(lire_env "$F" DEBUG)"
completer_env "$F" VIDE oui
verifier "completer_env complète" "oui" "$(lire_env "$F" VIDE)"
printf 'SANS_FIN=1' >"$T/sansfin"; ecrire_env "$T/sansfin" B 2
verifier "ajout après une dernière ligne sans retour" $'SANS_FIN=1\nB=2' "$(cat "$T/sansfin")"

verifier "fusionner_liste sans doublon" "a.cm,b.cm,127.0.0.1,c.cm" "$(fusionner_liste "a.cm,b.cm" "127.0.0.1, b.cm,,c.cm")"
verifier "fusionner_liste liste vide" "x" "$(fusionner_liste "" "x")"

verifier "hote_bd complet" "db.exemple.cm" "$(hote_bd 'postgresql://u:p@db.exemple.cm:5432/base?sslmode=require')"
verifier "hote_bd sans identifiants" "10.0.0.5" "$(hote_bd 'postgres://10.0.0.5/base')"
est_locale 'postgresql://u:p@127.0.0.1:5432/b'; verifier "est_locale 127.0.0.1" "0" "$?"
est_locale 'postgresql://u:p@localhost/b'; verifier "est_locale localhost" "0" "$?"
est_locale 'postgresql://u:p@db.exemple.cm/b'; verifier "est_locale distante" "1" "$?"

mdp="$(aleatoire 32)"
verifier "aleatoire : 32 caractères" "32" "${#mdp}"
[[ "$mdp" =~ ^[A-Za-z0-9]+$ ]]; verifier "aleatoire : alphanumérique" "0" "$?"

lire_options --domaine api.ecole.cm --bd postgresql://u:p@db:5432/b --frontend https://ecole.cm --sans-https --oui
verifier "option --domaine" "api.ecole.cm" "$DOMAINE"
verifier "option --sans-https" "non" "$AVEC_HTTPS"
verifier "option --oui" "non" "$INTERACTIF"

aide_texte="$(bash "$ICI/deployer_backend.sh" --aide)"
[[ "$aide_texte" == *"--domaine api.ecole.cm"* && "$aide_texte" != *"set -E"* ]]; verifier "--aide affiche l'en-tête" "0" "$?"

if (( echecs )); then echo "$echecs échec(s)"; exit 1; fi
echo "Tous les tests passent."
