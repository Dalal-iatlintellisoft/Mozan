from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
import babel
import time
from odoo import tools

# inheriting hr.employee to add some fields
class hr_employee(models.Model):
    _inherit = "hr.employee"

    emp_training_ids = fields.One2many('hr.training.training.employees', 'employee_id', domain=[('attend', '=', True)],
                                       string='Training')

# A model for university
class hr_university(models.Model):
    _name = "hr.university"
    _description = "University"

    name = fields.Char('University Name')

# A model for employee training
class hr_training_training_employees(models.Model):
    _name = "hr.training.training.employees"
    _description = "Training Employees"

    name = fields.Char('Employee Training')
    employee_id = fields.Many2one('hr.employee','Employee Name')
    attend = fields.Boolean('Attend')

# A model for Educational Level
class hr_educational_level(models.Model):
    _name = "hr.educational.level"
    _description = "Educational Level"

    name = fields.Char('Name')


class hr_main_department(models.Model):
    _name = "hr.main.department"
    _description = "Main Department"

    name = fields.Char('Name')

# A model for Employee Work Experience
class hr_employee_work_experience(models.Model):
    _name = "hr.employee.work.experience"
    _description = "Work Experience"

    name = fields.Char('Name')
    address = fields.Char('Address')
    leave = fields.Char('Reason for Quit')
    salary = fields.Float('Salary (SDG)')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    applicant_id = fields.Many2one('hr.applicant', 'Employee')


# inheriting hr.department to add analytic account
class hr_department(models.Model):
    _inherit = 'hr.department'
    analytic_debit_account_id = fields.Many2one('account.analytic.account', string="Department Analytic Account")

# A model hr department 
class hr_main_department(models.Model):
    _name = "hr.main.department"
    _description = "Department"

    name = fields.Char('Name')
    department_id = fields.Many2one('hr.department', 'Department')
    manager_id = fields.Many2one('hr.employee', 'Manager')
    

# A Trainee model
class hr_trainee(models.Model):
    _name = "hr.trainee"
    _description = "Trainee"

    def _default_department(self):
        for rec in self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1):
            return rec.department_id

    def _default_main_department(self):
        for rec in self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1):
            return rec.main_department_id

    name = fields.Char('Trainee Name', required=True)
    trainee_type = fields.Selection([('trainee', 'Trainee'), ('national_service', 'National Service')], string='Type')
    address = fields.Char('Address')
    date_of_birth = fields.Date('Date of Birth')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status')
    educational_id = fields.Many2one('hr.educational.level', 'Educational Type')
    specialization = fields.Char('Specialization')
    work_experience = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Work Experience')
    experience_year = fields.Integer(string='Experience Year No')
    job_id = fields.Many2one('hr.job', 'Job Title')
    date_from = fields.Date('From')
    date_to = fields.Date('To')
    duration = fields.Char('Duration', compute='_get_duration')
    salary = fields.Float('Salary (SDG)')
    has_salary = fields.Boolean('Has Salary ?', default=True)
    department_id = fields.Many2one('hr.department', 'Department', default=_default_department)
    main_department_id = fields.Many2one('hr.main.department', 'Main Department', default=_default_main_department)
    reason = fields.Text('Reason')
    employee_account = fields.Many2one('account.account', string="Debit Account")

    d_comment = fields.Char('Department Manager Comment')
    t_comment = fields.Char('Training Manager Comment')
    hr_comment = fields.Char('Hr Manager Comment')
    hrg_comment = fields.Char('Hr General Manager Comment')

    dmanager_id = fields.Many2one('res.users', 'Department Manager', readonly=True)
    d_manager_id = fields.Many2one('res.users', 'Training Manager', readonly=True)
    dg_manager_id = fields.Many2one('res.users', 'Hr Manager', readonly=True)
    hrg_manager_id = fields.Many2one('res.users', 'Hr General Manager', readonly=True)

    state = fields.Selection(
        [('draft', 'Department Manager Approval'), ('dm', 'Training Manager Approval'), ('tm', 'Hr Manager Approval'),
         ('hr', 'Hr General Manager Approval'), ('gm', 'Done'), ('close', 'Close'), ('refuse', 'Refuse')],
        'Status', readonly=True, track_visibility='onchange', copy=False, default='draft')

    @api.onchange('date_from', 'date_to')
    def _date_validation(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                from_date = rec.date_from
                to_date = rec.date_to
                if from_date > to_date:
                    raise UserError(_("You must be enter start date less than end date !"))

    @api.depends('date_from', 'date_to')
    def _get_duration(self):
        experience = ''
        for employee in self:
            if employee.date_from and employee.date_to:
                str_now = datetime.strptime(str(employee.date_to), '%Y-%m-%d').date()
                date_start = datetime.strptime(str(employee.date_from), '%Y-%m-%d').date()
                total_days = (str_now - date_start).days
                number_of_days = int(total_days / 365)
                total_days = total_days - 365 * number_of_days
                employee_months = int(12 * total_days / 365)
                employee_days = int(0.5 + total_days - 365 * employee_months / 12)
                experience = str(number_of_days) + ' Year(s) ' + str(employee_months) + ' Month(s) ' + str(
                    employee_days) + ' day(s)'
            employee.duration = experience

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_('You are not allow to delete the Confirm and Done state records'))
        res = super(hr_trainee, self).unlink()
        return res

    @api.one
    def dm_approve(self):
        self.dmanager_id = self.env.uid
        if self.trainee_type == 'trainee':
            self.state = 'dm'
        elif self.trainee_type == 'national_service':
            self.state = 'tm'

    @api.one
    def tm_approve(self):
        self.d_manager_id = self.env.uid
        self.state = 'tm'

    @api.one
    def hm_approve(self):
        self.dg_manager_id = self.env.uid
        self.state = 'hr'

    @api.one
    def gm_approve(self):
        self.hrg_manager_id = self.env.uid
        self.state = 'gm'

    @api.one
    def refuse(self):
        self.state = 'refuse'

    @api.one
    def close(self):
        self.state = 'close'



# inheriting Hr Job
class hr_job(models.Model):
    _inherit = 'hr.job'
    main_department_id = fields.Many2one('hr.main.department', 'Main Department')
    start_date = fields.Date(string='Expected date To Start work')
    job_type = fields.Selection([('new', 'New'), ('replace', 'Replacement for the person leaving the company')], string='Job Type')
    job_nature = fields.Selection([('always', 'Always'), ('seasonal', 'Seasonal'), ('transverse', 'Transverse')], string='Nature of the job')
    english_level = fields.Selection([('junior', 'Junior'), ('average', 'Average'), ('advanced', 'Advanced'), ('not_required', 'not required')], string='English Level')
    word = fields.Boolean(string='Word')
    excel = fields.Boolean(string='Excel')
    powerpoint = fields.Boolean(string='PowerPoint')
    other = fields.Char(string='Other')
    professional_testing = fields.Selection([('not_required', 'not Required'), ('required', 'Required')], string='Professional testing')



# A model Employee Appraisal
class hr_emp_appraisal(models.Model):
    _name = "hr.emp.appraisal"
    _description = "Employee Appraisal"
    _rec_name = 'employee_id'

    user_id = fields.Many2one('res.users', 'Ordered by', readonly=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    job_id = fields.Many2one('hr.job', 'Job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id')
    main_department_id = fields.Many2one('hr.main.department', 'Main Department')
    date = fields.Date(string='Appraisal Date', default=fields.Date.today())
    hiring_date = fields.Date(string='Hiring From', related='employee_id.hiring_date')
    promotion_date = fields.Date(string='Last Promotion Date')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', related='employee_id.marital')
    children = fields.Integer('Children', related='employee_id.children')

    personal_features_ids = fields.One2many('hr.appraisal.personal.features', 'appraisal_id', string='Features')
    professional_experience_ids = fields.One2many('hr.appraisal.professional.experience', 'appraisal_id', string='Experience')
    performance_tasks_ids = fields.One2many('hr.appraisal.performance.tasks', 'appraisal_id', string='Tasks')

    qualifications = fields.Integer('Qualifications and training', compute='get_emp_apprisal')
    violations = fields.Integer('Violations and penalties', compute='get_emp_apprisal')
    disease = fields.Integer('Aranic disease', compute='get_emp_apprisal')

    features = fields.Integer('Personal Features', compute='get_features_degree')
    experience = fields.Integer('Professional and technical expertise', compute='get_experience_degree')
    tasks = fields.Integer('Professional and technical performance', compute='get_tasks_degree')

    total = fields.Integer('Total Degree', compute='get_total_degree')
    level = fields.Selection([
        ('excellent', 'Excellent'),
        ('vgood', 'Very Good'),
        ('good', 'Good'),
        ('medium', 'Medium'),
        ('weak', 'Weak')
    ], string='Level', compute='get_total_degree')

    members_ids = fields.Many2many('hr.employee', 'emp_member_rel', 'member_id', 'employee_id', 'Appraisal Members')
    state = fields.Selection(
        [('draft', 'Department Approval'), ('confirm', 'Confirm'), ('hr', 'Hr Manager'),
        ('hgm', 'Hr General Manager'), ('gm', 'General Manager'), ('done', 'Done'), ('refuse', 'Refuse')],
        'Status', readonly=True, track_visibility='onchange', copy=False, default='draft')
    dmanager_id = fields.Many2one('res.users', 'Direct Department Manager', readonly=True)
    d_manager_id = fields.Many2one('res.users', 'Department Manager', readonly=True)
    dg_manager_id = fields.Many2one('res.users', 'Hr Manager', readonly=True)
    hrg_manager_id = fields.Many2one('res.users', 'Hr General Manager', readonly=True)
    gm_manager_id = fields.Many2one('res.users', 'General Manager', readonly=True)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_('You are not allow to delete the Confirm and Done state records'))
        res = super(hr_emp_appraisal, self).unlink()
        return res

    @api.depends('employee_id')
    def get_emp_apprisal(self):
        for rec in self:
            if rec.employee_id:
                training_ids = self.env['hr.training.training.employees'].search([
                    ('employee_id', '=', rec.employee_id.id), ('attend', '=', True)])
                self.qualifications = len(training_ids)
                leave_ids = self.env['hr.holidays'].search([('type', '=', 'remove'),
                                                            ('state', '=', 'validate'),
                                                            ('hol_type', '=', 'disease'),
                                                            ('employee_id', '=', rec.employee_id.id)])
                self.disease = len(leave_ids)
                penalty_ids = self.env['hr.emp.penalty'].search([
                    ('employee_id', '=', rec.employee_id.id)])
                self.violations = len(penalty_ids)


    @api.one
    def d_approve(self):
        self.dmanager_id = self.env.uid
        self.state = 'confirm'

    # @api.one
    # def approve(self):
    #     self.d_manager_id = self.env.uid
    #     self.state = 'confirm'

    @api.one
    def to_hr(self):
        self.d_manager_id = self.env.uid
        self.state = 'hr'

    @api.one
    def to_hgm(self):
        self.dg_manager_id = self.env.uid
        self.state = 'hgm'

    @api.one
    def to_gm(self):
        self.hrg_manager_id = self.env.uid
        self.state = 'gm'

    @api.one
    def done(self):
        self.gm_manager_id = self.env.uid
        self.state = 'done'

    @api.one
    def refuse(self):
        self.state = 'refuse'

    @api.one
    def reset(self):
        self.state = 'draft'

    @api.depends('personal_features_ids')
    def get_features_degree(self):
        for rec in self:
            features = 0
            degree = 0
            for line in rec.personal_features_ids:
                if line.level == 'excellent':
                    degree = 5
                if line.level == 'vgood':
                    degree = 4
                if line.level == 'good':
                    degree = 3
                if line.level == 'medium':
                    degree = 2
                if line.level == 'weak':
                    degree = 1
                features = degree + features
            self.features = features

    @api.depends('professional_experience_ids')
    def get_experience_degree(self):
        for rec in self:
            features = 0
            degree = 0
            for line in rec.professional_experience_ids:
                if line.level == 'excellent':
                    degree = 5
                if line.level == 'vgood':
                    degree = 4
                if line.level == 'good':
                    degree = 3
                if line.level == 'medium':
                    degree = 2
                if line.level == 'weak':
                    degree = 1
                features = degree + features
            self.experience = features

    @api.depends('performance_tasks_ids')
    def get_tasks_degree(self):
        for rec in self:
            features = 0
            degree = 0
            for line in rec.performance_tasks_ids:
                if line.level == 'excellent':
                    degree = 5
                if line.level == 'vgood':
                    degree = 4
                if line.level == 'good':
                    degree = 3
                if line.level == 'medium':
                    degree = 2
                if line.level == 'weak':
                    degree = 1
                features = degree + features
            self.tasks = features

    @api.depends('features', 'experience', 'tasks', 'qualifications', 'violations', 'disease')
    def get_total_degree(self):
        total = self.qualifications + self.violations + self.disease + self.features + self.experience + self.tasks
        self.total = total
        if total >= 90 and total <= 100:
            self.level = 'excellent'
        elif total >= 79 and total <= 89:
            self.level = 'vgood'
        elif total >= 68 and total <= 78:
            self.level = 'good'
        elif total >= 57 and total <= 67:
            self.level = 'medium'
        elif total <= 56:
            self.level = 'weak'


#######################
class hr_appraisal_features(models.Model):
    _name = "hr.appraisal.features"
    _description = "features"

    name = fields.Char('feature')

class hr_appraisal_personal_features(models.Model):
    _name = "hr.appraisal.personal.features"
    _description = "Features"

    name = fields.Many2one('hr.appraisal.features', 'feature')
    level = fields.Selection([
        ('excellent', 'Excellent'),
        ('vgood', 'Very Good'),
        ('good', 'Good'),
        ('medium', 'Medium'),
        ('weak', 'Weak')
    ], string='Level')

    appraisal_id = fields.Many2one('hr.emp.appraisal', 'Appraisal')

#######################
class hr_appraisal_experience(models.Model):
    _name = "hr.appraisal.experience"
    _description = "Experience"

    name = fields.Char('feature')

class hr_appraisal_professional_features(models.Model):
    _name = "hr.appraisal.professional.experience"
    _description = "Professional Experience"

    name = fields.Many2one('hr.appraisal.experience', 'Experience')
    level = fields.Selection([
        ('excellent', 'Excellent'),
        ('vgood', 'Very Good'),
        ('good', 'Good'),
        ('medium', 'Medium'),
        ('weak', 'Weak')
    ], string='Level')
    appraisal_id = fields.Many2one('hr.emp.appraisal', 'Appraisal')

#######################
class hr_appraisal_tasks(models.Model):
    _name = "hr.appraisal.tasks"
    _description = "Tasks"

    name = fields.Char('Tasks')

class hr_appraisal_performance_tasks(models.Model):
    _name = "hr.appraisal.performance.tasks"
    _description = "Performance Tasks"

    name = fields.Many2one('hr.appraisal.tasks', 'Tasks')
    level = fields.Selection([
        ('excellent', 'Excellent'),
        ('vgood', 'Very Good'),
        ('good', 'Good'),
        ('medium', 'Medium'),
        ('weak', 'Weak')
    ], string='Level')
    appraisal_id = fields.Many2one('hr.emp.appraisal', 'Appraisal')


################################
# hr.incentives
class HrIncentives(models.Model):
    _name = 'hr.incentives'

    name = fields.Char(string='Name', required=True)
    date = fields.Date(string='Date', default=fields.Date.today(), required=True)
    tax = fields.Float("Tax Amount %", default=10)
    amount = fields.Float('Incentives Amount')
    duration = fields.Integer(string="No Of Month", default=1)
    lta_transport_ids = fields.One2many('hr.incentives.line', 'lta_transport_id', string='Transport and LTA')
    journal_id = fields.Many2one('account.journal', string="Journal")
    debit_account = fields.Many2one('account.account', string="Debit Account")
    credit_account = fields.Many2one('account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    @api.onchange('date')
    def onchange_date(self):
        for x in self:
            ttyme = datetime.fromtimestamp(time.mktime(time.strptime(x.date, "%Y-%m-%d")))
            locale = self.env.context.get('lang', 'en_US')
            x.name = _('Grant for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))

    @api.one
    def action_approve(self):
        self.state = 'approve'
        for grant_id in self.lta_transport_ids:
            grant_id.state = 'approve'

    @api.one
    def action_refuse(self):
        self.state = 'refuse'
        for grant_id in self.lta_transport_ids:
            grant_id.state = 'refuse'

    @api.one
    def action_reset(self):
        self.state = 'draft'
        for grant_id in self.lta_transport_ids:
            grant_id.state = 'draft'

    @api.one
    def action_done(self):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        loan_ids = []
        amount_sum = 0.0
        for lta in self:
            lta_approve_date = fields.Date.today()
            journal_id = lta.journal_id.id
            reference = lta.name
            created_move_ids = []
            loan_ids = []

            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            for lta_transport_id in lta.lta_transport_ids:
                amount_sum += lta_transport_id.total_net

            lta_name = 'Transport and LTA payment of ' + reference
            move_dict = {
                'narration': reference,
                'ref': reference,
                'journal_id': journal_id,
                'date': lta_approve_date,
            }

            debit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.debit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount_sum > 0.0 and amount_sum or 0.0,
                'credit': amount_sum < 0.0 and -amount_sum or 0.0,
                'analytic_account_id': lta.analytic_debit_account_id.id,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.credit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount_sum < 0.0 and -amount_sum or 0.0,
                'credit': amount_sum > 0.0 and amount_sum or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            lta.write({'move_id': move.id, 'done_date': lta_approve_date})
            move.post()
        self.state = 'done'

    @api.multi
    def unlink(self):
        for x in self:
            if any(x.filtered(lambda HrIncentives: HrIncentives.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete allowance & bonus batch which is not draft or refused!'))
            return super(HrIncentives, x).unlink()


class HrIncentivesLine(models.Model):
    _name = 'hr.incentives.line'

    name = fields.Char(string='Name', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    contract_id = fields.Many2one('hr.contract', related='employee_id.contract_id', string='Contract')
    date = fields.Date(string='Date', default=fields.Date.today())
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', readonly=True,
                                    string="Department")
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', readonly=True, string="Job Position")
    code = fields.Char(string='Code', related='employee_id.code', readonly=True)
    amount = fields.Float('Incentives Amount')
    # tax_amount = fields.Float('Taxed Amount', compute='get_total_net')
    total_net = fields.Float('Total')
    duration = fields.Integer(string="No Of Month", default=1)
    journal_id = fields.Many2one('account.journal', string="Journal")
    debit_account = fields.Many2one('account.account', string="Debit Account")
    credit_account = fields.Many2one('account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account',
                                                related='department_id.analytic_debit_account_id',
                                                string="Analytic Account", readonly=True)
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    lta_transport_id = fields.Many2one('hr.incentives', string='LTA Transport', ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('done', 'Done'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    # @api.depends('amount')
    # def get_total_net(self):
    #     for rec in self:
    #         tax = self.amount * (rec.lta_transport_id.tax / 100)
    #         rec.tax_amount = tax
    #         rec.total_net = (self.amount * self.duration) - tax

    @api.one
    def action_approve(self):
        self.state = 'approve'

    @api.one
    def action_refuse(self):
        self.state = 'refuse'

    @api.one
    def action_reset(self):
        self.state = 'draft'

    @api.multi
    def unlink(self):
        for x in self:
            if any(x.filtered(lambda HrIncentivesLine: HrIncentivesLine.state not in ('draft', 'refuse'))):
                raise UserError(_('You cannot delete a allowance & LTA which is not draft or refused!'))
        return super(HrIncentivesLine, self).unlink()

    @api.one
    def action_done(self):
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        loan_ids = []
        for lta in self:
            lta_approve_date = fields.Date.today()
            amount = lta.total_net
            lta_name = 'additional amounts For ' + lta.employee_id.name
            reference = lta.name
            journal_id = lta.journal_id.id
            created_move_ids = []
            loan_ids = []

            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            move_dict = {
                'narration': lta_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': lta_approve_date,
            }

            debit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.debit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': lta.analytic_debit_account_id.id,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': lta_name,
                'partner_id': False,
                'account_id': lta.credit_account.id,
                'journal_id': journal_id,
                'date': lta_approve_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            lta.write({'move_id': move.id, 'done_date': lta_approve_date})
            move.post()
        self.state = 'done'
    

    @api.onchange('employee_id', 'date')
    def onchange_employee(self):
        if (not self.employee_id) or (not self.date):
            return
        employee = self.employee_id
        date_from = self.date
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        locale = self.env.context.get('lang', 'en_US')
        self.name = _('Additional Amounts %s for %s') % (
        employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))

    @api.constrains('name')
    def _no_duplicate_payslips(self):
        if self.employee_id:
            payslip_obj = self.search([('employee_id', '=', self.employee_id.id), ('name', '=', self.name),('state', '=', 'done')])
            if payslip_obj:
                raise Warning(_("This Employee Already Took his Month's Allowance!"))




