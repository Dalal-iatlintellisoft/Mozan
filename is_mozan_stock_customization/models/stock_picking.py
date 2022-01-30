# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
import json
import time

from itertools import groupby
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from operator import itemgetter

class Picking(models.Model):
    _inherit = ['stock.picking']
    _description = "Transfer"

    project_name = fields.Char(string='Project Name', translate=True)
    project_code = fields.Char(string='Project Code', translate=True)
    locatin = fields.Char(String='Project Location', translate=True)
    date_order = fields.Datetime('Date of Order', copy=False, readonly=True)
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    request_id = fields.Char(string='Request Number',translate=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', ondelete='cascade',default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)],limit=1), translate=True)
    code = fields.Char('Warehouse Code', related='warehouse_id.code',store=True, translate=True)
    show_inspection = fields.Boolean('Inspection Resolution', readonly=True, translate=True)
    request_id = fields.Many2one('material.request', string='Material Request', copy=False,translate=True)


    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('waiting_inspection', 'Waiting Inspection'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")


    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        if not self.move_lines:
            self.state = 'draft'
        elif any(move.state == 'draft' for move in self.move_lines):  # TDE FIXME: should be all ?
            self.state = 'draft'
        elif all(move.state == 'cancel' for move in self.move_lines):
            self.state = 'cancel'
        elif all(move.state in ['cancel', 'done'] for move in self.move_lines):
            self.state = 'done'
        elif self.picking_type_code =='incoming' and not self.show_inspection:
            self.state = 'waiting_inspection'
        elif self.picking_type_code =='incoming' and self.show_inspection:
            self.state = 'assigned'
        else:
            relevant_move_state = self.move_lines._get_relevant_state_among_moves()
            if relevant_move_state == 'partially_available':
                self.state = 'assigned'
            else:
                self.state = relevant_move_state

