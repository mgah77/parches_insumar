# -*- coding: utf-8 -*-

{
    'name': 'Parches Insumar',
    'version': '2.01',
    'category': 'General',
    'summary': '',
    'description': """
    Parches Insumar

       """,
    'author' : 'M.Gah',
    'website': '',
    'depends': ['stock','base','sale','sale_stock','l10n_cl_fe','product'],
    'data': [
            "security/groups.xml",
            "security/ir.model.access.csv"
	        "views/product_template.xml",
            "views/stock.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
