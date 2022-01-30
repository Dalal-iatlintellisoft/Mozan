from datetime import datetime
from dateutil import relativedelta
import time
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.osv import osv


class hr_employee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def create(self, vals):
        res = super(hr_employee, self).create(vals)
        next_seq = self.env['ir.sequence'].get('employee.ref')
        res.update({'staff_no': next_seq})
        return res


    @api.model
    @api.one
    def _compute_loans(self):
        for x in self:
            count = 0
            loan_remain_amount = 0.00
            loan_ids = x.env['hr.loan'].search([('employee_id', '=', x.id)])
            for loan in loan_ids:
                loan_remain_amount += loan.balance_amount
                count += 1
            x.loan_count = count
            x.loan_amount = loan_remain_amount

    @api.model
    @api.one
    def _compute_trip(self):
        for x in self:
            count = 0
            trip_remain_amount = 0.00
            trip_ids = x.env['hr.trip'].search([('employee_id', '=', x.id)])
            for trip in trip_ids:
                trip_remain_amount += trip.balance_amount
                count += 1
            x.loan_count = count
            x.loan_amount = trip_remain_amount

    is_manager = fields.Boolean(string="Is Manager")
    loan_amount = fields.Float(string="loan Amount", compute='_compute_loans')
    loan_count = fields.Integer(string="Loan Count", compute='_compute_loans')
    hiring_date = fields.Date(string="Date of Joining")
    quit_date = fields.Date(string="Date of Quit")
    staff_no = fields.Char('Staff no')
    hr_loan_request_id = fields.Many2one('hr.loan.request' ,string ='request')
    leave_balance = fields.Float(string='Leave Balance', compute='_compute_leave_balance')
    annual_leave = fields.Float(string="Annual Leave")
    local_leave = fields.Float(string=" Full Local Leave", default='86400')
    local_remaining_leaves = fields.Float( string =' local leaves')
    local_leave_balance = fields.Float(string=' Local Leave Balance', compute='_compute_localleave_balance')
    blood = fields.Selection([('o1', 'O+'), ('o2', 'O-'), ('a1', 'A+'), ('a2', 'A-'), ('b1', 'B+'), ('b2', 'B-'),
                              ('ab1', 'AB+'), ('ab2', 'AB-')])
    mother_name = fields.Char(string='Mother Name')
    code = fields.Char(string='Employee Code')
    national_service_from = fields.Date(string='Date From')
    national_service_to = fields.Date(string='Date To')
    graduation_year = fields.Date(string='Graduation Year')
    signature = fields.Binary(string='Signature')
    year_experience = fields.Integer(string='Years of Experience')
    month_experience = fields.Integer(string='Months of Experience')
    age_in_years = fields.Integer(string='Age In Years', compute='_calculate_age')
    family_member_ids = fields.One2many('family.member','employee_id', string=' Family Members')
    edu_level_id = fields.Many2one('educational.level', string='Degree')
    edu_section_id = fields.Many2one('education.section', string='Section',
                                     domain="[('education_level_id', '=', edu_level_id)]")
    age = fields.Char(compute='_calculate_age', string='Age')
    qualifications_ids = fields.One2many('qualifications','employee_id', string ='Qualifications')
    skills_ids = fields.One2many('skills','employee_id', string ='skills and Tranning')
    insurance_class = fields.Selection([('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
                                       string='Insurance Class')
    visa_date = fields.Date( string ='Visa Date')
    renew_date = fields.Date( string ='Renew Date')
    visa = fields.Char(compute='_calculate_visa', string='Visa')
    renew = fields.Boolean(compute='_calculate_visa' , string=' For Renew ')
    foreigner = fields.Boolean( string=' IS Foreigner ')
    @api.depends('visa_date')
    def _calculate_visa(self):
        str_now = datetime.datetime.now().date()
        visa = ''
        employee_years = 0
        for employee in self:
            if employee.visa_date:
                date_start = datetime.datetime.strptime(str(employee.visa_date), '%Y-%m-%d').date()
                # renew = datetime.datetime.strptime(str(employee.renew_date), '%Y-%m-%d').date()

                total_days = (str_now - date_start).days
                employee_years = int(total_days / 365)
                remaining_days = total_days - 365 * employee_years
                employee_months = int(12 * remaining_days / 365)
                employee_days = int(0.5 + remaining_days - 365 * employee_months / 12)
                visa = str(employee_years) + ' Year(s) ' + str(employee_months) + ' Month(s) ' + str(
                    employee_days) + ' day(s)'
                if employee.visa_date>employee.renew_date:
                    employee.renew= True
            employee.visa = visa


            # employee.age_in_years = employee_years

    @api.depends('remaining_leaves')
    def _compute_leave_balance(self):
        for leave in self:
            if leave.remaining_leaves:
                remaining_leaves = leave.remaining_leaves
                leave.leave_balance = remaining_leaves


    @api.depends('local_remaining_leaves','local_leave')
    def _compute_localleave_balance(self):
        for x in self:
            x.local_leave_balance= x.local_leave-float(x.local_remaining_leaves)

    @api.depends('birthday')
    def _calculate_age(self):
        str_now = datetime.datetime.now().date()
        age = ''
        employee_years = 0
        for employee in self:
            if employee.birthday:
                date_start = datetime.datetime.strptime(str(employee.birthday), '%Y-%m-%d').date()
                total_days = (str_now - date_start).days
                employee_years = int(total_days / 365)
                remaining_days = total_days - 365 * employee_years
                employee_months = int(12 * remaining_days / 365)
                employee_days = int(0.5 + remaining_days - 365 * employee_months / 12)
                age = str(employee_years) + ' Year(s) ' + str(employee_months) + ' Month(s) ' + str(
                    employee_days) + ' day(s)'
            employee.age = age
            employee.age_in_years = employee_years


class EduactionSection(models.Model):
    _name = 'education.section'
    name = fields.Char(string='Section')
    education_level_id = fields.Many2one('educational.level', string='Level')


class EducationalLevel(models.Model):
    _name = 'educational.level'
    name = fields.Char(string='Educational Level')
    edu_section_ids = fields.One2many('education.section', 'education_level_id', string='Section')

class family_member(models.Model):
    _name = 'family.member'
    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    birthday = fields.Date( string ='birthday')
    gender = fields.Selection([('Male','male'),('Female','female')])
    relation = fields.Selection(
        [('mother', 'Mother'), ('father', 'father '), ('son', 'Son/daughter'),
         ('wife', 'wife')])

class qualifications(models.Model):
    _name = 'qualifications'
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    name = fields.Selection(
        ([('bachelor', 'Bachelor '), ('higher_diploma', 'Higher Diploma '), ('master', 'Master '),('doctorate', 'Doctorate ')])
        ,string ='qualifications', required=True)
    degree = fields.Char( string ='Degree')
    date = fields.Date( string ='Date')
    university = fields.Char(string ='the University')

class skills(models.Model):
    _name = 'skills'
    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char( string='Name')
    degree = fields.Char(string='Degree')
    date = fields.Date(string='Date')
    center = fields.Char(string='Center Name')

# hr_contract hr_contract

class hr_contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def create(self, vals):
        res = super(hr_contract, self).create(vals)
        next_seq = self.env['ir.sequence'].get('contract.ref')
        res.update({'name': next_seq})
        return res

    eligible_si = fields.Boolean(string='Eligible For Social Insurance', default=True)
    legal_leave = fields.Selection(
        [('20', '20 day'), ('25', '25 day'),
         ('30', '30 day')], string='Legal Leave')
    grade = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'),
         ('10', '10')],compute='employee_legal_leave', string='Grade')
    gross_salary = fields.Float(string='Gross Salary')
    basic_salary = fields.Float(string='Basic Salary')
    cola = fields.Float(string='Cola')
    transport = fields.Float(string='Transport')
    housing = fields.Float(string='Housing')
    overtime = fields.Float(string='Overtime')
    total_incentive = fields.Float(string='Total Bonus',compute = 'compute_total_incentive',store=True)
    total_alwn = fields.Float(string=' Total Allownce' , compute='compute_allwnce')
    wage = fields.Float(string='Wage' , compute='compute_salary')
    Leave_allownce = fields.Float(string ='Leave Allownce')
    ramadan_allownce = fields.Float(string ='Ramadan')
    fitr_allownce = fields.Float(string ='Eid Fitr ')
    adha_allownce = fields.Float(string ='Eid Adha ')
    incentive = fields.Float('Bonus')

    @api.depends('incentive')
    def compute_total_incentive(self):
        for x in self:
            if x.incentive:
                x.total_incentive = x.incentive * 12

    @api.depends('gross_salary')
    def compute_salary(self):
        for x in self:
            if x.employee_id:
                x.wage =x.gross_salary + x.total_incentive/12

    @api.depends('Leave_allownce', 'ramadan_allownce', 'fitr_allownce','adha_allownce')
    def compute_allwnce(self):
        for x in self:
            if x.employee_id:
                x.total_alwn = x.ramadan_allownce + x.fitr_allownce + x.adha_allownce+x.Leave_allownce


    @api.depends('type_id')
    def employee_legal_leave(self):
        for x in self:
            if x.employee_id:
                type = x.type_id.name
                legal_leave = x.legal_leave
                if type == 'Employee':
                    self.legal_leave = '20'
                    update_leave = x._cr.execute("UPDATE hr_employee set annual_leave=%s"
                                                 " WHERE id= %s", (20, x.employee_id.id))
                elif legal_leave == '30':
                    update_leave = x._cr.execute("UPDATE hr_employee set annual_leave =%s"
                                                 "  WHERE id= %s", (30, x.employee_id.id))
                else:
                    legal_leave = '45'
                    update_leave = x._cr.execute("UPDATE hr_employee set annual_leave=%s"
                                                 "WHERE id= %s", (45, x.employee_id.id))

# hr_holidays

class hr_holidays(models.Model):
    _inherit = "hr.holidays"


    @api.constrains('date_to', 'date_from')
    def _check_date(self):
        for holiday in self:
            employement_period = 0.0
            date_from = str(holiday.date_from)
            if holiday.holiday_status_id.id == 1 and holiday.type != 'add':
                date_from = holiday.date_from
                d = datetime.datetime.strptime(date_from, DEFAULT_SERVER_DATETIME_FORMAT)
                date_from = str(d.date())
                if holiday.date_from:
                    employee_id = holiday.employee_id.id
                    hr_employee = holiday.env['hr.employee'].search([('id', '=', employee_id)])
                    if not hr_employee.hiring_date:
                        raise UserError(_('Please Add employee Hiring date!'))
                    hiring = str(hr_employee.hiring_date)
                    holiday_to = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                    hiring_date = datetime.datetime.strptime(hiring, '%Y-%m-%d')
                    employement_period = (holiday_to - hiring_date).days
                    if employement_period < 365.25:
                        raise UserError(_('You can not request leave before you complete Year!'))


