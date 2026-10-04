#!/usr/bin/env bash
#
# clone-pr.sh - Clone une Pull Request Github (OCA ou autre) dans le dossier ../OCA
#               et crée dans le dossier courant un lien vers chaque module modifié
#               par la PR.
#
# À lancer depuis le dossier des modules à tester (ex. dev_odoo/20.0/oca20) ;
# le dossier OCA doit être au même niveau (ex. dev_odoo/20.0/OCA).
#
# Installation (une fois) : lien dans ~/.local/bin, qui est dans le PATH
#   ln -s /home/tony/Documents/Développement/dev_odoo/18.0/infosaone/is_github18/scripts-externes/clone-pr.sh ~/.local/bin/clone-pr
#
# Usage :
#   clone-pr https://github.com/OCA/reporting-engine/pull/1203
#
# Résultat :
#   ../OCA/reporting-engine-pr1203/   clone complet du dépôt, branche pr-1203 = branche de la PR
#   ./report_xlsx -> ../OCA/reporting-engine-pr1203/report_xlsx
#
# Relancer le script met le clone à jour avec les derniers commits de la PR
# (refusé si le clone contient des modifications locales).
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

OCA_DIR="../OCA"
if [ ! -d "$OCA_DIR" ]; then
    echo "Dossier ${OCA_DIR} introuvable : il doit être au même niveau que le dossier courant."
    exit 1
fi

CLONE_NAME="${REPO}-pr${PR_NUMBER}"
CLONE_DIR="${OCA_DIR}/${CLONE_NAME}"
BRANCH="pr-${PR_NUMBER}"

CURL_AUTH=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
    CURL_AUTH=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

echo "==> Récupération des infos de la PR ${OWNER}/${REPO}#${PR_NUMBER}..."

PR_INFO=$(curl -s "${CURL_AUTH[@]}" "https://api.github.com/repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('base', {}).get('ref', ''))
print(d.get('title', ''))
print(d.get('state', ''))
")

BASE_REF=$(echo "$PR_INFO" | sed -n '1p')
PR_TITLE=$(echo "$PR_INFO" | sed -n '2p')
PR_STATE=$(echo "$PR_INFO" | sed -n '3p')

if [ -z "$BASE_REF" ]; then
    echo "Impossible de récupérer les infos de la PR (PR introuvable, limite de l'API, etc.)."
    exit 1
fi

echo "    Titre  : ${PR_TITLE}"
echo "    État   : ${PR_STATE}"
echo "    Cible  : ${BASE_REF}"

if [ -d "$CLONE_DIR" ]; then
    echo "==> Mise à jour du clone ${CLONE_DIR}..."
    if [ -n "$(git -C "$CLONE_DIR" status --porcelain)" ]; then
        echo "Le clone contient des modifications locales : mise à jour annulée."
        git -C "$CLONE_DIR" status --short
        exit 1
    fi
else
    echo "==> Clone de ${OWNER}/${REPO} (branche ${BASE_REF}) dans ${CLONE_DIR}..."
    git clone -q --filter=blob:none --single-branch --branch "$BASE_REF" \
        "https://github.com/${OWNER}/${REPO}.git" "$CLONE_DIR"
fi

# La branche de la PR est lue sur le dépôt d'origine (refs/pull/N/head) :
# fonctionne même si le fork de l'auteur a été supprimé.
git -C "$CLONE_DIR" fetch -q origin \
    "+refs/heads/${BASE_REF}:refs/remotes/origin/${BASE_REF}" \
    "+pull/${PR_NUMBER}/head:refs/remotes/origin/${BRANCH}"
git -C "$CLONE_DIR" checkout -q -B "$BRANCH" "origin/${BRANCH}"
echo "    Branche ${BRANCH} : $(git -C "$CLONE_DIR" log -1 --format='%h %cd %s' --date=short)"

echo "==> Modules modifiés par la PR..."
MODULES=$(git -C "$CLONE_DIR" diff --name-only "origin/${BASE_REF}...${BRANCH}" \
    | cut -d/ -f1 | sort -u \
    | while IFS= read -r folder; do
        [ -f "${CLONE_DIR}/${folder}/__manifest__.py" ] && echo "$folder"
    done || true)

if [ -z "$MODULES" ]; then
    echo "Aucun module (dossier avec __manifest__.py) modifié par la PR."
    exit 1
fi

echo "==> Liens dans $(pwd) :"
while IFS= read -r module; do
    target="${CLONE_DIR}/${module}"
    if [ -e "$module" ] && [ ! -L "$module" ]; then
        echo "    ${module} : existe déjà et n'est pas un lien, laissé tel quel"
        continue
    fi
    ln -sfn "$target" "$module"
    echo "    ${module} -> ${target}"
done <<< "$MODULES"

echo "==> Terminé."
