from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import math
from odoo.tools.float_utils import float_compare, float_round, float_is_zero



class hr_holidays(models.Model):
    _inherit = "hr.holidays"

    leave_balance = fields.Float(string='Legal Leave', related="employee_id.leave_balance")
    balance = fields.Float(string='Leave Balance', compute='_compute_leave_balance')
    visa_required = fields.Boolean ('visa')
    country_visited = fields.Char( 'Country to be visited ')
    period_stay= fields.Integer('Period of stay')

    @api.depends('number_of_days_temp')
    def _compute_leave_balance(self):
        for leave in self:
            if leave.number_of_days_temp:
                self.balance = leave.leave_balance - leave.number_of_days_temp

class exit_permission(models.Model):
    _name = 'exit.permission'
    name = fields.Char(string="Name ")
    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)


    employee_id = fields.Many2one('hr.employee', string='Employee')
    date_form = fields.Datetime(string="From Date", required=True , default=fields.Date.today())
    date_to = fields.Datetime(string="To Date", required=True)
    total_second = fields.Char('Number of Days', compute='_compute_number_of_days',  readonly=True)
    number_of_days = fields.Char('Number of Days', compute='_compute_number_of_days',  readonly=True,
                                 translate=True)

    notes = fields.Text( string ='Notes')
        # [('draft', 'To Submit'),
    state = fields.Selection([('draft', 'To Submit'), ('confirm', 'Submitted'), ('refuse', 'Refused'),
                              ('approve', 'Approve'), ('penalty_approval', 'Done')],
                             'Status', readonly=True, track_visibility='onchange', copy=False,
                             help='The status is set to \'To Submit\', when a Warring request is created.\
                          \nThe status is \'To Approve\', when Warring request is confirmed by user.\
                          \nThe status is \'Refused\', when Warring request is refused by manager.\
                          \nThe status is \'Approved\', when Warring request is approved by manager.', default="draft")
    @api.multi
    @api.depends('date_form', 'date_to')
    def _compute_number_of_days(self):
        for day in self:
            if day.date_to and day.date_form:
                if day.date_form < day.date_to:
                    from_dt = fields.Datetime.from_string(day.date_form)
                    to_dt = fields.Datetime.from_string(day.date_to)
                    day.number_of_days = to_dt - from_dt
                    day.total_second = (to_dt - from_dt).total_seconds()/60
                if day.date_form > day.date_to:
                    raise UserError(_('The Start Date muest be Less Than End Date!'))



    @api.one
    def confirm(self):
        self.state = 'confirm'
    @api.one
    def approve(self):
        if self.state =='confirm':
          y = self._cr.execute("UPDATE hr_employee set local_remaining_leaves=%s"
                               " WHERE id=%s",(self.total_second,  self.employee_id.id))
          self.state = 'approve'

