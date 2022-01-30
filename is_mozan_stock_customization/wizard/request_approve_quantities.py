# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class request_approve_quantities(models.TransientModel):
    _name = 'request.approve.quantities'
    _description = 'Approve Quantities'

    lins_ids = fields.Many2many('material.request', 'material_request_rel')

    def process(self):
        for picking in self.lins_ids:
            for move in picking.request_lines:
                    move.product_qty = move.ordered_qty

