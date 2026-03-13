# -*- coding: utf-8 -*-
{
    'name'     : 'Module InfoSaône Github pour Odoo 18',
    'version'  : '0.1',
    'author'   : 'InfoSaône',
    'category' : 'InfoSaône',
    'description': """
Module InfoSaône Github pour Odoo 18
===================================================
""",
    'maintainer' : 'InfoSaône',
    'website'    : 'http://www.infosaone.com',
    'depends'    : [
        'base',
    ],
    'data' : [
        'security/ir.model.access.csv',
        'views/res_company_view.xml',
        'views/is_github_repository_view.xml',
        'views/is_github_compte_view.xml',
        'views/menu.xml',
    ],
    "assets": {
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
