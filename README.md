# Module InfoSaône Github pour Odoo 18

## But du module

Ce module permet d'analyser des comptes et dépôts GitHub directement depuis Odoo 18.
Il interroge l'API GitHub pour rapatrier automatiquement les informations sur les comptes,
les dépôts, les branches, les contributeurs et les modules Odoo présents dans chaque dépôt.

---

## Fonctionnalités

### Comptes GitHub (`is.github.compte`)

Gestion d'une liste de comptes GitHub, qu'il s'agisse d'organisations ou d'utilisateurs.

Chaque fiche compte expose :

- Le **nom** du compte GitHub et son **URL** (calculée automatiquement).
- Le **nombre de dépôts** publics et le **nombre de membres/followers**.
- La liste des **dépôts** rattachés au compte.

Actions disponibles sur la fiche :

| Bouton | Effet |
|---|---|
| **Actualiser** | Interroge l'API GitHub pour mettre à jour le nombre de dépôts et de membres/followers. |
| **Récupérer les dépôts** | Crée dans Odoo tous les dépôts publics du compte qui n'existent pas encore. |
| **Dépôts** (stat button) | Ouvre la liste des dépôts rattachés à ce compte. |

---

### Dépôts GitHub (`is.github.repository`)

Chaque dépôt est rattaché à un compte. Une fiche dépôt contient :

- Le **nom** et l'**URL** du dépôt (calculée automatiquement).
- Les **branches** présentes (tags colorés).
- Le **nombre de contributeurs**, le **nombre de commits** et la **date du dernier commit**.
- La liste des **modules** Odoo détectés dans le dépôt.

Actions disponibles :

| Bouton | Effet |
|---|---|
| **Actualiser** (fiche ou liste) | Récupère depuis l'API GitHub les branches, les contributeurs, le nombre de commits, la date du dernier commit et la liste des modules présents dans chaque branche. |
| **Contributeurs** (stat button) | Ouvre la liste des contributeurs du dépôt. |
| **Modules** (stat button) | Ouvre la liste des modules détectés dans le dépôt. |

> La vue **liste** des dépôts dispose également d'un bouton **Actualiser** dans l'en-tête qui actualise tous les dépôts sélectionnés en une seule opération.

La vue **graphique** permet de visualiser, par compte, le nombre de contributeurs, de commits et de modules de chaque dépôt.

---

### Branches (`is.github.branch`)

Les branches sont créées automatiquement lors de l'actualisation des dépôts.

Chaque branche expose :

- Son **nom** et une **couleur** (attribuée automatiquement à la création, recalculable).
- Un indicateur **Branche de version** (activé si le nom suit le format `X.Y`, ex. `18.0`) et la **version majeure** correspondante.
- Le **nombre de modules** qui lui sont rattachés.

---

### Modules (`is.github.module`)

Les modules sont les **dossiers racine** détectés dans chaque branche d'un dépôt (les dossiers
`setup`, `dist`, `build`, `docs`, `tests`, etc. sont exclus automatiquement).

Chaque module expose :

- Son **nom**, le **dépôt** auquel il appartient et les **branches** dans lesquelles il est présent.
- Un champ **Commentaire** libre.

L'action **Voir les branches** ouvre la liste des branches qui contiennent ce module.

---

### Contributeurs (`is.github.contributor`)

Les contributeurs sont rapatriés depuis l'API lors de l'actualisation des dépôts.

Chaque contributeur expose :

- Son **login GitHub** et l'**URL** de son profil.
- La liste des **dépôts** sur lesquels il a contribué.

---

### Statistiques modules par branche (`is.github.module.stat`)

Vue SQL en lecture seule qui croise dépôts, branches et modules pour présenter, pour chaque
couple (dépôt, branche) :

- Le **nombre de modules** présents.
- Si la branche est une **branche de version** et sa **version majeure**.

Accessible depuis le menu **Github → Stat. modules**.

---

## Menus

Le module ajoute un menu principal **Github** avec les sous-menus suivants :

| Menu | Modèle |
|---|---|
| Comptes Github | `is.github.compte` |
| Dépôts Github | `is.github.repository` |
| Branches | `is.github.branch` |
| Contributeurs | `is.github.contributor` |
| Modules | `is.github.module` |
| Stat. modules | `is.github.module.stat` |

---

## Configuration de la clé API GitHub

### Pourquoi une clé API ?

Sans authentification, l'API GitHub est limitée à **60 requêtes par heure** par adresse IP.
Avec un *Personal Access Token*, cette limite passe à **5 000 requêtes par heure**.
Cette clé est indispensable dès lors que plusieurs dépôts sont actualisés en série.

### Étapes pour créer un Personal Access Token (classic)

1. Connectez-vous sur [https://github.com](https://github.com).

2. Cliquez sur votre **avatar** en haut à droite, puis sur **Settings**.

3. Dans le menu de gauche, descendez jusqu'à **Developer settings** (tout en bas).

4. Cliquez sur **Personal access tokens** → **Tokens (classic)**.

5. Cliquez sur **Generate new token** → **Generate new token (classic)**.

6. Renseignez les champs :
   - **Note** : donnez un nom explicite, par exemple `Odoo IS Github`.
   - **Expiration** : choisissez une durée selon vos besoins (90 jours, 1 an, ou sans expiration).
   - **Scopes** : pour un usage en lecture seule sur des données publiques, **aucun scope n'est nécessaire**. Cochez éventuellement `read:org` si vous souhaitez accéder aux membres d'organisations privées.

7. Cliquez sur **Generate token** en bas de page.

8. **Copiez immédiatement le token** affiché (il ne sera plus visible après avoir quitté la page).

### Saisie dans Odoo

1. Allez dans **Paramètres** → **Sociétés** → ouvrez votre société.
2. Cliquez sur l'onglet **Github**.
3. Collez le token dans le champ **Clé API Github**.
4. Sauvegardez.

---

## Utilisation

1. Allez dans le menu **Github** → **Comptes Github**.
2. Créez un nouveau compte en saisissant le **nom** du compte GitHub (ex : `oca`, `odoo`).
3. L'URL est calculée automatiquement : `https://github.com/oca`.
4. Cliquez sur le bouton **Actualiser** pour récupérer le nombre de dépôts et de contributeurs depuis l'API GitHub.
