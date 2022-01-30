# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mozan Inventory Customization',
    'version': '1.1',
    'author': 'Intellisoft Software',
    'summary': 'Inventory, Logistics, Warehousing and Inspection',
        'description': """
This module allows you to manage your Inventory.
===========================================================

Easily manage receipts and delivery orders , Control Products and all operations are stock moves between locations.""",

    'website': 'http://www.intellisoft.sd',
    'images': ['static/description/icon.png'],
    'depends': ['stock_account','account','product','stock', 'barcodes', 'web_planner','stock_landed_costs','sale'],
    'category': 'Warehouse',
    'sequence': 13,
    'data': [
        'views/product_template_view.xml',
        'reports/product_reports.xml',
        'reports/product_template_report.xml',
        'reports/delivery_report.xml',
        'reports/mozan_template.xml',
        'wizard/sales_report_view.xml',
        'wizard/costing_report_view.xml',
        'views/product_costing_sequence.xml',
        'views/stock_landed_cost_view.xml',



    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
