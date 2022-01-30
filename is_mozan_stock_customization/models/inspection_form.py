# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.addons import decimal_precision as dp


class inspection_order(models.Model):
    _name = "inspection.order"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Inspection Order"
    _order = 'id desc'

    name = fields.Char('Inspection Form Name', required=True, index=True, copy=False, translate=True)
    inspection_date = fields.Datetime('Inspection Date', required=True, index=True, copy=False,translate=True,default=fields.Datetime.now,)
    date_approve = fields.Datetime('Approval Date', readonly=1, index=True, copy=False,translate=True)
    order_id = fields.Many2one('stock.picking', string='Order Reference', index=True, required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True,related='order_id.partner_id',store=True, translate=True, track_visibility='always')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'confirm'),
        ('approve', 'Approve'),
        ('manager_approve', 'Manager Approve'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    inspection_lines = fields.One2many('product.inspection.line', 'inspection_id', string='Inspection Lines', states={'cancel': [('readonly', True)], 'manager_approve': [('readonly', True)]}, copy=True)
    notes = fields.Text('Terms and Conditions')

    @api.multi
    def get_product_inspection(self):
        if self.inspection_lines:
            self.inspection_lines.unlink()
        else:
            order_object = self.env['stock.move'].search([("picking_id", "=",self.order_id.id),('state','!=','done')])
            product_inspection = self.env ['product.inspection.line']
            for line in order_object:
                rec = product_inspection.create({
                    'product_id': line.product_id.id,
                    'order_qty': line.product_qty,
                    'specifications':'',
                    'ordered_quantities':'',
                    'damage':'',
                    'terms':'',
                    'inspection_id':self.id,
                })

    @api.multi
    def unlink(self):
        for inspection in self:
            if not inspection.state == 'cancel':
                raise UserError(_('In Order to Delete a Inspection Form, you must cancel it first.'))
        return super(inspection_order, self).unlink()

    @api.multi
    def button_draft(self):
        self.write({'state': 'draft'})
        return {}

    @api.multi
    def button_confirm(self):
        if not all(obj.inspection_lines for obj in self):
            raise UserError(_('You cannot confirm call because there is no product line,you must get product first'))
        self.write({'state': 'confirm'})
        return {}

    @api.multi
    def button_approve(self):
        self.write({'state': 'approve'})
        return {}

    @api.multi
    def button_manager_approve(self):
        date = datetime.now
        for product in self.inspection_lines:
            move_object = self.env['stock.move'].search([("picking_id", "=", self.order_id.id), (
                "product_id", "=", product.product_id.id), ("matching", "=", False)])

            if product.matched:
                matching = True

            if product.not_matched:
                matching = False

            if not product.not_matched and not product.matched:
                raise UserError(_('Unable to approve inspection without Inspection Resolution .'))


            if move_object:
                for mov in move_object:
                    self.env.cr.execute("""update stock_move set matching=%s where id=%s ;""", (matching, mov.id,))

        self.env.cr.execute("""update stock_picking set state=%s where id=%s ;""", ('assigned', self.order_id.id,))

        self.write({'state': 'manager_approve','date_approve':fields.Datetime.now()})
        return {}

    @api.multi
    def action_cancel(self):
        for order in self:
            if self.state == 'manager_approve':
                raise UserError(_('Unable to cancel inspection %s as some receptions have already been done.') % (order.name))

        self.write({'state': 'cancel'})


class product_inspection_line(models.Model):
    _name = "product.inspection.line"
    _description = "Product Inspection Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=True)
    order_qty= fields.Float('Purchase Order Quantity', digits=dp.get_precision('Product Unit of Measure'))
    incoming_qty = fields.Float('Incoming Quantities')
    inspection_id = fields.Many2one('inspection.order', string='Inspection Order', ondelete='cascade')
    matched = fields.Boolean('Matched and added to the Stock.',default=False)
    not_matched = fields.Boolean('Not matching the supplier is notified',default=False)
    specifications = fields.Text('Specifications required by purchase order', required=True)
    ordered_quantities = fields.Text('The quantities ordered by the purchase order', required=True)
    damage = fields.Text('Damage in Incoming Quantities', required=True)
    terms = fields.Text('Any other terms required by purchase order', required=True)
