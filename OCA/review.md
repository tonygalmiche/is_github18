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

## Se faire aider par Claude pour une review

Workflow habituel avec l'assistant pour dérouler une review de bout en bout, sans avoir à tout réexpliquer à chaque fois.

### 1. Récupérer les infos d'une PR

Donner l'URL de la PR (`https://github.com/OCA/<depot>/pull/<numero>`). `gh` n'est pas authentifié sur ce poste (`gh auth login` en échec), donc l'assistant utilise l'API publique Github en `curl` :
```bash
curl -s https://api.github.com/repos/OCA/<depot>/pulls/<numero>
curl -s https://api.github.com/repos/OCA/<depot>/issues/<numero>/comments        # commentaires généraux
curl -s https://api.github.com/repos/OCA/<depot>/pulls/<numero>/comments        # commentaires en ligne (review comments)
```
Il en tire : titre, état, branche cible, description, labels, stats (commits/fichiers), et le contenu des commentaires. Il précise si la PR dépend d'une autre PR, et son état (mergée ou non).

### 2. Comprendre le module et préparer un plan de test

L'assistant récupère les fichiers utiles (modèles, vues, README) depuis le fork/branche de la PR via `raw.githubusercontent.com/<fork>/<branche>/<chemin>`, sans cloner. Il en déduit un plan de test concret adapté au module (étapes UI précises, cas limites, contre-tests), et peut vérifier si le module est une **migration** (déjà présent sur une branche antérieure) ou un **nouveau module**.

### 3. Récupérer le code sur la base de test

Utiliser `clone-module.sh` (ou `clone-pr.sh`, voir plus haut) pour télécharger uniquement le(s) dossier(s) du module — l'assistant donne l'URL exacte du module (`.../tree/<branche>/<module>`) à passer au script, y compris pour les dépendances manquantes signalées par Odoo au démarrage.

### 4. Tests unitaires : pas nécessaire de les rejouer en local

La CI Github les fait déjà tourner à chaque push. Se concentrer sur le **test fonctionnel manuel en UI**.

### 5. Vérification en base (SSH + psql)

Pour valider un comportement backend difficile à observer en UI (ex. quel utilisateur a été assigné à un enregistrement créé automatiquement), l'assistant peut exécuter des requêtes SQL en lecture seule via SSH sur l'environnement de test, à condition d'avoir un accès.

### 6. Rédiger le commentaire de review

Sur demande, l'assistant rédige le texte à poster (voir section précédente) :
- Toujours en **anglais**, factuel, sans fioritures.
- Commence par `Tested on a local Odoo <version> instance: ...`.
- Format court par défaut ; sur demande, reformulé plus court ou en **liste à tirets** (un point testé par ligne).
- Se base uniquement sur les tests réellement confirmés par l'utilisateur dans la conversation (l'assistant demande confirmation si un résultat n'a pas été explicitement validé).
- **Toujours fourni dans un bloc de code** (```) pour un copier/coller direct dans le champ de review Github.

