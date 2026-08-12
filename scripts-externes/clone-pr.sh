#!/usr/bin/env bash
#
# clone-pr.sh - Récupère uniquement le(s) dossier(s) modifié(s) par une Pull Request
#               Github (OCA ou autre) dans le dossier courant, sans cloner tout le dépôt.
#
# Usage :
#   ./clone-pr.sh https://github.com/OCA/sale-workflow/pull/3925
#
# Variables d'environnement optionnelles :
#   GITHUB_TOKEN   Token Github (évite les limites de l'API non authentifiée)
#
set -euo pipefail

PR_URL="${1:-}"
if [ -z "$PR_URL" ]; then
    echo "Usage : $0 <url_pull_request_github>"
    exit 1
fi

if ! [[ "$PR_URL" =~ ^https://github\.com/([^/]+)/([^/]+)/pull/([0-9]+)/?$ ]]; then
    echo "URL de PR invalide : $PR_URL"
    echo "Format attendu : https://github.com/<owner>/<repo>/pull/<numero>"
    exit 1
fi

OWNER="${BASH_REMATCH[1]}"
REPO="${BASH_REMATCH[2]}"
PR_NUMBER="${BASH_REMATCH[3]}"

CURL_AUTH=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
    CURL_AUTH=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

echo "==> Récupération des infos de la PR ${OWNER}/${REPO}#${PR_NUMBER}..."

HEAD_INFO=$(curl -s "${CURL_AUTH[@]}" "https://api.github.com/repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
head = d.get('head', {})
repo = head.get('repo', {}) or {}
print(repo.get('full_name', ''))
print(head.get('ref', ''))
")

HEAD_REPO=$(echo "$HEAD_INFO" | sed -n '1p')
HEAD_REF=$(echo "$HEAD_INFO" | sed -n '2p')

if [ -z "$HEAD_REPO" ] || [ -z "$HEAD_REF" ]; then
    echo "Impossible de récupérer les infos de la PR (dépôt supprimé, PR introuvable, etc.)."
    exit 1
fi

echo "    Fork   : ${HEAD_REPO}"
echo "    Branche: ${HEAD_REF}"

echo "==> Récupération des dossiers modifiés..."

FOLDERS=$(curl -s "${CURL_AUTH[@]}" "https://api.github.com/repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/files?per_page=100" \
    | python3 -c "
import json, sys
files = json.load(sys.stdin)
folders = sorted({f['filename'].split('/')[0] for f in files if '/' in f['filename']})
print('\n'.join(folders))
")

if [ -z "$FOLDERS" ]; then
    echo "Aucun dossier de module détecté dans les fichiers modifiés."
    exit 1
fi

echo "    Dossier(s) : $(echo "$FOLDERS" | tr '\n' ' ')"

TMP_DIR=".clone-pr-tmp-${PR_NUMBER}"
rm -rf "$TMP_DIR"
mkdir "$TMP_DIR"
cd "$TMP_DIR"

git init -q
git remote add origin "https://github.com/${HEAD_REPO}.git"
git sparse-checkout init --no-cone

SPARSE_PATTERNS=()
while IFS= read -r folder; do
    SPARSE_PATTERNS+=("${folder}/*")
done <<< "$FOLDERS"
git sparse-checkout set "${SPARSE_PATTERNS[@]}"

echo "==> Téléchargement de la branche ${HEAD_REF}..."
git fetch -q --depth 1 origin "$HEAD_REF"
git checkout -q FETCH_HEAD

cd ..

echo "==> Déplacement des dossiers dans le répertoire courant..."
while IFS= read -r folder; do
    rm -rf "./${folder}"
    mv "${TMP_DIR}/${folder}" "./${folder}"
done <<< "$FOLDERS"

rm -rf "$TMP_DIR"

echo "==> Terminé. Dossier(s) récupéré(s) :"
echo "$FOLDERS"
