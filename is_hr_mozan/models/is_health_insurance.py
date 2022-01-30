from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class HrHealthInsurance(models.Model):
    _name = 'hr.health.insurance'
    _inherit = ['mail.thread']
    _description = "Health Insurance Request"

    name = fields.Char(string="Insurance Name", default="/", readonly=True)
    date = fields.Date(string="Date Request", default=fields.Date.today(), readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    # parent_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True, string="Department")
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position")
    ## Salary Details
    emp_salary = fields.Float(string="Salary", related ='employee_id.contract_id.wage')

    emp_account_id = fields.Many2one('account.account', string="Employee Account")
    treasury_account_id = fields.Many2one('account.account', string="Treasury Account")
    pay_account_id = fields.Many2one('account.account', string="Payment Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    insurance_amount = fields.Float(string="Insurance Amount", required=True)
    attach = fields.Binary("Attachments", help="here you can attach a file or a document to the record !!")
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_amount')
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_amount')
    installment_amount = fields.Float(string="Installment Amount")
    no_month = fields.Integer(string="No Of Month", default=12)
    payment_start_date = fields.Date(string="Start Date of Payment", required=True, default=fields.Date.today())
    insurance_line_ids = fields.One2many('hr.health.insurance.line', 'insurance_id', string="Insurance Line", index=True)
    entry_count = fields.Integer(string="Entry Count", compute='compute_entery_count')
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    state = fields.Selection(
        [('draft', 'To Submit'), ('send', 'Send'),('approve', 'Approve'),('refuse', 'Refuse'),
         ('refuse', 'Refused')],
        'Status', readonly=True, track_visibility='onchange', copy=False, default='draft')
    emp_app_id = fields.Many2one('res.users', string="Employee Approval By")


    @api.depends('installment_amount', 'insurance_amount')
    def _compute_months_from_installment(self):
        for loan in self:
            if loan.installment_amount:
                loan.no_month = loan.insurance_amount / loan.installment_amount

    @api.one
    def _compute_amount(self):
        total_paid_amount = 0.00
        for insurance in self:
            for line in insurance.insurance_line_ids:
                if line.paid:
                    total_paid_amount += line.paid_amount

            balance_amount = insurance.insurance_amount - total_paid_amount
            insurance.total_amount = insurance.insurance_amount
            insurance.balance_amount = balance_amount
            insurance.total_paid_amount = total_paid_amount


    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.insurance.req') or ' '
        res = super(HrHealthInsurance, self).create(values)
        return res

    @api.one
    def loan_refuse(self):
        for x in self:
            x.state = 'refuse'

    @api.one
    def loan_reset(self):
        for x in self:
            x.state = 'draft'


    @api.one
    def send(self):
        for x in self:
            x.state = 'send'





    @api.one
    @api.onchange('no_month')
    def validate_month(self):
        if self.no_month :
            if self.no_month < 1:
                raise Warning(_("Insurance period can't be less than 1 month"))

        # return {'value':{'no_month':no_month}}

    @api.one
    def account_approve(self):
        self.env.cr.execute("""select current_date;""")
        xt = self.env.cr.fetchall()
        self.comment_date4 = xt[0][0]
        if not self.emp_account_id or not self.treasury_account_id or not self.journal_id:
            raise Warning(_("You must enter employee account & Treasury account and journal to approve "))
        if not self.insurance_line_ids:
            raise Warning(_('You must compute insurance Request before Approved'))
        can_close = False
        insurance_obj = self.env['hr.health.insurance']
        # period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        insurance_ids = []
        for insurance in self:
            insurance_request_date = insurance.date
            # period_ids = period_obj.with_context().find(insurance_request_date).id
            company_currency = insurance.employee_id.company_id.currency_id.id
            current_currency = self.env.user.company_id.currency_id.id
            amount = insurance.insurance_amount
            insurance_name = 'Health insurance For ' + insurance.employee_id.name
            reference = insurance.name
            journal_id = insurance.journal_id.id
            move_vals = {
                'name': insurance_name,
                'date': insurance_request_date,
                'ref': reference,
                # 'period_id': period_ids or False,
                'journal_id': journal_id,
                'state': 'draft',
            }
            move_id = move_obj.create(move_vals)
            move_line_vals = {
                'name': insurance_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': insurance.treasury_account_id.id,
                'debit': 0.0,
                'credit': amount,
                # 'period_id': period_ids or False,
                'journal_id': journal_id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': 0.0,
                'date': insurance_request_date,
            }
            move_line_obj.create(move_line_vals)
            move_line_vals2 = {
                'name': insurance_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': insurance.emp_account_id.id,
                'credit': 0.0,
                'debit': amount,
                # 'period_id': period_ids or False,
                'journal_id': journal_id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': 0.0,
                'date': insurance_request_date,
            }
            move_line_obj.create(move_line_vals2)
            self.write({'move_id': move_id.id})
            # self.state = 'account_approve'
            self.accounting_app_id = self.env.user.id
            self.accounting_app_date = datetime.today()

    @api.multi
    def compute_insurance_line(self):
        insurance_line = self.env['hr.health.insurance.line']
        insurance_line.search([('insurance_id', '=', self.id)]).unlink()
        for insurance in self:
            date_start_str = datetime.strptime(insurance.payment_start_date, '%Y-%m-%d')
            insurance_amount = insurance.insurance_amount
            no_month = insurance.no_month
            counter = 1
            amount_per_time = insurance_amount / no_month
            # raise Warning(_(insurance.insurance_amount))
            for i in range(1, insurance.no_month + 1):
                if i != (insurance.no_month):
                    line_id = insurance_line.create({
                        'paid_date': date_start_str,
                        'paid_amount': round(amount_per_time, 2),
                        'employee_id': insurance.employee_id.id,
                        'insurance_id': insurance.id})
                elif i == insurance.no_month:
                    line_id = insurance_line.create({
                        'paid_date': date_start_str,
                        'paid_amount': round(amount_per_time, 2) + round(
                            insurance.insurance_amount - (round(amount_per_time, 2) * insurance.no_month), 2),
                        # amount_per_time+(insurance.insurance_amount-(amount_per_time*insurance.no_month)),
                        'employee_id': insurance.employee_id.id,
                        'insurance_id': insurance.id})
                counter += 1
                date_start_str = date_start_str + relativedelta(months=1)

        return True

    @api.model
    @api.multi
    def compute_entery_count(self):
        count = 0
        entry_count = self.env['account.move.line'].search_count([('insurance_id', '=', self.id)])
        self.entry_count = entry_count

    @api.multi
    def button_reset_balance_total(self):
        total_paid_amount = 0.00
        for insurance in self:
            for line in insurance.insurance_line_ids:
                if line.paid == True:
                    total_paid_amount += line.paid_amount
            balance_amount = insurance.insurance_amount - total_paid_amount
            self.write({'total_paid_amount': total_paid_amount, 'balance_amount': balance_amount})



    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_("Warning! You cannot delete a insurance which is in %s state.") % (rec.state))
                return super(HrHealthInsurance,self).unlink()

    @api.model
    def _needaction_domain_get(self):
        dept = self.employee_id.user_id.has_group('is_newtech_purchase_customization.group_department_manager')
        hr = self.employee_id.user_id.has_group('hr.group_hr_manager')
        # gm = self.employee_id.user_id.has_group('is_hr_matwa.group_hr_general_manager')
        account = self.employee_id.user_id.has_group('account.group_account_manager')

        dept_approve = dept and 'emp_approve' or None
        hr_approve = hr and 'hod_approve' or None
        # gm_approve = gm and 'confirm' or None
        account_approve = account and 'admin_approve' or None

        return [('state', 'in', (dept_approve, hr_approve, account_approve))]


class HrHealthInsuranceLine(models.Model):
    _name = "hr.health.insurance.line"
    _description = "HR Loan Request Line"

    paid_date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    paid_amount = fields.Float(string="Paid Amount", required=True)
    paid = fields.Boolean(string="Paid")
    notes = fields.Text(string="Notes")
    insurance_id = fields.Many2one('hr.health.insurance', string="Loan Ref.", ondelete='cascade')
    payroll_id = fields.Many2one('hr.payslip', string="Payslip Ref.")

    @api.one
    def action_paid_amount(self):
        context = self._context
        can_close = False
        insurance_obj = self.env['hr.health.insurance']
        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        insurance_ids = []
        for line in self:
            if line.insurance_id.state != 'account_approve':
                raise Warning(_("Loan Request must be approved"))
            if line.paid == True:
                raise Warning(_("Insurance Installment Is Already Paid!"))
            paid_date = line.paid_date
            period_ids = period_obj.with_context().find(paid_date).id
            company_currency = line.employee_id.company_id.currency_id.id
            current_currency = self.env.user.company_id.currency_id.id
            amount = line.paid_amount
            insurance_name = 'Insurance Payment For ' + line.employee_id.name
            reference = line.insurance_id.name
            journal_id = line.insurance_id.journal_id.id
            acct_id = line.insurance_id.treasury_account_id
            if line.insurance_id.pay_account_id:
                acct_id = line.insurance_id.pay_account_id
            # if self.employee_id.cost_center_id.name == 'M':
            #     acct_id = self.env['account.account'].search([('name', 'ilike', 'Salaries Exp-M')])
            # elif self.employee_id.cost_center_id.name == 'AD':
            #     acct_id = self.env['account.account'].search([('name', 'ilike', 'Salaries Exp-Adm')])
            # elif self.employee_id.cost_center_id.name == 'S':
            #     acct_id = self.env['account.account'].search([('name', 'ilike', 'Salaries Exp-S')])
            move_vals = {
                'name': insurance_name,
                'date': paid_date,
                'ref': reference,
                'period_id': period_ids or False,
                'journal_id': journal_id,
                'state': 'draft',
            }
            move_id = move_obj.create(move_vals)
            move_line_vals = {
                'name': insurance_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.insurance_id.emp_account_id.id,
                'debit': 0.0,
                'credit': amount,
                'period_id': period_ids or False,
                'journal_id': journal_id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': 0.0,
                'date': paid_date,
                'insurance_id': line.insurance_id.id,
            }
            move_line_obj.create(move_line_vals)
            move_line_vals2 = {
                'name': insurance_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': acct_id.id,
                'credit': 0.0,
                'debit': amount,
                'period_id': period_ids or False,
                'journal_id': journal_id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': 0.0,
                'date': paid_date,
                'insurance_id': line.insurance_id.id,
            }
            move_line_obj.create(move_line_vals2)
            self.write({'paid': True})
        return True




class hr_employee(models.Model):
    _inherit = "hr.employee"

    @api.multi
    @api.one
    def _compute_insurances(self):
        count = 0
        insurance_remain_amount = 0.00
        insurance_ids = self.env['hr.health.insurance'].search([('employee_id', '=', self.id)])
        for insurance in insurance_ids:
            insurance_remain_amount += insurance.balance_amount
            count += 1
        self.insurance_count = count
        self.insurance_amount = insurance_remain_amount

    insurance_amount = fields.Float(string="insurance Amount", compute='_compute_insurances')
    insurance_count = fields.Integer(string="Loan Count", compute='_compute_insurances')


class account_move_line(models.Model):
    _inherit = "account.move.line"

    insurance_id = fields.Many2one('hr.health.insurance', string="Loan")
