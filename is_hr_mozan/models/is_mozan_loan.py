from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, time
import babel
import time
from odoo import tools


# from is_hr_matwa.models.is_hr_contract import create


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "HR Loan Request"

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.depends('date','employee_id')
    def get_name(self):
        for x in self:
            if x.date:
                ttyme = datetime.fromtimestamp(time.mktime(time.strptime(str(x.date), "%Y-%m-%d")))
                locale = self.env.context.get('lang', 'en_US')
                x.name = _('Loan for %s at Date %s') % (x.employee_id.name,
                    tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y',locale=locale)))

    name = fields.Char(string="Loan Name", readonly=True,compute ='get_name')
    date = fields.Date(string="Date Request", default=lambda self: fields.date.today(), readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True)
    parent_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department")
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position")
    emp_salary = fields.Float(string="Employee Salary", related='employee_id.contract_id.wage', readonly=True)
    # loan_old_amount = fields.Float(string="Old Loan Amount Not Paid", compute='_get_old_loan')
    employee_account = fields.Many2one('account.account', string="Debit Account", readonly=True)
    loan_account = fields.Many2one('account.account', string="Credit Account")
    payment_account = fields.Many2one('account.account', string="Payment Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    loan_amount = fields.Float(string="Loan Amount", required=True)
    attach = fields.Binary("Attachments", help="here you can attach a file or a document to the record !!")
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_amount')
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_amount')
    no_month = fields.Integer(string="No Of Month", default=1)
    payment_start_date = fields.Date(string="Deduction Start Date", required=True)
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    entry_count = fields.Integer(string="Entry Count", compute='compute_entery_count')
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    refund_move_id = fields.Many2one('account.move', string="Journal Refund Entry", readonly=True)
    refund_amount = fields.Float(string='Refunded Amount')
    refund_date = fields.Date(string="Refund Date", readonly=True)
    emp_prev_loan = fields.Float(string="Long Loan Deduction", compute='_get_salary_ded', store=True)
    emp_prev_advance_loan = fields.Float(string="Short Loan Deduction", compute='_get_salary_ded', store=True)
    pen_total = fields.Float(string="Penalty Deductions", compute='_get_salary_ded', store=True)
    total_ded = fields.Float(string="Total Deductions", compute='_get_salary_ded', store=True)
    chann_ids = fields.Many2many('mail.channel', 'pay_slip_id', 'channel_id', string='Channel')
    # paid_amount = fields.Float(string='Paid Value')
    state = fields.Selection(
        [('draft', 'To Submit'), ('approve', 'Sent'),
         ('confirm', 'HR Confirmed'), ('gm_approve', 'Confirmed'), ('account_confirm', 'Account Approval'),
         ('done', 'Paid'), ('refunded', 'Refunded'),
         ('refuse', 'Refused')],
        'Status', readonly=True, track_visibility='onchange', copy=False,
        help='The status is set to \'To Submit\', when a loan request is created.\
                  \nThe status is \'Confirmed\', when loan request is confirmed by department manager.\
                  \nThe status is \'Approved\', when loan request is confirmed by HR manager.\
                  \nThe status is \'Refused\', when loan request is refused by manager.\
                  \nThe status is \'Approved\', when loan request is approved by manager.', default='draft')

    @api.multi
    def unlink(self):
        for x in self:
            if any(x.filtered(lambda hr_loan: hr_loan.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete a Loan which is not draft or refused!'))
            return super(HrLoan, x).unlink()

    @api.depends('employee_id')
    def _get_salary_ded(self):
        for x in self:
            remaining_advance_loan_installment = 0.0
            remaining_loan_installment = 0.0
            pen_total = 0.0
            if x.employee_id:
                contract_ids = x.env['hr.contract'].search([('employee_id', '=', x.employee_id.id)])
                if contract_ids:
                    last_contract = contract_ids[-1]
                    x.emp_si = last_contract.wage * .08

                loan_ids = x.env['hr.loan.line'].search(
                    [('employee_id', '=', x.employee_id.id), ('paid', '=', False), ('paid_date', '>=', x.date),
                     ('loan_id.state', '=', 'done')])
                if loan_ids:
                    remaining_loan_installment = 0.0
                    for loan_id in loan_ids:
                        remaining_loan_installment += loan_id.paid_amount
                    x.emp_prev_loan = remaining_loan_installment

                short_loan_ids = x.env['hr.monthlyloan'].search(
                    [('employee_id', '=', x.employee_id.id), ('state', '=', 'done'), ('date', '>=', x.date)])
                if short_loan_ids:
                    remaining_advance_loan_installment = 0.0
                    for short_loan in short_loan_ids:
                        remaining_advance_loan_installment += short_loan.loan_amount
                    x.emp_prev_advance_loan = remaining_advance_loan_installment
                penalty_ids = x.env['hr.warnings'].search(
                    [('employee_id', '=', x.employee_id.id), ('name', '>=', x.date), ('deduct_amount', '>=', 0.0),
                     ('state', '=', 'done')])
                for penalty_id in penalty_ids:
                    pen_total += penalty_id.deduct_amount

                x.total_ded = remaining_advance_loan_installment + remaining_loan_installment + pen_total

    @api.model
    def _needaction_domain_get(self):
        dept = self.employee_id.user_id.has_group('is_hr_tesla_12.group_department_manager')
        hr = self.employee_id.user_id.has_group('hr.group_hr_manager')
        gm = self.employee_id.user_id.has_group('is_hr_tesla_12.group_general_manager')
        account = self.employee_id.user_id.has_group('account.group_account_manager')
        account_user = self.employee_id.user_id.has_group('account.group_account_user')

        dept_approve = dept and 'draft' or None
        hr_approve = hr and 'approve' or None
        gm_approve = gm and 'confirm' or None
        account_approve = account and 'gm_approve' or None

        return [('state', 'in', (dept_approve, hr_approve, gm_approve, account_approve))]

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.loan.long') or ' '
        res = super(HrLoan, self).create(values)
        return res

    @api.one
    def _compute_amount(self):
        total_paid_amount = 0.00
        for loan in self:
            for line in loan.loan_line_ids:
                if line.paid:
                    total_paid_amount += line.paid_amount

            balance_amount = loan.loan_amount - total_paid_amount - loan.refund_amount
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid_amount
            # print self.balance_amount

    # @api.onchange('employee_id')
    # def _onchange_employee_d(self):
    #     for x in self:
    #         if x.employee_id:
    #             x.emp_salary = x.employee_id.contract_id.wage

    @api.one
    def loan_refuse(self):
        self.state = 'refuse'

    @api.one
    def loan_reset(self):
        self.state = 'draft'

    @api.one
    def loan_confirm(self):
        # noti
        message_pool = self.env['mail.message']

        user_from_email = self.env.user.email
        recipient_partners = []
        users = self.env['res.users']
        partner = users.search([('id', '=', self.env.user.id)])
        group = self.env.ref('hr.group_hr_manager')
        print(group.users)
        for recipient in group.users:
            # if recipient == self.env.user.approval_manager:
            recipient_partners.append(
                (recipient.partner_id)
            )
        record_name = self.name
        users = self.env['res.users'].browse(recipient_partners)
        emp_ids = []
        names = []
        self.chann_ids = False

        for part in partner:
            partner_id = part.partner_id.id
            for noti in recipient_partners:
                emp_ids.append(noti.id)
                names.append(noti.name)

            channel_ids = self.env['mail.channel'].search([])
            for chan in channel_ids:
                if len(chan.channel_partner_ids) == 2:
                    followers = []
                    for partner in chan.channel_partner_ids:
                        followers.append(partner.id)

                    if followers:
                        for line in emp_ids:
                            couples = []
                            couples.append(partner_id)
                            couples.append(line)
                            if followers == couples:
                                self.chann_ids = [(4, chan.id)]
            for line in emp_ids:
                coup = []
                chnne_id = []
                nam = []
                coup.append(partner_id)
                # nam.append(part.partner_id.name)
                coup.append(line)
                # nam.append(line)
                boole = False
                for item in self.chann_ids:
                    people = []
                    for peop in item.channel_partner_ids:
                        people.append(peop.id)
                    if people:
                        if people == coup:
                            boole = True
                            # to concatenate channel name
                if boole == False:
                    res_part = self.env['res.partner'].search([('id', 'in', coup)])
                    no = 0
                    for res in res_part:
                        nam.append(res.name)
                        if no == 0:
                            nom = res.name + ','
                        else:
                            nom = nom + res.name + ','
                        no += 1
                    chnne = self.env['mail.channel'].create(
                        {'channel_partner_ids': [(6, 0, coup)], 'name': nom, 'public': 'private',
                         'channel_type': 'chat'})

                    for line in chnne:
                        chnne_id = []
                        chnne_id.append(line.id)

                if chnne_id:
                    for line in chnne_id:
                        self.chann_ids = [(4, line)]

            ids = []
            for line in self.chann_ids:
                ids.append(line.id)
            template = {
                'subject': 'You have loan request waiting for you, please check it.',
                'body': 'You have loan request ' + self.name + ' waiting for approval',
                'model': 'hr.loan',
                'res_id': self.id,
                'message_type': 'comment',
                'email_from': user_from_email,
                'record_name': record_name,
                'subtype_id.name': 'Discussions',
                'channel_ids': [(6, 0, ids)],
            }

            message = self.env['mail.message'].create(template)
            print(message)
            for noti in recipient_partners:
                partner_id = noti.id
                notification = {
                    'mail_message_id': message.id,
                    'res_partner_id': partner_id,
                    'is_read': False,
                    'email_status': 'sent',
                }
                notification_ids = self.env['mail.notification'].create(notification)
                print(notification_ids)
            for mess in message:
                mess.needaction_partner_ids = [(4, pid.id) for pid in recipient_partners]

        self.compute_loan_line()
        self.state = 'approve'

    @api.one
    def loan_gm_approve(self):
        # noti
        message_pool = self.env['mail.message']

        user_from_email = self.env.user.email
        recipient_partners = []
        users = self.env['res.users']
        partner = users.search([('id', '=', self.env.user.id)])
        group = self.env.ref('account.group_account_manager')
        print(group.users)
        for recipient in group.users:
            recipient_partners.append(
                (recipient.partner_id)
            )
        record_name = self.name
        users = self.env['res.users'].browse(recipient_partners)
        emp_ids = []
        names = []
        self.chann_ids = False

        for part in partner:
            partner_id = part.partner_id.id
            for noti in recipient_partners:
                emp_ids.append(noti.id)
                names.append(noti.name)

            channel_ids = self.env['mail.channel'].search([])
            for chan in channel_ids:
                if len(chan.channel_partner_ids) == 2:
                    followers = []
                    for partner in chan.channel_partner_ids:
                        followers.append(partner.id)

                    if followers:
                        for line in emp_ids:
                            couples = []
                            couples.append(partner_id)
                            couples.append(line)
                            if followers == couples:
                                self.chann_ids = [(4, chan.id)]
            for line in emp_ids:
                coup = []
                chnne_id = []
                nam = []
                coup.append(partner_id)
                # nam.append(part.partner_id.name)
                coup.append(line)
                # nam.append(line)
                boole = False
                for item in self.chann_ids:
                    people = []
                    for peop in item.channel_partner_ids:
                        people.append(peop.id)
                    if people:
                        if people == coup:
                            boole = True
                            # to concatenate channel name
                if boole == False:
                    res_part = self.env['res.partner'].search([('id', 'in', coup)])
                    no = 0
                    for res in res_part:
                        nam.append(res.name)
                        if no == 0:
                            nom = res.name + ','
                        else:
                            nom = nom + res.name + ','
                        no += 1
                    chnne = self.env['mail.channel'].create(
                        {'channel_partner_ids': [(6, 0, coup)], 'name': nom, 'public': 'private',
                         'channel_type': 'chat'})

                    for line in chnne:
                        chnne_id = []
                        chnne_id.append(line.id)

                if chnne_id:
                    for line in chnne_id:
                        self.chann_ids = [(4, line)]

            ids = []
            for line in self.chann_ids:
                ids.append(line.id)
            template = {
                'subject': 'You have loan request waiting for you, please check it.',
                'body': 'You have loan request ' + self.name + ' waiting for approval',
                'model': 'hr.loan',
                'res_id': self.id,
                'message_type': 'comment',
                'email_from': user_from_email,
                'record_name': record_name,
                'subtype_id.name': 'Discussions',
                'channel_ids': [(6, 0, ids)],
            }

            message = self.env['mail.message'].create(template)
            print(message)
            for noti in recipient_partners:
                partner_id = noti.id
                notification = {
                    'mail_message_id': message.id,
                    'res_partner_id': partner_id,
                    'is_read': False,
                    'email_status': 'sent',
                }
                notification_ids = self.env['mail.notification'].create(notification)
                print(notification_ids)
            for mess in message:
                mess.needaction_partner_ids = [(4, pid.id) for pid in recipient_partners]
        self.state = 'gm_approve'

    @api.one
    def hr_validate(self):
        # noti
        message_pool = self.env['mail.message']

        user_from_email = self.env.user.email
        recipient_partners = []
        users = self.env['res.users']
        partner = users.search([('id', '=', self.env.user.id)])
        # group = self.env.ref('is_hr_tesla_12.group_general_manager')
        # print(group.users)
        # for recipient in group.users:
        #     # if recipient == self.env.user.approval_manager:
        #     recipient_partners.append(
        #         (recipient.partner_id)
        #     )
        record_name = self.name
        users = self.env['res.users'].browse(recipient_partners)
        emp_ids = []
        names = []
        self.chann_ids = False

        for part in partner:
            partner_id = part.partner_id.id
            for noti in recipient_partners:
                emp_ids.append(noti.id)
                names.append(noti.name)

            channel_ids = self.env['mail.channel'].search([])
            for chan in channel_ids:
                if len(chan.channel_partner_ids) == 2:
                    followers = []
                    for partner in chan.channel_partner_ids:
                        followers.append(partner.id)

                    if followers:
                        for line in emp_ids:
                            couples = []
                            couples.append(partner_id)
                            couples.append(line)
                            if followers == couples:
                                self.chann_ids = [(4, chan.id)]
            for line in emp_ids:
                coup = []
                chnne_id = []
                nam = []
                coup.append(partner_id)
                # nam.append(part.partner_id.name)
                coup.append(line)
                # nam.append(line)
                boole = False
                for item in self.chann_ids:
                    people = []
                    for peop in item.channel_partner_ids:
                        people.append(peop.id)
                    if people:
                        if people == coup:
                            boole = True
                            # to concatenate channel name
                if boole == False:
                    res_part = self.env['res.partner'].search([('id', 'in', coup)])
                    no = 0
                    for res in res_part:
                        nam.append(res.name)
                        if no == 0:
                            nom = res.name + ','
                        else:
                            nom = nom + res.name + ','
                        no += 1
                    chnne = self.env['mail.channel'].create(
                        {'channel_partner_ids': [(6, 0, coup)], 'name': nom, 'public': 'private',
                         'channel_type': 'chat'})

                    for line in chnne:
                        chnne_id = []
                        chnne_id.append(line.id)

                if chnne_id:
                    for line in chnne_id:
                        self.chann_ids = [(4, line)]

            ids = []
            for line in self.chann_ids:
                ids.append(line.id)
            template = {
                'subject': 'You have loan request waiting for you, please check it.',
                'body': 'You have loan request ' + self.name + ' waiting for approval',
                'model': 'hr.loan',
                'res_id': self.id,
                'message_type': 'comment',
                'email_from': user_from_email,
                'record_name': record_name,
                'subtype_id.name': 'Discussions',
                'channel_ids': [(6, 0, ids)],
            }

            message = self.env['mail.message'].create(template)
            print(message)
            for noti in recipient_partners:
                partner_id = noti.id
                notification = {
                    'mail_message_id': message.id,
                    'res_partner_id': partner_id,
                    'is_read': False,
                    'email_status': 'sent',
                }
                notification_ids = self.env['mail.notification'].create(notification)
                print(notification_ids)
            for mess in message:
                mess.needaction_partner_ids = [(4, pid.id) for pid in recipient_partners]
        self.state = 'confirm'

    @api.one
    def action_account_confirm(self):
        # noti
        message_pool = self.env['mail.message']

        user_from_email = self.env.user.email
        recipient_partners = []
        users = self.env['res.users']
        partner = users.search([('id', '=', self.env.user.id)])
        group = self.env.ref('account.group_account_user')
        print(group.users)
        for recipient in group.users:
            # if recipient == self.env.user.approval_manager:
            recipient_partners.append(
                (recipient.partner_id)
            )
        record_name = self.name
        users = self.env['res.users'].browse(recipient_partners)
        emp_ids = []
        names = []
        self.chann_ids = False

        for part in partner:
            partner_id = part.partner_id.id
            for noti in recipient_partners:
                emp_ids.append(noti.id)
                names.append(noti.name)

            channel_ids = self.env['mail.channel'].search([])
            for chan in channel_ids:
                if len(chan.channel_partner_ids) == 2:
                    followers = []
                    for partner in chan.channel_partner_ids:
                        followers.append(partner.id)

                    if followers:
                        for line in emp_ids:
                            couples = []
                            couples.append(partner_id)
                            couples.append(line)
                            if followers == couples:
                                self.chann_ids = [(4, chan.id)]
            for line in emp_ids:
                coup = []
                chnne_id = []
                nam = []
                coup.append(partner_id)
                # nam.append(part.partner_id.name)
                coup.append(line)
                # nam.append(line)
                boole = False
                for item in self.chann_ids:
                    people = []
                    for peop in item.channel_partner_ids:
                        people.append(peop.id)
                    if people:
                        if people == coup:
                            boole = True
                            # to concatenate channel name
                if boole == False:
                    res_part = self.env['res.partner'].search([('id', 'in', coup)])
                    no = 0
                    for res in res_part:
                        nam.append(res.name)
                        if no == 0:
                            nom = res.name + ','
                        else:
                            nom = nom + res.name + ','
                        no += 1
                    chnne = self.env['mail.channel'].create(
                        {'channel_partner_ids': [(6, 0, coup)], 'name': nom, 'public': 'private',
                         'channel_type': 'chat'})

                    for line in chnne:
                        chnne_id = []
                        chnne_id.append(line.id)

                if chnne_id:
                    for line in chnne_id:
                        self.chann_ids = [(4, line)]

            ids = []
            for line in self.chann_ids:
                ids.append(line.id)
            template = {
                'subject': 'You have loan request waiting for you, please check it.',
                'body': 'You have loan request ' + self.name + ' waiting for approval',
                'model': 'hr.loan',
                'res_id': self.id,
                'message_type': 'comment',
                'email_from': user_from_email,
                'record_name': record_name,
                'subtype_id.name': 'Discussions',
                'channel_ids': [(6, 0, ids)],
            }

            message = self.env['mail.message'].create(template)
            print(message)
            for noti in recipient_partners:
                partner_id = noti.id
                notification = {
                    'mail_message_id': message.id,
                    'res_partner_id': partner_id,
                    'is_read': False,
                    'email_status': 'sent',
                }
                notification_ids = self.env['mail.notification'].create(notification)
                print(notification_ids)
            for mess in message:
                mess.needaction_partner_ids = [(4, pid.id) for pid in recipient_partners]
        self.state = 'account_confirm'

    # @api.one
    @api.onchange('no_month')
    def validate_month(self):
        for x in self:
            if x.no_month < 1:
                raise Warning(_("Loan period can't be less than 1 month"))

                # return {'value':{'no_month':no_month}}

    @api.one
    def loan_validate(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        self.env.cr.execute("""select current_date;""")
        xt = self.env.cr.fetchall()
        self.comment_date4 = xt[0][0]
        if not self.employee_account or not self.loan_account or not self.journal_id:
            raise Warning(_("You must enter employee account & Loan account and journal to approve "))
        if not self.loan_line_ids:
            raise Warning(_('You must compute Loan Request before Approved'))
        can_close = False
        loan_obj = self.env['hr.loan']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        loan_ids = []
        for loan in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            loan_request_date = loan.date
            company_currency = loan.employee_id.company_id.currency_id.id
            current_currency = self.env.user.company_id.currency_id.id
            amount = loan.loan_amount
            loan_name = 'Loan For ' + loan.employee_id.name
            reference = loan.name
            journal_id = loan.journal_id.id
            move_dict = {
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': loan_request_date,
            }
            debit_line = (0, 0, {
                'name': loan_name,
                'partner_id': loan.employee_id.address_id.id,
                'account_id': loan.employee_account.id,
                'journal_id': journal_id,
                'date': loan_request_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': loan.loan_account.id,
                'journal_id': journal_id,
                'date': loan_request_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_journal_credit = loan.journal_id.default_credit_account_id.id
                if not acc_journal_credit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        loan.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_credit,
                    'journal_id': journal_id,
                    'date': loan_request_date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_journal_deit = loan.journal_id.default_debit_account_id.id
                if not acc_journal_deit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        loan.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_deit,
                    'journal_id': journal_id,
                    'date': loan_request_date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            loan.write({'move_id': move.id, 'date': loan_request_date})
            move.post()
            self.state = 'done'

    @api.multi
    def compute_loan_line(self):
        for loan in self:
            loan_line = self.env['hr.loan.line']
            loan_line.search([('loan_id', '=', self.id)]).unlink()
            date_start_str = datetime.strptime(str(loan.payment_start_date), '%Y-%m-%d')
            counter = 1
            amount_per_time = loan.loan_amount / loan.no_month
            for i in range(1, loan.no_month + 1):
                if i != loan.no_month:
                    line_id = loan_line.create({
                        'paid_date': date_start_str,
                        'paid_amount': round(amount_per_time, 2),
                        'employee_id': loan.employee_id.id,
                        'loan_id': loan.id})
                elif i == loan.no_month:
                    line_id = loan_line.create({
                        'paid_date': date_start_str,
                        'paid_amount': round(amount_per_time, 2) +
                                       round(loan.loan_amount - (round(amount_per_time, 2) * loan.no_month), 2),
                        'employee_id': loan.employee_id.id,
                        'loan_id': loan.id})
                counter += 1
                date_start_str = date_start_str + relativedelta(months=1)

        return True

    @api.model
    @api.multi
    def compute_entery_count(self):
        for loan in self:
            count = 0
            # entry_count = loan.env['account.move.line'].search_count([('loan_id', '=', loan.id)])
            # loan.entry_count = entry_count

    @api.multi
    def button_reset_balance_total(self):
        total_paid_amount = 0.00
        for loan in self:
            for line in loan.loan_line_ids:
                if line.paid:
                    total_paid_amount += line.paid_amount
            balance_amount = loan.loan_amount - total_paid_amount
            self.write({'total_paid_amount': total_paid_amount, 'balance_amount': balance_amount})

            # @api.constrains('employee_id')
            # def _emp_loan_unpaid(self):
            #     for loan in self:
            #         if loan.employee_id:
            #             past_loans_ids = loan.env['hr.loan'].search(
            #                 [('employee_id', '=', loan.employee_id.id), ('state', '=', 'done')])
            #             for past_loans in past_loans_ids:
            #                 loan_line_ids = loan.env['hr.loan.line'].search([('loan_id', '=', past_loans.id)])
            #                 for loan_line in loan_line_ids:
            #                     if not loan_line.paid:
            #                         raise Warning(_(
            #                             "This employee must complete payments for a current running loan, in order to request another"))


class HrLoanLine(models.Model):
    _name = "hr.loan.line"
    _description = "HR Loan Request Line"

    paid_date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    paid_amount = fields.Float(string="Paid Amount", required=True)
    paid = fields.Boolean(string="Paid")
    stopped = fields.Boolean(string="Stopped")
    notes = fields.Text(string="Notes")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", ondelete='cascade')
    payroll_id = fields.Many2one('hr.payslip', string="Payslip Ref.")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)

    @api.one
    def action_paid_amount(self):
        # for line in self:
        #     context = self._context
        #     can_close = False
        #     loan_obj = self.env['hr.loan']
        #     move_obj = self.env['account.move']
        #     move_line_obj = self.env['account.move.line']
        #     currency_obj = self.env['res.currency']
        #     created_move_ids = []
        #     loan_ids = []
        #     line_ids = []
        #     debit_sum = 0.0
        #     credit_sum = 0.0
        #     if not line.payroll_id:
        #         if line.loan_id.state != 'done':
        #             raise Warning(_("Loan Request must be approved"))
        #         paid_date = line.paid_date
        #         company_currency = line.employee_id.company_id.currency_id.id
        #         current_currency = self.env.user.company_id.currency_id.id
        #         debit_account = False
        #         amount = line.paid_amount
        #         loan_name = 'Installment Payment of ' + line.loan_id.employee_id.name
        #         reference = line.loan_id.name
        #         journal_id = line.loan_id.journal_id.id
        #         if line.loan_id.payment_account.id:
        #             debit_account = line.loan_id.payment_account.id
        #         if not line.loan_id.payment_account.id:
        #             debit_account = line.loan_id.loan_account.id
        #
        #         debit_line = (0, 0, {
        #             'name': loan_name,
        #             'ref': reference,
        #             'account_id': debit_account,
        #             'journal_id': journal_id,
        #             'analytic_account_id': False,
        #             'date': paid_date,
        #             'debit': amount > 0.0 and amount or 0.0,
        #             'credit': amount < 0.0 and -amount or 0.0,
        #             'partner_id': False,
        #
        #         })
        #         line_ids.append(debit_line)
        #         debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
        #
        #         credit_line = (0, 0, {
        #             'name': loan_name,
        #             'ref': reference,
        #             'account_id': line.loan_id.employee_account.id,
        #             'journal_id': journal_id,
        #             'analytic_account_id': False,
        #             'date': paid_date,
        #             'debit': amount < 0.0 and -amount or 0.0,
        #             'credit': amount > 0.0 and amount or 0.0,
        #             'partner_id': line.employee_id.address_id.id,
        #
        #         })
        #         line_ids.append(credit_line)
        #         move_dict = {'name': loan_name,
        #                      'narration': loan_name,
        #                      'ref': reference,
        #                      'journal_id': journal_id,
        #                      'date': fields.Date.today(),
        #                      'line_ids': line_ids
        #                      }
        #         move = self.env['account.move'].create(move_dict)
        #         move.post()
        self.write({'paid': True, 'notes': 'Paid'})

    @api.one
    @api.constrains('paid_amount')
    def _loan_line_installment(self):
        for x in self:
            if x.paid_amount:
                short_loan_ids = x.env['hr.monthlyloan'].search(
                    [('employee_id', '=', x.employee_id.id), ('state', '=', 'done')])
                short_loan_amt = 0.00
                for loan in short_loan_ids:
                    DATETIME_FORMAT = "%Y-%m-%d"
                    short_loan_date = datetime.strptime(str(loan.date), DATETIME_FORMAT)
                    installment_loan_date = datetime.strptime(x.paid_date, DATETIME_FORMAT)
                    if short_loan_date.month == installment_loan_date.month:
                        short_loan_amt += loan.loan_amount
            #     if x.paid_amount + short_loan_amt > x.loan_id.emp_salary * 0.8:
            #         raise Warning(_("Monthly Loan  Cannot Exceed 70% of The Employee's Salary!"))
            # else:
                        short_loan_ids = x.env['hr.monthlyloan'].search(
                            [('employee_id', '=', x.employee_id.id), ('state', '=', 'done')])
                        short_loan_amt = 0.00
                        for loan in short_loan_ids:
                            DATETIME_FORMAT = "%Y-%m-%d"
                            short_loan_date = datetime.strptime(loan.date, DATETIME_FORMAT)
                            installment_loan_date = datetime.strptime(x.paid_date, DATETIME_FORMAT)
                            if short_loan_date.month == installment_loan_date.month:
                                short_loan_amt += loan.loan_amount
                        if x.paid_amount + short_loan_amt > x.loan_id.emp_salary:
                            raise Warning(_("Monthly Loan Cannot Exceed The Employee's Salary!"))


class hr_monthlyloan(models.Model):
    _name = 'hr.monthlyloan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.one
    def loan_cancel(self):
        # self.action_paid()
        can_close = False
        loan_obj = self.env['hr.monthlyloan']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        print(self.state)
        loan_ids = []
        if self.state == 'done':
            print('tttttttttttttttttt')
            loan_pay_date = fields.Date.today()
            amount = self.loan_amount
            loan_name = 'Loan Cancel of ' + self.employee_id.name + self.move_id.name
            reference = 'Loan Cancel of ' + self.employee_id.name
            journal_id = self.journal_id.id
            move_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            currency_obj = self.env['res.currency']
            created_move_ids = []
            loan_ids = []

            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            move_dict = {
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': loan_pay_date,
            }

            debit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': self.loan_account.id,
                'journal_id': journal_id,
                'date': loan_pay_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': self.employee_account.id,
                'journal_id': journal_id,
                'date': loan_pay_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            print(move)
            self.write({'move_id_pay': move.id, 'date_pay': loan_pay_date})
            move.post()
        self.state = 'cancel'

    name = fields.Char('Loan')
    date = fields.Date(string="loan Date", default=lambda self: fields.date.today(), readonly=True)
    date_pay = fields.Date(string="Loan Pay Date", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department")
    loan_amount = fields.Float(string="Loan Amount", required=True)
    employee_salary = fields.Float(string="Employee Salary", compute='_compute_salary')
    employee_account = fields.Many2one('account.account', string="Debit Account")
    loan_account = fields.Many2one('account.account', string="Credit Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    move_id_pay = fields.Many2one('account.move', string="Loan Payment Entry", readonly=True)
    payment_account = fields.Many2one('account.account', string="Payment Account")
    state = fields.Selection(
        [('draft', 'To Submit'), ('confirm', 'Sent'),
         ('approve', 'HR Approval'), ('account_confirm', 'Account Approval'), ('done', 'Done'), ('paid', 'Paid'),('cancel', 'Cancel'),
         ('refuse', 'Refused')],
        'Status', default='draft', readonly=True)

    @api.model
    def _needaction_domain_get(self):
        hr = self.employee_id.user_id.has_group('hr.group_hr_manager')
        gm = self.employee_id.user_id.has_group('is_hr_tesla_12.group_hr_general_manager')
        account = self.employee_id.user_id.has_group('account.group_account_manager')
        account_user = self.employee_id.user_id.has_group('account.group_account_user')

        hr_approve = hr and 'confirm' or None
        account_approve = account and 'approve' or None
        account_confirm = account_user and 'account_confirm' or None

        return [('state', 'in', (hr_approve, account_approve, account_confirm))]

    @api.one
    def loan_confirm(self):
        self.state = 'confirm'

    @api.one
    def loan_approve(self):
        self.state = 'approve'

    @api.one
    def action_account_confirm(self):
        self.state = 'account_confirm'

    @api.one
    def action_paid(self):
        # can_close = False
        # loan_obj = self.env['hr.monthlyloan']
        # move_obj = self.env['account.move']
        # move_line_obj = self.env['account.move.line']
        # created_move_ids = []
        # loan_ids = []
        # for loan in self:
        #     if loan.state == 'done':
        #         loan_pay_date = fields.Date.today()
        #         amount = loan.loan_amount
        #         loan_name = 'Short Loan Payment For ' + loan.employee_id.name
        #         reference = loan.name
        #         journal_id = loan.journal_id.id
        #         move_obj = self.env['account.move']
        #         move_line_obj = self.env['account.move.line']
        #         currency_obj = self.env['res.currency']
        #         created_move_ids = []
        #         loan_ids = []
        #         if loan.payment_account.id:
        #             debit_account = loan.payment_account.id
        #         if not loan.payment_account.id:
        #             debit_account = loan.loan_account.id
        #         line_ids = []
        #         debit_sum = 0.0
        #         credit_sum = 0.0
        #         move_dict = {
        #             'narration': loan_name,
        #             'ref': reference,
        #             'journal_id': journal_id,
        #             'date': loan_pay_date,
        #         }
        #
        #         debit_line = (0, 0, {
        #             'name': loan_name,
        #             'partner_id': loan.employee_id.address_id.id,
        #             'account_id': debit_account,
        #             'journal_id': journal_id,
        #             'date': loan_pay_date,
        #             'debit': amount > 0.0 and amount or 0.0,
        #             'credit': amount < 0.0 and -amount or 0.0,
        #             'analytic_account_id': False,
        #             'tax_line_id': 0.0,
        #         })
        #         line_ids.append(debit_line)
        #         debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
        #         credit_line = (0, 0, {
        #             'name': loan_name,
        #             'partner_id': loan.employee_id.address_id.id,
        #             'account_id': loan.employee_account.id,
        #             'journal_id': journal_id,
        #             'date': loan_pay_date,
        #             'debit': amount < 0.0 and -amount or 0.0,
        #             'credit': amount > 0.0 and amount or 0.0,
        #             'analytic_account_id': False,
        #             'tax_line_id': 0.0,
        #         })
        #         line_ids.append(credit_line)
        #         credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
        #         move_dict['line_ids'] = line_ids
        #         move = self.env['account.move'].create(move_dict)
        #         loan.write({'move_id_pay': move.id, 'date_pay': loan_pay_date})
        #         move.post()
        self.state = 'paid'

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.loan.short') or ' '
        res = super(hr_monthlyloan, self).create(values)
        return res

    @api.depends('employee_id')
    def _compute_salary(self):
        if self.employee_id:
            self.employee_salary = self.employee_id.contract_id.wage

    @api.one
    def loan_validate(self):
        if not self.employee_account or not self.loan_account or not self.journal_id:
            raise Warning(_("You must enter employee account & Loan account and journal to approve "))
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        loan_ids = []
        for monthh_loan in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            loan_date = monthh_loan.date
            company_currency = monthh_loan.employee_id.company_id.currency_id.id
            current_currency = self.env.user.company_id.currency_id.id
            amount = monthh_loan.loan_amount
            loan_name = 'Short Loan For ' + monthh_loan.employee_id.name
            reference = monthh_loan.name
            journal_id = monthh_loan.journal_id.id
            move_dict = {
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': loan_date,
            }
            debit_line = (0, 0, {
                'name': loan_name,
                'partner_id': monthh_loan.employee_id.address_id.id,
                'account_id': monthh_loan.employee_account.id,
                'journal_id': journal_id,
                'date': loan_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': loan_name,
                'partner_id': False,
                'account_id': monthh_loan.loan_account.id,
                'journal_id': journal_id,
                'date': loan_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            monthh_loan.write({'move_id': move.id, 'date': loan_date})
            move.post()
            self.state = 'done'

    @api.one
    @api.constrains('loan_amount')
    def _loan_amount(self):
        if self.loan_amount:
            salary = self.employee_salary
            allowable_loan = salary * 70 / 100
            if self.loan_amount > allowable_loan:
                raise Warning(_("Monthly Loan Cannot Exceed 70% of The Employee's Salary!"))

    @api.one
    def loan_refuse(self):
        self.state = 'refuse'

    @api.one
    def loan_reset(self):
        self.state = 'draft'

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_("Warning! You cannot delete a Loan which is in %s state.") % (rec.state))
            return super(hr_monthlyloan, self).unlink()


class WizardLoan(models.Model):
    _name = 'wizard.loan'
    _description = 'Pay Loan'
    loan_id = fields.Many2one('hr.loan', 'Loan', ondelete='cascade')
    refund_amount = fields.Float('Refund')

    def refund_loan(self):
        for loan in self:
            if loan.loan_id:
                refund_amount = loan.refund_amount
                hr_loan_id = loan.loan_id
                unpaid_amount = hr_loan_id.balance_amount
                total_amount = hr_loan_id.loan_amount
                reaming_amount = unpaid_amount - refund_amount
                if reaming_amount == 0:
                    if hr_loan_id.state == 'done':
                        loan_amount = 0.0
                        acc_journal_credit = hr_loan_id.journal_id.default_credit_account_id.id
                        acc_journal_debit = hr_loan_id.journal_id.default_credit_account_id.id
                        # if not acc_journal_credit:
                        #     raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        #         hr_loan_id.journal_id.name))

                        precision = self.env['decimal.precision'].precision_get('Payroll')
                        self.env.cr.execute("""select current_date;""")
                        xt = self.env.cr.fetchall()
                        self.comment_date4 = xt[0][0]
                        loan_line_ids = hr_loan_id.loan_line_ids
                        for loan_line in loan_line_ids:
                            paid = loan_line.paid
                            if not paid:
                                loan_line.paid = True
                                created_move_ids = []
                                loan_ids = []
                                line_ids = []
                                debit_sum = 0.0
                                credit_sum = 0.0
                                refund_date = fields.Date.today()
                                journal_id = hr_loan_id.journal_id.id
                                company_currency = hr_loan_id.employee_id.company_id.currency_id.id
                                current_currency = hr_loan_id.env.user.company_id.currency_id.id
                                ref_loan_name = 'Refund Loan For ' + hr_loan_id.employee_id.name
                                reference = 'Refund Loan'
                                move_dict = {
                                    'narration': ref_loan_name,
                                    'ref': reference,
                                    'journal_id': journal_id,
                                    'date': refund_date,
                                }
                                debit_line = (0, 0, {
                                    'name': ref_loan_name,
                                    'partner_id': False,
                                    'account_id': hr_loan_id.loan_account.id,
                                    'journal_id': journal_id,
                                    'date': refund_date,
                                    'debit': unpaid_amount > 0.0 and unpaid_amount or 0.0,
                                    'credit': unpaid_amount < 0.0 and -unpaid_amount or 0.0,
                                    'analytic_account_id': False,
                                    'tax_line_id': 0.0,
                                })
                                line_ids.append(debit_line)
                                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                                credit_line = (0, 0, {
                                    'name': ref_loan_name,
                                    'partner_id': hr_loan_id.employee_id.address_id.id,
                                    'account_id': hr_loan_id.employee_account.id,
                                    'journal_id': journal_id,
                                    'date': refund_date,
                                    'debit': unpaid_amount < 0.0 and -unpaid_amount or 0.0,
                                    'credit': unpaid_amount > 0.0 and unpaid_amount or 0.0,
                                    'analytic_account_id': False,
                                    'tax_line_id': 0.0,
                                })
                                line_ids.append(credit_line)
                                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                                if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                                    adjust_credit = (0, 0, {
                                        'name': _('Adjustment Entry'),
                                        'partner_id': False,
                                        'account_id': acc_journal_debit,
                                        'journal_id': journal_id,
                                        'date': refund_date,
                                        'debit': 0.0,
                                        'credit': debit_sum - credit_sum,
                                    })
                                    line_ids.append(adjust_credit)

                                elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                                    if not acc_journal_debit:
                                        raise UserError(_(
                                            'The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                                            hr_loan_id.journal_id.name))
                                    adjust_debit = (0, 0, {
                                        'name': _('Adjustment Entry'),
                                        'partner_id': False,
                                        'account_id': acc_journal_credit,
                                        'journal_id': journal_id,
                                        'date': refund_date,
                                        'debit': credit_sum - debit_sum,
                                        'credit': 0.0,
                                    })
                                    line_ids.append(adjust_debit)
                                move_dict['line_ids'] = line_ids
                                move = loan.env['account.move'].create(move_dict)
                                hr_loan_id.write({'refund_move_id': move.id, 'refund_date': refund_date,
                                                  'state': 'refunded'})
                                move.post()
                if reaming_amount > 0:
                    loan_unpaid_ids = self.env['hr.loan.line'].search([('loan_id', '=', hr_loan_id.id),
                                                                       ('paid', '=', False)])

                    ded_amount = refund_amount / len(loan_unpaid_ids)
                    for unpaid in loan_unpaid_ids:
                        new_amount = unpaid.paid_amount - ded_amount
                        unpaid.paid_amount = new_amount
                    hr_loan_id.refund_amount += refund_amount


                    # raise UserError(_('You Have To Refund %s') % unpaid_amount)


# class account_move_line(models.Model):
#     _inherit = "account.move.line"
#
#     loan_id = fields.Many2one('hr.loan', string="Loan", ondelete='cascade')
