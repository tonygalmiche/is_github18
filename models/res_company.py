# -*- coding: utf-8 -*-
from odoo import fields, models  # type: ignore


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_github_key = fields.Char("Clé API Github")
