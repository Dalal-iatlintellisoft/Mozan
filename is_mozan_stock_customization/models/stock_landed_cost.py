# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.addons.stock_landed_costs.models import product
from odoo.exceptions import UserError


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'
    _description = 'Customize Stock Landed Cost for volume by peice'

    rate = fields.Float('Rate', compute='_compute_inverse_rate')
    inverse_rate = fields.Float('Inverse Rate')

    @api.depends('inverse_rate')
    def _compute_inverse_rate(self):
        if self.inverse_rate:
            if self.inverse_rate <= 0.00:
                raise UserError('Can not divide Zero Amount')
            else:
                self.rate = 1/self.inverse_rate

    def get_valuation_lines(self):

        lines = []

        for move in self.mapped('picking_ids').mapped('move_lines'):
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.valuation != 'real_time' or move.product_id.cost_method != 'fifo':
                continue
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': move.value / self.rate,
                'weight': move.product_id.weight_pcs * move.product_qty,
                'volume': move.product_id.volume_pcs * move.product_qty
            }
            lines.append(vals)
        if not lines and self.mapped('picking_ids'):
            raise UserError(_('The selected picking does not contain any move that would be impacted by landed costs. Landed costs are only possible for products configured in real time valuation with real price costing method. Please make sure it is the case, or you selected the correct picking'))
        return lines


