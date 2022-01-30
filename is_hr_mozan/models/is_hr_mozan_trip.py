# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta
import time
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_compare
import math


class HrTrip(models.Model):
    _name = 'hr.trip'

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char( string ='Name' )
    employee_id = fields.Many2one('hr.employee', string="Leder", required=True)
    eng_ids = fields.One2many( 'hr.employee.trip','emp_trip_id' , string = 'Engineers')
    trip_start_date = fields.Datetime(string="Trip Date From")
    trip_end_date = fields.Datetime(string="Trip Date To")
    trip_dist = fields.Text(string='Trip Destination', required=True)
    no_of_days = fields.Float(string='No Of Days')
    note = fields.Text(string='Notes')
    trip_no = fields.Char(string='No')
    travel_means_id = fields.Many2one(  'travel.means', string ="Means of travel")
    # attachment_ids = fields.One2many('ir.attachment','errand_form_id', string ="treatment form")
    type = fields.Selection([
        ('internal','internal'),('external','external')
    ])
    total_amount= fields.Float( string = 'Total' , compute='compute_total_amount')



    debit_account = fields.Many2one('account.account', string="Debit  Account")
    credit_account = fields.Many2one('account.account', string="Credit Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one('account.move', string="Journal Entry")
    direct_manager_nots = fields.Text(string="Direct manager Nots")
    project_manager_nots = fields.Text(string="project manager Nots")
    genaral_manager_nots = fields.Text(string="genaral manager Nots")
    finance_manager_nots = fields.Text(string="Finance manager Nots")
    external_amount = fields.Float( string ='External Amount')
    state = fields.Selection(
        [('draft', 'To Submit'), ('sent', 'Sent'), ('confirm', ' confirm')
            , ('approve', 'approve'), ('done', 'Done'), ('end', 'End'), ('refuse', 'refuse')], 'Status', default='draft')

    @api.depends('eng_ids')
    def compute_total_amount(self):
        sum = 0
        if self.name:
            for record in self:
                for line in record.eng_ids:
                    sum += line.emp_amount
                    self.total_amount = sum

    @api.one
    def send_request(self):
        self.state = 'sent'

    @api.one
    def confirm_request(self):
        self.state = 'confirm'

    @api.one
    def approve_request(self):
        self.state = 'approve'


    @api.one
    def trip_refuse(self):
        self.state = 'refuse'

    @api.one
    def trip_reset(self):
        self.state = 'draft'



    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)
        if employee_id:
            time_delta = to_dt - from_dt
            return math.ceil(time_delta.days + float(time_delta.seconds) / 86400)
    @api.onchange('trip_start_date','trip_start_date')
    def _onchange_date_from(self):
        date_from = self.trip_start_date
        date_to = self.trip_end_date
        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.no_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.no_of_days = 0

    @api.onchange('trip_end_date')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        date_from = self.trip_start_date
        date_to = self.trip_end_date

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.no_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.no_of_days = 0

    @api.multi
    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda HrTrip: HrTrip.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete a Trip which is not draft or refused!'))
            return super(HrTrip, rec).unlink()


    @api.depends('no_of_days','type')
    def get_amount(self):
        for x in self:
            type = x.type
            per_diem =False
            if type == 'internal':
                amount = x.salary_day*x.no_of_days
            if type == 'external':
                amount = x.external_amount
                x.amount = amount

    @api.one
    def trip_account_done(self):
        for trip in self:
            precision = self.env['decimal.precision']
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            per_diem = 0.0
            trip_name = trip.name
            amount = trip.no_of_days*per_diem
            trip.amount = amount
            journal_id = trip.journal_id.id
            approve_date = fields.Date.today()
            debit_account = trip.debit_account.id
            credit_account = trip.debit_account.id
        move_dict = {
            'narration': trip_name,
            'ref': trip_name,
            'journal_id': journal_id,
            'date': approve_date,
        }
        debit_line = (0, 0, {
            'name': trip_name,
            'partner_id': False,
            'account_id': debit_account,
            'journal_id': journal_id,
            'date': approve_date,
            'debit': amount > 0.0 and amount or 0.0,
            'credit': amount < 0.0 and -amount or 0.0,
            'analytic_account_id': False,
            'tax_line_id': 0.0,
        })
        line_ids.append(debit_line)
        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
        credit_line = (0, 0, {
            'name': trip_name,
            'partner_id': False,
            'account_id': credit_account,
            'journal_id': journal_id,
            'date': approve_date,
            'debit': amount < 0.0 and -amount or 0.0,
            'credit': amount > 0.0 and amount or 0.0,
            'analytic_account_id': False,
            'tax_line_id': 0.0,
        })
        line_ids.append(credit_line)
        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
        move_dict['line_ids'] = line_ids
        move = self.env['account.move'].create(move_dict)
        trip.write({'move_id': move.id, 'date_approve': approve_date})
        move.post()
        trip.state = 'done'



class travel_means(models.Model):
    _name = 'travel.means'
    name = fields.Char( string ="Name",required=True)

class hr_employee_trip(models.Model):
    _name = 'hr.employee.trip'
    name = fields.Many2one('hr.employee', string="Employee", required=True)
    emp_trip_id = fields.Many2one('hr.trip', string =' employee')
    department_id = fields.Many2one('hr.department', readonly=True,
                                    string="Department")
    job_id = fields.Many2one('hr.job', readonly=True, string="Job Position")
    emp_salary = fields.Float(string="Employee Salary")
    emp_amount = fields.Float( string = 'Amount')



