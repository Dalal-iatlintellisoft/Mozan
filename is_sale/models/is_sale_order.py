# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    g_discount = fields.Float('Discount')
    taxes_ids=fields.Many2many('account.tax')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('approve', 'Manager Approve'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    total_b_d=fields.Float(compute="getTotalBD")

    def back_draft(self):
        self.state='draft'

    @api.one
    def getTotalBD(self):
        t=0
        for rec in self.order_line:
           t+=rec.subtotal_wd
        self.total_b_d=t

    @api.onchange('g_discount','order_line')
    def check_discount(self):
        for rec in self.order_line:
            rec.discount = self.g_discount

    @api.onchange('taxes_ids','order_line')
    def check_tax(self):
        for rec in self.order_line:
            rec.tax_id=self.taxes_ids

    def approve(self):
        self.state = 'approve'

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    company=fields.Char(store=False)
    en_name=fields.Char(store=False)
    ar_name=fields.Char(store=False)
    veriant =fields.Char(store=False)
    size =fields.Char(store=False)
    subtotal_wd=fields.Float(compute='getsubWithoutDisc')
    qty_package = fields.Float(string="Qty Package", compute='get_qty_package')

    @api.one
    @api.depends('product_id')
    def get_qty_package(self):
        if self.product_uom_qty and self.product_id.piece > 0:
            product_peice = self.product_id.piece
            self.qty_package = self.product_uom_qty / product_peice

    @api.one
    def getsubWithoutDisc(self):
        self.subtotal_wd=self.product_uom_qty*self.price_unit


    def get_domain(self):
        domain=[]
        if self.company:
            domain.append(('company.name','ilike',self.company))
        if self.en_name:
            domain.append(('english_name','ilike',self.en_name ))
        if self.ar_name :
            domain.append(('arabic_name','ilike',self.ar_name ))
        if self.veriant:
            domain.append( ('variant','ilike',self.veriant ))
        if self.size:
            domain.append(('size','ilike',self.size))

        return domain

    @api.onchange('company','en_name','ar_name','veriant','size')
    def filter_product(self):
        ids=self.product_id.search(self.get_domain()).mapped('id')

        return {
            'domain':{
                'product_id':[('id','in',ids)]
            }
        }
