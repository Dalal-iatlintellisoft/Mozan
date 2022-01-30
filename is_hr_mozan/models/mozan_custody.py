# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Custody(models.Model):
    _name = 'custody'
    _inherit = ['mail.thread']
    name = fields.Many2one('hr.employee', string='Employee Name', default=lambda self: self.env.uid, required=True)
    request_date = fields.Date(string='Date', required=True)

    custody_line_ids = fields.One2many('custody.line', 'custody_id', string='Custody Line', required=True)
    state = fields.Selection([('draft', 'To Submit'), ('sent', 'To Confirm By Hr'), ('confirm', 'Confirm By Hr'),
                              ('approve', 'Approved By Accounting'), ('receive_custody_hr', 'Custody Received'),
                              ('receive_custody_account', 'Done')], string='State', default='draft')

    @api.one
    def send_to_hr(self):
        self.state = 'sent'

    @api.one
    def hr_confirm(self):
        self.state = 'confirm'

    @api.one
    def account_confirm(self):
        self.state = 'approve'

    @api.one
    def hr_custody_receive(self):
        self.state = 'receive_custody_hr'

    @api.one
    def account_custody_receive(self):
        self.state = 'receive_custody_account'


class CustodyLine(models.Model):
    _name = 'custody.line'
    name = fields.Many2one('custody.item', string='Custody Item')
    custody_no = fields.Char('Custody Number', related='name.custody_no')
    custody_received_date = fields.Datetime(string='Custody Received Date')
    custody_delivery_date = fields.Datetime(string='Custody Delivery Date')
    note = fields.Char(string='Note')
    custody_id = fields.Many2one('custody', string='Custody Line', ondelete='cascade')


class CustodyItem(models.Model):
    _name = 'custody.item'
    name = fields.Char(string='Name')
    custody_no = fields.Char(string='Number')


class CustodyRequest(models.Model):
    _name = 'custody.request'

    name = fields.Many2one('hr.employee', string='name')
    department_id = fields.Many2one('hr.department', related='name.department_id')
    date_request = fields.Datetime(string='Date Request')
    custody_line_ids = fields.One2many('custody.line.request', 'custody_id', string='Custody Line')
    state = fields.Selection([('draft', 'To Submit'), ('sent', 'To Confirm By Hr'), ('confirm', 'Confirm By Hr'),
                              ('approve', 'Approved By Accounting')], string='State', default='draft')
    @api.one
    def send_to_hr(self):
        self.state = 'sent'

    @api.one
    def hr_confirm(self):
        self.state = 'confirm'

    @api.one
    def account_confirm(self):
        self.state = 'approve'


class CustodyLineRequest(models.Model):
    _name = 'custody.line.request'

    name = fields.Many2one('custody.item', string='Custody Item')
    note = fields.Char(string='Note')
    custody_id = fields.Many2one('custody.request', string='Custody Line', ondelete='cascade')
