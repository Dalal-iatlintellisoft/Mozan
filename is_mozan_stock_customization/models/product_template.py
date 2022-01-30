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


class StockValuationAdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    lot_name = fields.Many2one('stock.production.lot','Lot',compute='get_product_lot')

    @api.one
    def get_product_lot(self):
        lines = []
        for move in self.env['stock.landed.cost'].mapped('picking_ids').mapped('move_lines'):
            move_line_ids = move.move_line_ids
            for line in move_line_ids:
                self.lot_name = line.lot_id.name
                vals = {
                    'lot_name': line.lot_id.name,
                }
                lines.append(vals)
            return lines


class ProductCategory(models.Model):
    _inherit = 'product.category'

    value_usd = fields.Float('VALUE (USD)')
    precentage = fields.Integer('Percentage')
    product_log_category_ids = fields.One2many('product.log.category','product_category_id','Products Categories')
    value_usd = fields.Float('VALUE (USD)')
    sea_fright = fields.Float('SEA FREIGHT')
    custom_usd = fields.Float('CUSTOM USD')
    black_market = fields.Float('B.M USD')
    container = fields.Float('container v (m3)')
    health = fields.Float('HEALTH')
    ssmt = fields.Float('SSMT')
    clearance = fields.Float('CLEARANCE')
    inter_transfer = fields.Float('INT. TRANS')
    profit = fields.Integer('EXPECTED PROFIT')
    precentage = fields.Integer('Precentage')
    vat = fields.Integer('V.A.T')
    bpt = fields.Integer('B.P.T')
    bdt = fields.Integer('B.D.T')


class ProductLogCategory(models.Model):
    _name = 'product.log.category'

    date = fields.Date('Date')
    product_category_id = fields.Many2one('product.category','Product Category')
    product_id = fields.Many2one('product.product', 'Product')
    virtual_cost = fields.Float('Virtual Cost',)
    actual_cost = fields.Float('Actual Cost')
    sale_cost = fields.Float('Sales Cost')
    name = fields.Char('Name')


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _name = 'product.template'

    name = fields.Char(string="Name", store = True)
    company = fields.Many2one('log.company', string="Company")
    english_name = fields.Char(string="English Name")
    variant = fields.Char(string="Variant")
    size = fields.Char('Size')
    arabic_name = fields.Char(string="Arabic Name")
    package = fields.Float('Package Per Carton')
    piece = fields.Float('Piece Per Package')
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], string="Tracking", default='lot')
    virtual_cost = fields.Float('Virtual Cost')
    actual_cost = fields.Float('Actual Cost')
    sale_cost = fields.Float('Sale Cost')
    standard_price = fields.Float(
        'Cost', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help="Cost used for stock valuation in standard price and as a first price to set in average/fifo. "
             "Also used as a base price for pricelists. "
             "Expressed in the default unit of measure of the product. ")


class LogCompany(models.Model):
    _name = 'log.company'

    name = fields.Char(string="Company")


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = 'stock.move'

    qty_package = fields.Float(string="Qty Package" ,compute='get_qty_package')

    @api.one
    @api.depends('product_id')
    def get_qty_package(self):
        if self.quantity_done and self.product_id.piece > 0:
            product_peice = self.product_id.piece 
            self.qty_package = self.quantity_done/product_peice


class ProductProduct(models.Model):
    _inherit = "product.product"


    @api.one
    @api.depends('weight','volume')
    def get_weight_volume(self):
        qty = self.piece * self.package
        if self.weight and qty > 0:
            self.weight_pcs = self.weight/qty
        if self.volume and qty > 0:
                self.volume_pcs = self.volume / qty
    
    @api.onchange( 'company','english_name','variant','size','arabic_name')
    def get_ar_en(self):
        if self.landed_cost_ok == False:
            if self.variant_ok == True:
                self.name = (self.company and self.company.name or ' ') + ' ' +(self.english_name  and self.english_name or ' ') +' ' + (self.variant and self.variant or ' ')+' ' +(self.size and self.size or ' ' )+' ' +(self.arabic_name and self.arabic_name or ' ')
            else:
                name = ' '
                self.name = (self.company and self.company.name or ' ') +' '+(self.english_name and self.english_name or ' ')+' '+(self.size and self.size or ' ')+'  '+ (self.arabic_name and self.arabic_name or ' ')


   # name = fields.Char('Product Name',compute = 'get_ar_en',store=True,readonly = False)
    company = fields.Many2one('log.company',string="Company")
    currency_usd_id = fields.Many2one('res.currency',string="USD",compute='_compute_currency_usd_id')
    english_name = fields.Char(string="English Name")
    variant = fields.Char(string="Variant")
    size = fields.Char('Size',)
    arabic_name = fields.Char(string="Arabic Name" )
    package = fields.Float('Package Per Carton',digits=(12,0))
    piece = fields.Float( 'Peice Per Package',digits=(12,0))
    weight = fields.Float('Weight',digits=(12,8))
    volume = fields.Float('Volume',digits=(12,8))
    weight_pcs = fields.Float('Weight(pcs)', digits=(12, 8),compute='get_weight_volume')
    volume_pcs = fields.Float('Volume(pcs)', digits=(12, 8),compute='get_weight_volume')
    customer_sale = fields.Float('suggested Sale Price')
    package_price = fields.Float('Package Price')
    cost_dollar = fields.Float('Carton Cost')
    variant_ok = fields.Boolean('Has a Variant',default=True)
    invoice_policy = fields.Selection(
        [('order', 'Ordered quantities'),
         ('delivery', 'Delivered quantities'),
         ], string='Invoicing Policy',
        help='Ordered Quantity: Invoice based on the quantity the customer ordered.\n'
             'Delivered Quantity: Invoiced based on the quantity the vendor delivered (time or deliveries).',
        default='delivery')
    purchase_method = fields.Selection(
        [('order', 'Ordered quantities'),
         ('delivery', 'Delivered quantities'),
         ], string='Invoicing Policy',
        help='Ordered Quantity: Invoice based on the quantity the customer ordered.\n'
             'Delivered Quantity: Invoiced based on the quantity the vendor delivered (time or deliveries).',
        default='order')
    virtual_cost = fields.Float('Virtual Cost')
    actual_cost = fields.Float('Actual Cost')
    sale_cost = fields.Float('Sale Cost')
    lot_ids = fields.One2many('stock.production.lot', 'product_id', 'Lots', domain=[('lot_trigger', '=', 0.0)])

 

    @api.multi
    def _compute_currency_usd_id(self):
        main_company = self.env['res.currency'].search([('name', '=', 'USD')], limit=1, order="id")
        for template in self:
            template.currency_usd_id = main_company.id


class Orderpoint(models.Model):
    _name = "stock.warehouse.orderpoint"
    _inherit = ['stock.warehouse.orderpoint','mail.thread', 'mail.activity.mixin']

    carton_min_qty = fields.Float('Minimum Carton Quantity')
    flag = fields.Boolean('Flag')

    @api.onchange('carton_min_qty')
    def _compute_peice_quantity(self):
        if self.carton_min_qty:
            self.product_min_qty = self.carton_min_qty * self.product_id.package * self.product_id.piece

    @api.constrains('product_min_qty')
    def qty_minimum_alarm(self):
        for rec in self:
            product_qty = rec.product_id.qty_available
            if rec.flag == False:
                if rec.product_min_qty <= product_qty:
                    manager_group_id = self.env['res.groups'].search([('name', 'like', 'Stock Manager')], limit=1).id
                    activity = self.env['mail.activity.type'].search([('name', 'like', 'Stock Manager')], limit=1)
                    self.env.cr.execute(
                        '''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (manager_group_id))
                    for mg in self.env.cr.fetchall():
                        vals = {
                            'activity_type_id': activity.id,
                            'res_id': self.id,
                            'res_model_id': self.env['ir.model'].search([('model', 'like', 'stock.warehouse.orderpoint')],
                                                                        limit=1).id,
                            'user_id': mg[0] or 1,
                            'summary':'The Product reached the minimum quantity',
                        }
                    # add lines
                    self.env['mail.activity'].create(vals)
                    self.flag = True


class ProductionLot(models.Model):
    _name = 'stock.production.lot'
    _inherit = ['stock.production.lot','mail.thread', 'mail.activity.mixin']

    lot_trigger = fields.Float('Lot Trigger',compute = '_compute_lot_domain',store=True)
    flag = fields.Boolean('Flag')
    product_qty = fields.Float('Quantity', compute='_product_qty',store=True)

    @api.onchange('life_date')
    def compute_lot_colorize(self):
        product_lot_ids = self.search([])
        for rec in product_lot_ids:
            if not rec.life_date:
                rec.life_date = datetime.strptime(fields.Datetime.now(), '%Y-%m-%d %H:%M:%S')
            today = datetime.strptime(fields.Datetime.now(), '%Y-%m-%d %H:%M:%S')
            current_date = datetime.strptime(str(rec.life_date), '%Y-%m-%d %H:%M:%S')
            days = (today - current_date).days
            if days >= 0:
                rec.flag = True
            else:
                rec.flag = False

    @api.one
    @api.depends('name','product_qty')
    def _compute_lot_domain(self):
        for rec in self:
            print(rec.product_qty)
            product_qty = rec.product_qty
            if product_qty == 0.0:
                rec.lot_trigger = 1.0
                print(rec.lot_trigger)

class ProductCosting(models.Model):
    _name = 'product.costing'
    _inherit = ['mail.thread']

    # @api.onchange('currency_id')
    # def get_currency_rate(self):
    #     for rec in self:
    #         rec.black_market = rec.currency_id.inv_rate

    name = fields.Char('Name',readonly = True)
    date = fields.Date('Date', default=fields.Date.context_today)
    product_category_ids = fields.Many2many('product.category', 'product_actual_category_rel','cost_id','category_id', string = 'Categories',required = True)
    picking_id = fields.Many2one('stock.picking','Picking Number')
    value_usd = fields.Float('VALUE (USD)')
    sea_fright = fields.Float('SEA FREIGHT')
    custom_usd = fields.Float('CUSTOM USD')
    black_market = fields.Float('B.M USD')
    container = fields.Float('container v (m3)')
    health = fields.Float('HEALTH')
    ssmt = fields.Float('SSMT')
    clearance = fields.Float('CLEARANCE')
    inter_transfer = fields.Float('INT. TRANS')
    profit = fields.Integer('EXPECTED PROFIT')
    precentage = fields.Integer('Precentage')
    vat = fields.Integer('V.A.T')
    bpt = fields.Integer('B.P.T')
    bdt = fields.Integer('B.D.T')
    currency_id = fields.Many2one('res.currency', 'Currency',required =True)
    flag = fields.Boolean('Flag')


    @api.model
    def create(self, vals):
        res = super(ProductCosting, self).create(vals)
        next_seq = self.env['ir.sequence'].get('product.cost.no')
        res.update({'name': next_seq})
        return res

    @api.multi
    def compute_virtual_cost(self):
        pass
        for record in self:
            sea_fright = record.sea_fright
            custom_usd = record.custom_usd
            black_market = record.currency_id.inv_rate
            current_date = record.currency_id.date
            actual_black_market = record.black_market
            container = record.container
            health = record.health
            ssmt = record.ssmt
            clearance = record.clearance
            inter_transfer = record.inter_transfer
            profit = record.profit / 100
            vat = record.vat / 100
            bpt = record.bpt / 100
            bdt = record.bdt / 100
            if len(record.product_category_ids) != 0:
                for product in self.env['product.product'].search(
                        [('product_tmpl_id.categ_id', '=', record.product_category_ids._ids)]):
                    print('****************************',product.name,product.categ_id.name,record.product_category_ids._ids)
                    volume = product.volume
                    weight = product.weight
                    piece = product.piece
                    package = product.package
                    lst_price = product.lst_price
                    value_usd = product.product_tmpl_id.categ_id.value_usd
                    precentage = product.product_tmpl_id.categ_id.precentage / 100
                    if container * sea_fright > 0:
                        carton_cost_usd = product.cost_dollar
                        carton_sea_fright = volume / container * sea_fright
                        carton_custom_price_usd = weight * value_usd / 1000
                        carton_custom_price_sdg = carton_custom_price_usd * custom_usd
                        carton_custom_value = carton_custom_price_sdg * precentage
                        carton_bpt = carton_custom_price_sdg * bpt
                        carton_bdt = carton_custom_price_sdg * bdt
                        carton_vat = (carton_custom_price_sdg + carton_custom_value + carton_bdt) * vat
                        carton_health = volume / container * health
                        carton_ssmt = volume / container * ssmt
                        carton_clearance = volume / container * clearance
                        carton_int_transfer = volume / container * inter_transfer
                        sub_total = carton_cost_usd + carton_sea_fright
                        total1 = sub_total * black_market
                        actual_total1 = sub_total * actual_black_market
                        remain = carton_custom_value + carton_bpt + carton_bdt + carton_vat + carton_health + carton_ssmt + carton_clearance + carton_int_transfer
                        total = total1 + remain
                        actual_total = actual_total1 + remain
                        carton_profit = total * profit
                        actual_carton_profit = actual_total * profit
                        carton_final_vat = ((total + carton_profit) * vat) - carton_vat
                        actual_carton_final_vat = ((actual_total + actual_carton_profit) * vat) - carton_vat
                        carton_virtual_cost = total + carton_final_vat
                        carton_actual_cost = actual_total + actual_carton_final_vat
                        # carton_actual_cost = total1 + carton_custom_value + carton_bpt + carton_bdt + carton_vat + carton_health + carton_ssmt + carton_clearance + carton_int_transfer
                        print('++++++++++++++++++++++++++++++++++++++', carton_actual_cost)
                        if piece > 0:
                            peice_virtual_cost = carton_virtual_cost / piece
                            product.virtual_cost = peice_virtual_cost
                            product.sale_cost = lst_price / 1.2
                            peice_actual_cost = carton_actual_cost / piece
                            # print('*****************************', peice_actual_cost)
                            product.actual_cost = peice_actual_cost
                            # print(peice_actual_cost)
                            product_log_vals = {
                                'date': current_date,
                                'virtual_cost': product.virtual_cost,
                                'actual_cost': product.actual_cost,
                                'sale_cost':   product.sale_cost,
                                'product_id': product.id,
                                'name':product.name,
                                'product_category_id': product.product_tmpl_id.categ_id.id,
                            }
                            self.env['product.log.category'].create(product_log_vals)

    @api.multi
    def compute_actual_cost(self):
        for record in self:
            sea_fright = record.sea_fright
            custom_usd = record.custom_usd
            black_market = record.black_market
            virtual_black_market = record.currency_id.inv_rate
            container = record.container
            health = record.health
            ssmt = record.ssmt
            clearance = record.clearance
            inter_transfer = record.inter_transfer
            profit = record.profit / 100
            vat = record.vat / 100
            bpt = record.bpt / 100
            bdt = record.bdt / 100
            if len(record.product_category_ids) != 0:
                # for rec in record.product_category_ids:
                for product in self.env['product.product'].search(
                        [('product_tmpl_id.categ_id', '=', record.product_category_ids._ids)]):
                    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%',product)
                    volume = product.volume
                    weight = product.weight
                    piece = product.piece
                    package = product.package
                    lst_price = product.lst_price
                    value_usd = product.product_tmpl_id.categ_id.value_usd
                    precentage = product.product_tmpl_id.categ_id.precentage / 100
                    if container * sea_fright > 0:
                        carton_cost_usd = product.cost_dollar
                        carton_sea_fright = volume / container * sea_fright
                        carton_custom_price_usd = weight * value_usd / 1000
                        carton_custom_price_sdg = carton_custom_price_usd * custom_usd
                        carton_custom_value = carton_custom_price_sdg * precentage
                        carton_bpt = carton_custom_price_sdg * bpt
                        carton_bdt = carton_custom_price_sdg * bdt
                        carton_vat = (carton_custom_price_sdg + carton_custom_value + carton_bdt) * vat
                        carton_health = volume / container * health
                        carton_ssmt = volume / container * ssmt
                        carton_clearance = volume / container * clearance
                        carton_int_transfer = volume / container * inter_transfer
                        sub_total = carton_cost_usd + carton_sea_fright
                        total1 = sub_total * black_market
                        virtual_total1 = sub_total * virtual_black_market
                        remain = carton_custom_value + carton_bpt + carton_bdt + carton_vat + carton_health + carton_ssmt + carton_clearance + carton_int_transfer
                        total = total1 + remain
                        virtual_total = virtual_total1 + remain
                        virtual_carton_profit = virtual_total * profit
                        carton_profit = total * profit
                        carton_final_vat = ((total + carton_profit) * vat) - carton_vat
                        virtual_carton_final_vat = ((virtual_total + virtual_carton_profit) * vat) - carton_vat
                        carton_virtual_cost = virtual_total1 + carton_custom_value + carton_bpt + carton_bdt + carton_vat + carton_health + carton_ssmt + carton_clearance + carton_int_transfer
                        carton_actual_cost = total1 + carton_custom_value + carton_bpt + carton_bdt + carton_vat + carton_health + carton_ssmt + carton_clearance + carton_int_transfer
                        if piece > 0:
                            peice_virtual_cost = (carton_virtual_cost + virtual_carton_final_vat) / piece
                            product.virtual_cost = peice_virtual_cost
                            product.sale_cost = lst_price / 1.2
                            peice_actual_cost = (carton_actual_cost + carton_final_vat) / piece
                            product.actual_cost = peice_actual_cost
                            product_log_vals = {
                                'date': record.date,
                                'actual_cost': product.actual_cost,
                                'virtual_cost': product.virtual_cost,
                                'sale_cost' :   product.sale_cost,
                                'product_id': product.id,
                                'name': product.name,
                                'product_category_id' : product.product_tmpl_id.categ_id.id,
                            }
                            self.env['product.log.category'].create(product_log_vals)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    inv_rate = fields.Float('Inverse Rate',compute = 'get_inverse_rate')
    date = fields.Date('Current Date',)

    @api.one
    @api.depends('rate')
    def get_inverse_rate(self):
        if self.rate != 0.0:
            self.inv_rate =1/self.rate
            currency_rate_obj = self.env['res.currency.rate'].search([('currency_id','=',self.id)] , order = 'name desc',limit = 1)
            self.date = currency_rate_obj.name


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    @api.model
    def create(self, vals):
        self.env['product.costing'].search([]).compute_virtual_cost()
        res = super(ResCurrencyRate ,self).create(vals)
        return res

