# -*- coding: utf-8 -*-
{
    'name': "Sales Mozan",

    'summary': """add some futures for the defual odoo sales modules
        """,

  

    'author': "Intellisoft Software",
    'website': "http://www.intellisoft.sd",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','is_mozan_stock_customization'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/is_sale_security.xml',
        'views/sale_order_view.xml',
        'report/report.xml'
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
