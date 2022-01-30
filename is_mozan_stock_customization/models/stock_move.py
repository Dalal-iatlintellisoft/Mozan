# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta
from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class StockMove(models.Model):
    _inherit = "stock.move"


    subtotal = fields.Float('Subtotal',compute='_compute_subtotal', store=True, translate=True)
    remain_qty = fields.Float('Remain Custody',compute='_compute_remain_qty', store=True, translate=True)
    previous_picking = fields.Char('Previous Movement',compute='_compute_previous_qty', store=True, translate=True)
    last_out = fields.Float('Last Out',compute='_compute_last_out', store=True, translate=True)
    matching = fields.Boolean('Inspection Resolution', readonly=True, translate=True)

    # show_details_visible = fields.Boolean('Details Visible', compute='_compute_show_details_visible')
    # is_locked = fields.Boolean(compute='_compute_is_locked', readonly=True)

    @api.depends('price_unit','product_id','product_qty','quantity_done')
    def _compute_subtotal(self):
        for x in self :
            x.subtotal = x.price_unit * x.product_qty

    @api.multi
    @api.depends('picking_type_id.code','product_id')
    def _compute_remain_qty(self):
        for y in self:
            y.remain_qty = y.product_id.qty_available

            # if y.picking_type_id.code == 'incoming':
            #     location = y.picking_id.location_dest_id.id
            #     y.remain_qty = self.env['stock.quant']._get_available_quantity(y.product_id, location)
            #
            # if y.picking_type_id.code == 'outgoing':
            #     location = y.picking_id.location_id.id
            #     y.remain_qty = self.env['stock.quant']._get_available_quantity(y.product_id, location)

    @api.multi
    @api.depends('product_id')
    def _compute_previous_qty(self):
        for c in self:
            pick = self.env['stock.move'].search([('product_id', '=', c.product_id.id), ('state', '=', 'done')], order='date desc', limit=1)
            for x in pick:
                c.previous_picking = x.picking_id.name


    @api.multi
    @api.depends('product_id')
    def _compute_last_out(self):
        for e in self:
            pick = self.env['stock.move'].search([('product_id', '=',e.product_id.id),('picking_type_id.code','=','outgoing'),('state', '=', 'done')], order='date desc', limit=1)
            for mov in pick:
                e.last_out = mov.product_qty

    @api.onchange('quantity_done')
    def onchange_quantity_done(self):
        for x in self :
            x.subtotal = x.price_unit * x.quantity_done




