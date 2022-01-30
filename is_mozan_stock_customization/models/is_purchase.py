# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Avinash Nk(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime, date
from odoo import models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    flag = fields.Boolean('Flag')


    @api.constrains('date_order')
    def purchase_expiry_alarm(self):
        manager_group_id = self.env.ref('purchase.group_purchase_manager').id
        for rec in self:
            if rec.date_order:
                today = datetime.strptime(fields.Datetime.now(), '%Y-%m-%d %H:%M:%S')
                date_order = datetime.strptime(rec.date_order, '%Y-%m-%d %H:%M:%S')
                days = (today - date_order).days
                if rec.flag == False and days <= 15 and rec.state == 'draft':
                    activity = self.env['mail.activity.type'].search([('name', 'like', 'Purchase Manager')],limit=1)
                    self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (manager_group_id))
                    for mg in self.env.cr.fetchall():
                        vals = {
                            'activity_type_id': activity.id,
                            'res_id': self.id,
                            'res_model_id': self.env['ir.model'].search([('model', 'like', 'purchase.order')], limit=1).id,
                            'user_id': mg[0] or 1,
                            'summary': 'The Purchase Order Number '+ rec.name + ' ' + str('will be expired soon')
                        }
                    self.env['mail.activity'].create(vals)
                    self.flag = True


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_package = fields.Float(string="Carton")

    @api.onchange('qty_package')
    def get_qty_package(self):
        if self.product_id.piece * self.product_id.package > 0:
            self.product_qty = self.product_id.piece * self.product_id.package *self.qty_package
            self.price_unit = self.product_id.cost_dollar / (self.product_id.piece * self.product_id.package)


    @api.onchange('product_qty')
    def get_qty_unit(self):
        if self.product_id.piece * self.product_id.package > 0 :
            self.qty_package=self.product_qty/(self.product_id.piece * self.product_id.package)
            self.price_unit = self.product_id.cost_dollar / (self.product_id.piece * self.product_id.package)



class stockmove(models.Model):

    _inherit = 'stock.move.line'

    qty_package = fields.Float(string="Carton")

    @api.onchange('qty_package')
    def get_qty_package(self):
        self.qty_done = self.product_id.piece * self.product_id.package * self.qty_package

    @api.onchange('qty_done')
    def get_qty_unit(self):
        if self.product_id.piece * self.product_id.package > 0:
            self.qty_package = self.qty_done / (self.product_id.piece * self.product_id.package)



