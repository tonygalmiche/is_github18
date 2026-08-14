#!/usr/bin/env bash
#
# clone-module.sh - Récupère un seul dossier (module) d'un dépôt Github, à une branche
#                    donnée, dans le dossier courant, sans cloner tout le dépôt.
#
# Usage :
#   ./clone-module.sh https://github.com/OCA/field-service/tree/18.0/fieldservice
#
set -euo pipefail

URL="${1:-}"
if [ -z "$URL" ]; then
    echo "Usage : $0 <url_github_tree>"
    echo "Exemple : $0 https://github.com/OCA/field-service/tree/18.0/fieldservice"
    exit 1
fi

if ! [[ "$URL" =~ ^https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)$ ]]; then
    echo "URL invalide : $URL"
    echo "Format attendu : https://github.com/<owner>/<repo>/tree/<branche>/<chemin_module>"
    exit 1
fi

OWNER="${BASH_REMATCH[1]}"
REPO="${BASH_REMATCH[2]}"
BRANCH="${BASH_REMATCH[3]}"
MODULE_PATH="${BASH_REMATCH[4]%/}"
MODULE_NAME="$(basename "$MODULE_PATH")"

echo "==> Dépôt   : ${OWNER}/${REPO}"
echo "==> Branche : ${BRANCH}"
echo "==> Module  : ${MODULE_PATH}"

TMP_DIR=".clone-module-tmp-${MODULE_NAME}"
rm -rf "$TMP_DIR"
mkdir "$TMP_DIR"
cd "$TMP_DIR"

git init -q
git remote add origin "https://github.com/${OWNER}/${REPO}.git"
git sparse-checkout init --no-cone
git sparse-checkout set "${MODULE_PATH}/*"

echo "==> Téléchargement..."
git fetch -q --depth 1 origin "$BRANCH"
git checkout -q FETCH_HEAD

cd ..

echo "==> Déplacement du module dans le répertoire courant..."
rm -rf "./${MODULE_NAME}"
mv "${TMP_DIR}/${MODULE_PATH}" "./${MODULE_NAME}"
rm -rf "$TMP_DIR"

echo "==> Terminé. Module récupéré : ${MODULE_NAME}"
