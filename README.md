# Module InfoSaône Github pour Odoo 18

## But du module

Ce module permet d'analyser des comptes GitHub directement depuis Odoo 18.

Il offre les fonctionnalités suivantes :

- **Fiche Société** : stockage sécurisé d'une clé API GitHub pour lever les limitations de l'API anonyme (60 requêtes/heure → 5 000 requêtes/heure avec clé).
- **Comptes Github** (`is.github.compte`) : gestion d'une liste de comptes GitHub (organisations ou utilisateurs) avec récupération automatique :
  - du nombre de dépôts publics,
  - du nombre de membres (organisation) ou de followers (utilisateur).
- **Actualisation à la demande** via un bouton dans la fiche du compte.

---

## Configuration de la clé API GitHub

### Pourquoi une clé API ?

Sans authentification, l'API GitHub est limitée à **60 requêtes par heure** par adresse IP. Avec un *Personal Access Token*, cette limite passe à **5 000 requêtes par heure**.

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
