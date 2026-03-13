# -*- coding: utf-8 -*-
import logging
import re
import requests
from datetime import datetime
from odoo import fields, models, api  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_logger = logging.getLogger(__name__)


class IsGithubModuleStat(models.Model):
    _name        = 'is.github.module.stat'
    _description = "Statistiques modules par branche"
    _auto        = False
    _order       = 'repository_id, branch_id'

    repository_id = fields.Many2one('is.github.repository', "Dépôt"  , readonly=True)
    compte_id     = fields.Many2one('is.github.compte'    , "Compte"  , readonly=True)
    branch_id     = fields.Many2one('is.github.branch'    , "Branche" , readonly=True)
    is_version    = fields.Boolean("Branche de version"  , readonly=True)
    version_major = fields.Integer("Version majeure"      , readonly=True)
    module_count  = fields.Integer("Modules"              , readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS is_github_module_stat")
        self.env.cr.execute("""
            CREATE VIEW is_github_module_stat AS (
                SELECT
                    (m.repository_id * 100000 + rel.branch_id) AS id,
                    m.repository_id,
                    r.compte_id,
                    rel.branch_id,
                    (b.name ~ '^[0-9]+\\.[0-9]+$') AS is_version,
                    CASE WHEN b.name ~ '^[0-9]+\\.[0-9]+$'
                         THEN CAST(SPLIT_PART(b.name, '.', 1) AS INTEGER)
                         ELSE 0
                    END AS version_major,
                    COUNT(m.id) AS module_count
                FROM is_github_module m
                JOIN is_github_module_branch_rel rel ON rel.module_id = m.id
                JOIN is_github_repository r ON r.id = m.repository_id
                JOIN is_github_branch b ON b.id = rel.branch_id
                GROUP BY m.repository_id, r.compte_id, rel.branch_id, b.name
            )
        """)


class IsGithubCompte(models.Model):
    _name        = 'is.github.compte'
    _description = "Compte Github"
    _order       = 'name'

    name             = fields.Char("Nom"                        , required=True, index=True)
    url              = fields.Char("URL"                        , compute='_compute_url')
    commentaire      = fields.Text("Commentaire")
    nb_repos         = fields.Integer("Nombre de dépôts"        , readonly=True)
    nb_contributors  = fields.Integer("Nombre de contributeurs" , readonly=True)
    repository_ids   = fields.One2many('is.github.repository'   , 'compte_id', string="Liste des dépôts")
    repository_count = fields.Integer("Dépôts"                  , compute='_compute_repository_count')

    @api.depends('name')
    def _compute_url(self):
        for rec in self:
            rec.url = f"https://github.com/{rec.name}" if rec.name else ""

    @api.depends('repository_ids')
    def _compute_repository_count(self):
        for rec in self:
            rec.repository_count = len(rec.repository_ids)

    def _fetch_all_pages(self, url, headers, params=None):
        """Récupère tous les éléments paginés d'un endpoint GitHub."""
        items       = []
        page        = 1
        base_params = dict(params or {})
        while True:
            base_params.update({'per_page': 100, 'page': page})
            resp = requests.get(url, headers=headers, params=base_params, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            items.extend(data)
            if len(data) < 100:
                break
            page += 1
        return items

    def action_actualiser(self):
        self.ensure_one()
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        name = self.name

        # Tentative via l'endpoint organisation
        resp = requests.get(f'https://api.github.com/orgs/{name}', headers=headers, timeout=15)
        if resp.status_code == 200:
            data            = resp.json()
            nb_repos        = data.get('public_repos', 0)
            members         = self._fetch_all_pages(f'https://api.github.com/orgs/{name}/members', headers)
            nb_contributors = len(members)
        else:
            # Tentative via l'endpoint utilisateur
            resp = requests.get(f'https://api.github.com/users/{name}', headers=headers, timeout=15)
            if resp.status_code == 200:
                data            = resp.json()
                nb_repos        = data.get('public_repos', 0)
                nb_contributors = data.get('followers', 0)
            else:
                raise UserError(f"Impossible de récupérer les données pour le compte « {name} » (code {resp.status_code}).")

        self.write({
            'nb_repos'       : nb_repos,
            'nb_contributors': nb_contributors,
        })

    def action_fetch_repositories(self):
        """Récupère tous les dépôts du compte et les crée/met à jour localement."""
        self.ensure_one()
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        name = self.name

        # Tentative org → utilisateur
        resp = requests.get(f'https://api.github.com/orgs/{name}', headers=headers, timeout=15)
        if resp.status_code == 200:
            repos = self._fetch_all_pages(f'https://api.github.com/orgs/{name}/repos', headers, {'type': 'public'})
        else:
            resp2 = requests.get(f'https://api.github.com/users/{name}', headers=headers, timeout=15)
            if resp2.status_code == 200:
                repos = self._fetch_all_pages(f'https://api.github.com/users/{name}/repos', headers)
            else:
                raise UserError(f"Impossible de récupérer les dépôts pour le compte « {name} ».")

        Repo     = self.env['is.github.repository']
        existing = {r.name: r for r in self.repository_ids}

        for repo_data in repos:
            repo_name = repo_data.get('name', '')
            if repo_name and repo_name not in existing:
                Repo.create({'name': repo_name, 'compte_id': self.id})

        self.nb_repos = len(repos)

    def action_view_repositories(self):
        """Ouvre la liste des dépôts de ce compte."""
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Dépôts — {self.name}',
            'res_model': 'is.github.repository',
            'view_mode': 'list,form',
            'domain'   : [('compte_id', '=', self.id)],
            'context'  : {'default_compte_id': self.id},
        }



class IsGithubBranch(models.Model):
    _name        = 'is.github.branch'
    _description = "Branche Github"
    _order       = 'name'

    name  = fields.Char("Nom"    , required=True, index=True)
    color = fields.Integer("Couleur", default=0)
    is_version    = fields.Boolean("Branche de version",  compute='_compute_is_version', store=True, readonly=False)
    version_major = fields.Integer("Version majeure",      compute='_compute_is_version', store=True, readonly=True)
    module_link_ids = fields.Many2many(
        'is.github.module',
        'is_github_module_branch_rel', 'branch_id', 'module_id',
        string="Liste des modules"
    )
    module_count = fields.Integer("Modules", compute='_compute_module_count', store=True)

    @api.depends('name')
    def _compute_is_version(self):
        import re as _re
        for rec in self:
            m = _re.match(r'^(\d+)\.\d+$', rec.name or '')
            rec.is_version    = bool(m)
            rec.version_major = int(m.group(1)) if m else 0

    @api.depends('module_link_ids')
    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_link_ids)

    def action_view_modules(self):
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Modules — {self.name}',
            'res_model': 'is.github.module',
            'view_mode': 'list,form',
            'domain'   : [('branch_ids', 'in', [self.id])],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'color' not in vals and vals.get('name'):
                vals['color'] = (hash(vals['name']) % 11) + 1
        return super().create(vals_list)

    def action_compute_color(self):
        """Recalcule la couleur à partir du nom."""
        for rec in self:
            rec.color = (hash(rec.name or '') % 11) + 1 if rec.name else 0


class IsGithubModule(models.Model):
    _name        = 'is.github.module'
    _description = "Module Github (OCA)"
    _order       = 'repository_id, name'

    name          = fields.Char("Nom"        , required=True, index=True)
    repository_id = fields.Many2one('is.github.repository', "Dépôt", required=True, ondelete='cascade', index=True)
    branch_ids    = fields.Many2many(
        'is.github.branch',
        'is_github_module_branch_rel', 'module_id', 'branch_id',
        string="Branches"
    )
    branch_count  = fields.Integer("Nb branches", compute='_compute_branch_count', store=True)
    commentaire   = fields.Text("Commentaire")

    @api.depends('branch_ids')
    def _compute_branch_count(self):
        for rec in self:
            rec.branch_count = len(rec.branch_ids)

    def action_view_branches(self):
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Branches — {self.name}',
            'res_model': 'is.github.branch',
            'view_mode': 'list,form',
            'domain'   : [('id', 'in', self.branch_ids.ids)],
        }


class IsGithubContributor(models.Model):
    _name        = 'is.github.contributor'
    _description = "Contributeur Github"
    _order       = 'name'

    name             = fields.Char("Nom")
    url              = fields.Char("URL")
    repository_ids   = fields.Many2many(
        'is.github.repository',
        'is_github_repo_contributor_rel', 'contributor_id', 'repository_id',
        string="Liste des dépôts"
    )
    repository_count = fields.Integer("Dépôts", compute='_compute_repository_count', store=True)

    @api.depends('repository_ids')
    def _compute_repository_count(self):
        for rec in self:
            rec.repository_count = len(rec.repository_ids)

    def action_view_repositories(self):
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Dépôts de {self.name}',
            'res_model': 'is.github.repository',
            'view_mode': 'list,form',
            'domain'   : [('contributor_ids', 'in', [self.id])],
        }


class IsGithubRepository(models.Model):
    _name        = 'is.github.repository'
    _description = "Dépôt Github"
    _order       = 'name'

    name             = fields.Char("Nom"                        , required=True, index=True)
    url              = fields.Char("URL"                        , compute='_compute_url')
    compte_id        = fields.Many2one('is.github.compte'       , "Compte"               , required=True, ondelete='cascade', index=True)
    branch_ids       = fields.Many2many('is.github.branch'      , string="Branches")
    contributor_ids  = fields.Many2many(
        'is.github.contributor',
        'is_github_repo_contributor_rel', 'repository_id', 'contributor_id',
        string="Liste des contributeurs"
    )
    contributor_count = fields.Integer("Contributeurs"          , compute='_compute_contributor_count')
    nb_contributors  = fields.Integer("Nombre de contributeurs" , readonly=True, store=True)
    nb_commits       = fields.Integer("Nombre de commits"       , readonly=True)
    last_commit_date = fields.Datetime("Dernier commit"         , readonly=True)
    module_ids       = fields.One2many('is.github.module', 'repository_id', string="Liste des modules")
    module_count     = fields.Integer("Modules"                 , compute='_compute_module_count', store=True)
    commentaire      = fields.Text("Commentaire")

    @api.depends('name', 'compte_id.name')
    def _compute_url(self):
        for rec in self:
            if rec.compte_id and rec.name:
                rec.url = f"https://github.com/{rec.compte_id.name}/{rec.name}"
            else:
                rec.url = ""

    @api.depends('contributor_ids')
    def _compute_contributor_count(self):
        for rec in self:
            rec.contributor_count = len(rec.contributor_ids)

    @api.depends('module_ids')
    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_ids)

    def action_view_contributors(self):
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Contributeurs — {self.name}',
            'res_model': 'is.github.contributor',
            'view_mode': 'list',
            'domain'   : [('repository_id', '=', self.id)],
            'context'  : {'default_repository_id': self.id},
        }
    def action_view_modules(self):
        self.ensure_one()
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Modules — {self.name}',
            'res_model': 'is.github.module',
            'view_mode': 'list,form',
            'domain'   : [('repository_id', '=', self.id)],
            'context'  : {'default_repository_id': self.id},
        }
    def _fetch_all_pages(self, url, headers, params=None):
        items      = []
        page       = 1
        base_params = dict(params or {})
        while True:
            base_params.update({'per_page': 100, 'page': page})
            resp = requests.get(url, headers=headers, params=base_params, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            items.extend(data)
            if len(data) < 100:
                break
            page += 1
        return items

    def _do_actualiser(self, headers):
        """Actualise un seul dépôt. Doit être appelé avec ensure_one()."""
        owner    = self.compte_id.name
        repo     = self.name
        base_url = f'https://api.github.com/repos/{owner}/{repo}'

        # --- Branches ---
        branches          = self._fetch_all_pages(f'{base_url}/branches', headers)
        Branch            = self.env['is.github.branch']
        branch_ids        = []
        branch_name_to_id = {}
        for b in branches:
            bname    = b.get('name', '')
            existing = Branch.search([('name', '=', bname)], limit=1)
            if not existing:
                existing = Branch.create({'name': bname})
            branch_ids.append(existing.id)
            branch_name_to_id[bname] = existing.id

        # --- Contributeurs ---
        contributors    = self._fetch_all_pages(f'{base_url}/contributors', headers)
        Contributor     = self.env['is.github.contributor']
        new_contrib_ids = []
        for c in contributors:
            login = c.get('login', '')
            curl  = c.get('html_url', '')
            if not login:
                continue
            existing = Contributor.search([('name', '=', login)], limit=1)
            if existing:
                if existing.url != curl:
                    existing.url = curl
                new_contrib_ids.append(existing.id)
            else:
                new_contrib_ids.append(Contributor.create({'name': login, 'url': curl}).id)
        nb_contributors = len(new_contrib_ids)

        # --- Dernier commit & nombre de commits ---
        last_commit_date = False
        nb_commits       = 0
        resp = requests.get(f'{base_url}/commits', headers=headers,
                            params={'per_page': 1}, timeout=15)
        if resp.status_code == 200:
            commits = resp.json()
            if commits:
                date_str = (commits[0].get('commit', {})
                                      .get('committer', {})
                                      .get('date', ''))
                if date_str:
                    last_commit_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            # Nombre total de commits via l'en-tête Link
            link  = resp.headers.get('Link', '')
            match = re.search(r'[?&]page=(\d+)>; rel="last"', link)
            if match:
                nb_commits = int(match.group(1))
            else:
                nb_commits = len(self._fetch_all_pages(f'{base_url}/commits', headers))

        self.write({
            'branch_ids'      : [(6, 0, branch_ids)],
            'contributor_ids' : [(6, 0, new_contrib_ids)],
            'nb_contributors' : nb_contributors,
            'nb_commits'      : nb_commits,
            'last_commit_date': last_commit_date,
        })

        # --- Modules (dossiers racine par branche) ---
        _EXCLUDED = {'setup', 'dist', 'build', 'docs', 'doc', 'tests', 'test'}
        module_branches = {}  # {folder_name: [branch_id, ...]}
        for b in branches:
            bname = b.get('name', '')
            bid   = branch_name_to_id.get(bname)
            resp_c = requests.get(f'{base_url}/contents/', headers=headers,
                                  params={'ref': bname}, timeout=15)
            if resp_c.status_code != 200:
                continue
            for item in resp_c.json():
                if item.get('type') != 'dir':
                    continue
                fname = item['name']
                if fname.startswith('.') or fname.startswith('_') or fname in _EXCLUDED:
                    continue
                module_branches.setdefault(fname, []).append(bid)

        existing_modules = {m.name: m for m in self.module_ids}
        found_names = set(module_branches.keys())
        # Supprimer les modules disparus
        for mname, mrec in existing_modules.items():
            if mname not in found_names:
                mrec.unlink()
        # Créer ou mettre à jour
        Module = self.env['is.github.module']
        for mname, mbranch_ids in module_branches.items():
            if mname in existing_modules:
                existing_modules[mname].write({'branch_ids': [(6, 0, mbranch_ids)]})
            else:
                Module.create({'name': mname, 'repository_id': self.id,
                               'branch_ids': [(6, 0, mbranch_ids)]})

        # Mettre à jour module_count sur les branches impactées
        self.branch_ids._compute_module_count()
        # Mettre à jour module_count sur ce dépôt
        self._compute_module_count()

    def action_actualiser(self):
        self.ensure_one()
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        self._do_actualiser(headers)

    def action_actualiser_selection(self):
        """Actualise les dépôts sélectionnés de manière synchrone."""
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        total = len(self)
        _logger.info("[Github] Actualisation lancée : %d dépôt(s)", total)
        for idx, repo in enumerate(self, start=1):
            _logger.info("[Github] Dépôt %d/%d : '%s/%s'", idx, total, repo.compte_id.name, repo.name)
            repo._do_actualiser(headers)
        _logger.info("[Github] Actualisation terminée : %d dépôt(s)", total)
