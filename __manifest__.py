# -*- coding: utf-8 -*-

{
    'name': 'Insumar_parches',
    'version': '4.01',
    'category': 'General',
    'summary': '',
    'description': """
    Parches Insumar

       """,
    'author' : 'M.Gah',
    'website': '',
    'depends': ['account','stock','base','sale','sale_stock','sale_management','l10n_cl_fe','product','contacts','utm','hr','crm'],
    'data': [
            "security/groups.xml",
            "security/ir.model.access.csv",
	        "views/product_template.xml",
            "views/stock_picking.xml",
            "views/sale_order.xml",
            "views/account.xml",
            "views/banned_menu_views.xml",
            "views/configuration_menu.xml",
            "views/partner.xml",
            "views/calendar.xml",
            "views/sale_template.xml",
            "views/crm.xml"
    ],
    'assets': {
        'web.report_assets_common': [
            'parches_insumar/static/src/css/styles_pdf_layout.css',
        ],
    },            
    'installable': True,
    'auto_install': False,
    'application': True,
}
