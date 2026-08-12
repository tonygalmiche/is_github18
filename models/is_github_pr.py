# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime
import requests
from odoo import fields, models, api  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_logger = logging.getLogger(__name__)


def _parse_gh_datetime(date_str):
    if not date_str:
        return False
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')


class IsGithubPr(models.Model):
    _name        = 'is.github.pr'
    _description = "Pull Request Github"
    _order       = 'compte_id, repository_id, number desc'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [
        ('repository_number_uniq', 'unique(repository_id, number)', "Cette Pull Request existe déjà pour ce dépôt."),
    ]

    number             = fields.Integer("Numéro"        , required=True, tracking=True)
    name               = fields.Char("Titre"            , required=True, tracking=True)
    url                = fields.Char("URL"               , tracking=True)
    repository_id      = fields.Many2one('is.github.repository', "Dépôt"  , required=True, ondelete='cascade', index=True, tracking=True)
    compte_id          = fields.Many2one('is.github.compte'     , "Compte" , related='repository_id.compte_id', store=True, index=True, tracking=True)
    branch_id          = fields.Many2one('is.github.branch'     , "Branche cible", index=True, tracking=True)
    module_ids         = fields.Many2many(
        'is.github.module',
        'is_github_pr_module_rel', 'pr_id', 'module_id',
        string="Modules", tracking=True
    )
    contributor_id     = fields.Many2one('is.github.contributor', "Auteur" , index=True, tracking=True)
    state              = fields.Selection([
        ('open'  , "Ouverte"),
        ('closed', "Fermée"),
        ('merged', "Fusionnée"),
    ], "État", default='open', required=True, tracking=True)
    draft              = fields.Boolean("Brouillon", tracking=True)
    needs_review       = fields.Boolean("Needs review", index=True, tracking=True)
    action             = fields.Selection([
        ('analyse'   , "Analysé"),
        ('a_faire'   , "A faire"),
        ('fait'      , "Fait"),
        ('abandonne' , "Abandonné"),
    ], "Action", index=True, tracking=True)
    labels             = fields.Char("Étiquettes"        , tracking=True)
    github_created_at  = fields.Datetime("Créée le"      , tracking=True)
    github_updated_at  = fields.Datetime("Mise à jour le", tracking=True)
    last_sync_date     = fields.Datetime("Dernière actualisation", readonly=True, tracking=True)
    commentaire        = fields.Text("Commentaire"       , tracking=True)

    def action_set_abandonne(self):
        self.write({'action': 'abandonne'})

    def _do_actualiser(self, headers):
        """Actualise une seule PR depuis Github. Doit être appelé avec ensure_one()."""
        owner = self.repository_id.compte_id.name
        repo  = self.repository_id.name
        resp = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/pulls/{self.number}',
            headers=headers, timeout=15,
        )
        if resp.status_code != 200:
            raise UserError(
                f"Impossible de récupérer la PR #{self.number} ({owner}/{repo}) : code {resp.status_code}."
            )
        data = resp.json()

        label_names     = [lbl.get('name', '') for lbl in data.get('labels', [])]
        is_needs_review = any(lbl.strip().lower() == 'needs review' for lbl in label_names)

        pr_state = 'open'
        if data.get('state') == 'closed':
            pr_state = 'merged' if data.get('merged_at') else 'closed'

        title       = data.get('title', '')
        title_lower = title.lower()
        matched_module_ids = [
            m.id for m in self.repository_id.module_ids
            if m.name and m.name.lower() in title_lower
        ]

        author = data.get('user') or {}
        login  = author.get('login', '')
        contributor = self.contributor_id
        if login:
            Contributor = self.env['is.github.contributor']
            contributor = Contributor.search([('name', '=', login)], limit=1)
            if not contributor:
                contributor = Contributor.create({'name': login, 'url': author.get('html_url', '')})

        vals = {
            'name'              : title,
            'url'               : data.get('html_url', ''),
            'contributor_id'    : contributor.id if contributor else False,
            'state'             : pr_state,
            'draft'             : data.get('draft', False),
            'needs_review'      : is_needs_review,
            'labels'            : ', '.join(label_names),
            'github_created_at' : _parse_gh_datetime(data.get('created_at')),
            'github_updated_at' : _parse_gh_datetime(data.get('updated_at')),
            'last_sync_date'    : fields.Datetime.now(),
        }
        if matched_module_ids:
            vals['module_ids'] = [(6, 0, matched_module_ids)]
        self.write(vals)

    def action_actualiser(self):
        self.ensure_one()
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        self._do_actualiser(headers)

    def action_actualiser_selection(self):
        """Actualise les PR sélectionnées de manière synchrone."""
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        total = len(self)
        _logger.info("[Github] Actualisation lancée : %d PR(s)", total)
        for idx, pr in enumerate(self, start=1):
            _logger.info("[Github] PR %d/%d : '%s#%s'", idx, total, pr.repository_id.name, pr.number)
            pr._do_actualiser(headers)
        _logger.info("[Github] Actualisation terminée : %d PR(s)", total)


class IsGithubPrImport(models.Model):
    _name        = 'is.github.pr.import'
    _description = "Recherche / import de Pull Requests Github"
    _order       = 'name'

    name           = fields.Char("Nom"                       , required=True, default="Recherche PR")
    compte_ids     = fields.Many2many('is.github.compte'    , string="Comptes")
    module_ids     = fields.Many2many('is.github.module'    , string="Modules")
    branch_id      = fields.Many2one('is.github.branch'     , string="Branche", required=True)
    contributor_id = fields.Many2one('is.github.contributor', string="Contributeur")
    title_filter   = fields.Char("Filtre sur le titre")
    needs_review   = fields.Boolean("Needs review uniquement", default=True)
    state          = fields.Selection([
        ('open'  , "Ouverte"),
        ('closed', "Fermée"),
        ('all'   , "Toutes"),
    ], "État", default='open', required=True)
    limit          = fields.Integer("Nombre max. de résultats par compte", default=200)
    last_run_date  = fields.Datetime("Dernière recherche", readonly=True)
    last_created   = fields.Integer("Dernières PR créées"       , readonly=True)
    last_updated   = fields.Integer("Dernières PR mises à jour" , readonly=True)

    def _fetch_all_pages(self, headers, query, limit):
        items = []
        page  = 1
        while len(items) < limit:
            resp = requests.get(
                'https://api.github.com/search/issues', headers=headers,
                params={'q': query, 'per_page': 100, 'page': page, 'sort': 'updated', 'order': 'desc'},
                timeout=15,
            )
            if resp.status_code != 200:
                break
            data      = resp.json()
            page_items = data.get('items', [])
            if not page_items:
                break
            items.extend(page_items)
            if len(page_items) < 100:
                break
            page += 1
            time.sleep(1)
        return items[:limit]

    def action_fetch(self):
        self.ensure_one()
        token = self.env.company.is_github_key
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        comptes = self.compte_ids or self.env['is.github.compte'].search([])
        if not comptes:
            raise UserError("Aucun compte Github enregistré.")

        Pr          = self.env['is.github.pr']
        Repo        = self.env['is.github.repository']
        Contributor = self.env['is.github.contributor']

        wanted_module_ids = set(self.module_ids.ids)
        total_created = 0
        total_updated = 0

        for compte in comptes:
            query_parts = [f'org:{compte.name}', 'type:pr', f'base:{self.branch_id.name}']
            if self.state != 'all':
                query_parts.append(f'state:{self.state}')
            if self.needs_review:
                query_parts.append('label:"needs review"')
            if self.contributor_id:
                query_parts.append(f'author:{self.contributor_id.name}')
            query = ' '.join(query_parts)

            items = self._fetch_all_pages(headers, query, self.limit)

            for item in items:
                repo_full = item['repository_url'].split('/repos/')[-1]
                repo_name = repo_full.split('/', 1)[-1]
                repo = Repo.search([('compte_id', '=', compte.id), ('name', '=', repo_name)], limit=1)
                if not repo:
                    repo = Repo.create({'name': repo_name, 'compte_id': compte.id})

                author = item.get('user') or {}
                login  = author.get('login', '')
                contributor = False
                if login:
                    contributor = Contributor.search([('name', '=', login)], limit=1)
                    if not contributor:
                        contributor = Contributor.create({'name': login, 'url': author.get('html_url', '')})

                label_names   = [lbl.get('name', '') for lbl in item.get('labels', [])]
                is_needs_review = any(lbl.strip().lower() == 'needs review' for lbl in label_names)

                pr_state = 'open'
                if item.get('state') == 'closed':
                    pr_state = 'merged' if item.get('pull_request', {}).get('merged_at') else 'closed'

                title       = item.get('title', '')
                title_lower = title.lower()

                if self.title_filter and self.title_filter.lower() not in title_lower:
                    continue

                matched_module_ids = [
                    m.id for m in repo.module_ids
                    if m.name and m.name.lower() in title_lower
                ]

                if wanted_module_ids and not (wanted_module_ids & set(matched_module_ids)):
                    continue

                vals = {
                    'number'            : item['number'],
                    'name'              : title,
                    'url'               : item.get('html_url', ''),
                    'repository_id'     : repo.id,
                    'branch_id'         : self.branch_id.id,
                    'contributor_id'    : contributor.id if contributor else False,
                    'state'             : pr_state,
                    'draft'             : item.get('draft', False),
                    'needs_review'      : is_needs_review,
                    'labels'            : ', '.join(label_names),
                    'github_created_at' : _parse_gh_datetime(item.get('created_at')),
                    'github_updated_at' : _parse_gh_datetime(item.get('updated_at')),
                }
                if matched_module_ids:
                    vals['module_ids'] = [(6, 0, matched_module_ids)]

                existing = Pr.search([('repository_id', '=', repo.id), ('number', '=', item['number'])], limit=1)
                if existing:
                    existing.write(vals)
                    total_updated += 1
                else:
                    Pr.create(vals)
                    total_created += 1

        _logger.info("[Github] PR fetch : %d créée(s), %d mise(s) à jour", total_created, total_updated)

        self.write({
            'last_run_date': fields.Datetime.now(),
            'last_created' : total_created,
            'last_updated' : total_updated,
        })

        domain = [
            ('branch_id', '=', self.branch_id.id),
            ('compte_id', 'in', comptes.ids),
            ('action', '!=', 'abandonne'),
        ]
        if self.needs_review:
            domain.append(('needs_review', '=', True))
        if self.contributor_id:
            domain.append(('contributor_id', '=', self.contributor_id.id))
        if wanted_module_ids:
            domain.append(('module_ids', 'in', list(wanted_module_ids)))
        if self.title_filter:
            domain.append(('name', 'ilike', self.title_filter))

        return {
            'type'     : 'ir.actions.act_window',
            'name'     : f'Pull Requests ({total_created} créée(s), {total_updated} mise(s) à jour)',
            'res_model': 'is.github.pr',
            'view_mode': 'list,form',
            'domain'   : domain,
            'context'  : {'search_default_not_abandonne': 1},
        }
