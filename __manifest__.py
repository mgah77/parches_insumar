# -*- coding: utf-8 -*-

{
    'name': 'Parches Insumar',
    'version': '1',
    'category': 'General',
    'summary': '',
    'description': """
    Parches Insumar

       """,
    'author' : 'M.Gah',
    'website': '',
    'depends': ['stock','base','sale','l10n_cl_fe'],
    'data': [
	    "security/groups.xml",
        "views/menu_restriccion.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
