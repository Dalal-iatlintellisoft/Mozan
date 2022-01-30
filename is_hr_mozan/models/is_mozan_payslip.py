from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
import math
import babel
import time
from odoo import tools

class MozanPayslip(models.Model):
    _inherit = "hr.payslip"
    rate = fields.Float("rate")
    bank_acct_num = fields.Char("Bank Account Number")
    # deductions
    personal_loan = fields.Float("Personal Loan", readonly=True, compute='get_loan', store=True)
    short_loan = fields.Float("Monthly Loan", readonly=True, compute='get_short_loan', store=True)
    net_salary = fields.Float("Net Salary", compute='get_net_salary', store=True)
    penalties_deduction = fields.Float("Penalty",readonly=True, compute='get_penalty', store=True)
    unpaid_leave = fields.Float("Unpaid Leave", readonly=True, compute='compute_unpaid', store=True)

    other_deduction = fields.Float( string = 'Other Deduction')
    taxs = fields.Float( string = 'Taxes')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                    \n* If the payslip is confirmed by hr, the status is \'Confirmed\'.
                    \n* If the payslip is under verification, the status is \'Waiting\'.
                    \n* If the payslip is confirmed by account then status is set to \'Done\'.
                    \n* When user cancel payslip the status is \'Rejected\'.""")

    @api.depends('employee_id', 'line_ids')
    def get_net_salary(self):
        for rec in self:
            net = 0.00
            total = 0.00
            if rec.line_ids and rec.employee_id:
                    payslip_line_ids = rec.env['hr.payslip.line'].search([('employee_id', '=', rec.employee_id.id),
                                                                          ('code', '=', 'NET'),
                                                                          ('slip_id', '=', rec.id)])
                    print('%55555555%%%%%%%%%%%%%%%',rec.employee_id.name)

                    for slip in payslip_line_ids:
                        total = slip.total
            rec.net_salary = total

    api.model
    def compute_sheet(self):
        res = super(MozanPayslip, self).compute_sheet()
        for rec in self:
            if rec.date_to:
                ttyme = datetime.fromtimestamp(time.mktime(time.strptime(str(rec.date_to), "%Y-%m-%d")))
                locale = self.env.context.get('lang', 'en_US')
                month = tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM', locale=locale))
                print('#################',month.islower())
                month = month.lower()
                print(month)
                change_bonus_ids = rec.env['change.bonus'].search([('name', '=', month)],limit=1)
                if change_bonus_ids:
                    print('#################', change_bonus_ids)
                    for record in rec.line_ids:
                        if record.code == 'incen':
                            record.amount = record.amount + change_bonus_ids.amount
                            record.total = record.amount

        return res

    @api.multi
    def action_hr_confirm(self):
        for rec in self:
            rec.compute_sheet()
            rec.state = 'confirm'

    @api.depends('employee_id')
    def get_loan(self):
        for rec in self:
            employee_ids =  self.env['hr.loan'].search(
               [ ('employee_id', '=', rec.employee_id.id)])
            for x in employee_ids:
                if x.employee_id:
                    loan_ids = self.env['hr.loan.line'].search(
                        [('loan_id', '=', x.id), ('paid', '=', False), ('paid_date', '>=', rec.date_from),
                         ('paid_date', '<=', rec.date_to)])

                    for loan_id in loan_ids:
                        if loan_id.loan_id.state == 'done':
                            rec.personal_loan += loan_id.paid_amount



    @api.depends('employee_id')
    def get_short_loan(self):
        amount = 0.00
        for x in self:
            if x.employee_id:
                loan_ids = self.env['hr.monthlyloan'].search
        loan_ids = self.env['hr.monthlyloan'].search([('employee_id', '=', self.employee_id.id),('state', '=', 'done'), ('date', '>=', self.date_from),('date', '<=', self.date_to)])
        for loan in loan_ids:
            amount += loan.loan_amount
            self.short_loan = amount


    @api.multi
    def action_payslip_done(self):
        for payslip in self:
            if payslip.employee_id:
                payslip_obj = payslip.search(
                    [('employee_id', '=', payslip.employee_id.id), ('name', '=', payslip.name), ('state', '=', 'done')])
                if payslip_obj:
                    raise Warning(_("This Employee Already Took This Month's Salary!"))
            loan_ids = payslip.env['hr.loan.line'].search(
                [('employee_id', '=', payslip.employee_id.id), ('paid', '=', False)])
            for line in loan_ids:
                if line.paid_date >= payslip.date_from and line.paid_date <= payslip.date_to and line.loan_id.state == "done":
                    if not line.paid:
                        line.payroll_id = payslip.id
                        line.action_paid_amount()
                else:
                    line.payroll_id = False

            short_loan_ids = payslip.env['hr.monthlyloan'].search(
                [('state', '=', 'done'),
                 ('date', '>=', payslip.date),
                 ('date', '<=', payslip.date_to)])
            for rec in short_loan_ids:
                employee_ids = self.env['employee.loan'].search(
                    [('employee_id', '=', self.employee_id.id)])
                for short_loan in short_loan_ids:
                    short_loan.action_paid()

        return super(MozanPayslip, self).action_payslip_done()

    @api.constrains('name')
    def _no_duplicate_payslips(self):
        if self.employee_id:
            payslip_obj = self.search([('employee_id', '=', self.employee_id.id), ('name', '=', self.name),
                                       ('state', '=', 'done')])
            if payslip_obj:
                raise Warning(_("This Employee Already Took his Month's Salary!"))


class MozanHrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    @api.multi
    def close_payslip_run(self):
        for slip in self:
            for slip_run in slip.slip_ids:
                slip_run.action_payslip_done()
        return super(MozanHrPayslipRun, self).close_payslip_run()

    @api.multi
    def action_hr_confirm(self):
        for slip in self:
            slip.state = 'confirm'
            for slip_run in slip.slip_ids:
                slip_run.action_hr_confirm()

    @api.depends('employee_id', 'date_from', 'date_to')
    def get_penalty(self):
        for pen in self:
            if pen.employee_id:
                amount = 0.00
                warning_ids = self.env['hr.warnings'].search(
                    [('employee_id', '=', pen.employee_id.id), ('warning_penalty_mon', '>', 0.00),
                     ('pen_type', '=', 'deduction'), ('state', '=', 'penalty_approval'),
                     ('warning_date', '>=', pen.date_from),
                     ('warning_date', '<=', pen.date_to)])
                if warning_ids:
                    for warning in warning_ids:
                        amount += warning.warning_penalty_mon

                pen.penalties_deduction = amount

    @api.depends('employee_id')
    def compute_unpaid(self):
        for x in self:
            if x.worked_days_line_ids:
                unpaid_sum = 0
                for worked_ids in x.worked_days_line_ids:
                    if worked_ids.code == 'Unpaid':
                        unpaid_sum += worked_ids.number_of_days
                employee_salary = x.employee_id.contract_id.wage
                total_upaid_salary = employee_salary * unpaid_sum / 30
                x.unpaid_leave = total_upaid_salary

class ChangeBonus(models.Model):
    _name = 'change.bonus'
    # _rec_name ='month'


    name = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('november', 'November'),
    ], string='Month')
    amount = fields.Float('Amount')


