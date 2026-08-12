# Contribuer à l'OCA — Processus de review

Résumé de la page [odoo-community.org/resources/review](https://www.odoo-community.org/resources/review), qui explique comment participer aux revues de code (reviews) des contributions à l'OCA (Odoo Community Association).

## Étapes principales

1. **Créer un compte GitHub**
   Un compte GitHub gratuit est nécessaire : renseigner une adresse e-mail et la confirmer via le lien reçu par e-mail.

2. **Choisir une contribution à examiner**
   Parcourir les demandes de révision (pull requests) disponibles en filtrant par :
   - nom du projet (ex : `OCA/bank-payment`) ;
   - titre de la contribution ;
   - résultats des tests automatisés (une coche verte est requise) ;
   - étiquettes spécifiques, notamment `needs review` ;
   - version d'Odoo ciblée.

3. **Comprendre la description**
   Lire attentivement la description de la fonctionnalité ou du correctif proposé. Si les explications manquent de clarté, demander des précisions en commentaire de la pull request.

4. **Tester la contribution**
   Une instance Odoo fonctionnelle est généralement disponible via un lien **Runboat**, avec les identifiants :
   - Email : `admin`
   - Mot de passe : `admin`

## Critères de validation

Après les tests, soumettre son avis via le bouton **"Review changes"** sur GitHub, avec deux choix possibles :
- **Approuver** si tout fonctionne correctement ;
- **Demander des modifications**, en décrivant précisément les problèmes rencontrés.

## Aller plus loin

Les contributeurs motivés peuvent rejoindre la liste de diffusion **"Contributors"** de l'OCA pour s'impliquer davantage, selon leurs compétences et leur disponibilité.

## Faire une review en local avec le script `clone-pr.sh`

Plutôt que d'utiliser Runboat, il est possible de tester une PR sur sa propre base Odoo (ex : base `oca18` dédiée aux tests). Le script [`scripts-externes/clone-pr.sh`](../scripts-externes/clone-pr.sh) de ce module automatise la récupération du code.

### Fonctionnement du script

À partir de l'URL d'une pull request, le script :
1. Interroge l'API Github pour trouver le fork et la branche de la PR.
2. Détecte automatiquement le(s) dossier(s) de module modifié(s) par la PR.
3. Télécharge **uniquement** ce(s) dossier(s) (sparse-checkout Git, profondeur 1) — pas besoin de cloner tout le dépôt.
4. Place le(s) module(s) dans le répertoire courant, prêt à être ajouté à l'`addons_path`, et nettoie tous les fichiers temporaires (dont `.git`).

### Procédure rapide

1. Se placer dans le dossier contenant les modules de la base de test :
   ```bash
   cd ~/Documents/Développement/dev_odoo/18.0/oca18
   ```

2. Lancer le script avec l'URL de la PR :
   ```bash
   ./is_github18/scripts-externes/clone-pr.sh https://github.com/OCA/<depot>/pull/<numero>
   ```
   (Astuce : définir `GITHUB_TOKEN` en variable d'environnement pour éviter la limite de l'API Github non authentifiée.)

3. Installer ou mettre à jour le module sur la base de test :
 
4. Tester le scénario décrit dans la PR sur l'interface Odoo (base `oca18`).


### Poster sa review sur GitHub

1. Sur la page de la PR, aller sur l'onglet **"Files changed"** pour parcourir le code modifié (c'est ce qui fait apparaître le bouton "Submit review" en haut à droite).
2. Cliquer sur ce bouton **"Submit review"**
3. Rédiger un commentaire court et factuel, en anglais, décrivant ce qui a été testé. Exemple :
   ```
   Functional review

   Tested on Odoo 18.0: <résumé très court du scénario testé et du résultat>. Works as expected.
   ```
4. Choisir :
   - **Approve** si tout fonctionne correctement ;
   - **Request changes** si un problème bloquant a été rencontré (le décrire précisément) ;
   - **Comment** pour un simple avis sans validation.
5. Cliquer sur **"Submit review"**.
