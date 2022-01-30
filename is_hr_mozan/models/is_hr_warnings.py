from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
class warning_management(models.Model):
    _name = 'hr.warnings'
    _description = 'Warning Management'
    name = fields.Char('warnings' , compute ='compute_string', required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee",  required=True)
    warning= fields.Many2one('warning.warning', string ='Warning Name ',  required=True)
    leval = fields.Selection(
        [('first', ' first penalty'),
      ('second', ' second penalty'),
      ('third', ' third penalty'),
      ('Fourth', 'Fourth penalty'),
      ('fifth', ' fifth penalty')],string ='leval', required=True)

    explanation_date = fields.Date("Explanation Form Date")
    explanation = fields.Text("Reason")
    warning_date = fields.Date("Warning Date", required=True, default=fields.date.today())
    pen_type = fields.Many2one('penalty.penalty', string = 'penalty' , compute='_get_pen_type')
    deduct_dayes = fields.Float( string ='Deduct Dayes' )
    deduct_amount = fields.Float( string ='Deduct Amount' , compute='_get_penalty')

    pen_desc = fields.Text("Penalty Description")
    improvement_steps = fields.Text( string = 'Steps for improvement')
    state = fields.Selection([('draft', 'To Submit'),('confirm', 'Submitted'), ('refuse', 'Refused'),
         ('seen', 'Seen By Employee'), ('hr', 'HR Approval'),('penalty_approval', 'Done')],
        'Status', readonly=True, track_visibility='onchange', copy=False,
        help='The status is set to \'To Submit\', when a Warring request is created.\
                      \nThe status is \'To Approve\', when Warring request is confirmed by user.\
                      \nThe status is \'Refused\', when Warring request is refused by manager.\
                      \nThe status is \'Approved\', when Warring request is approved by manager.', default="draft")
    wage = fields.Float( strin ="Old salary" , related = "employee_id.contract_id.wage",required=True)
    hr_notes = fields.Text( string ='HR Notes')

    @api.depends('warning', 'leval')
    def _get_pen_type(self):
        for pen in self:
            if pen.warning:
                warnings = pen.env['penalty.penalty'].search(
                    [('warnings_id', '=', pen.warning.id), ('leval', '=', pen.leval)])
                self.pen_type = warnings
                for x in warnings:
                    if x.name:
                        x.deduct_dayes = self.deduct_dayes


    @api.depends('warning_date','employee_id')
    def compute_string(self):
        for x in self:
            if x.employee_id:
                x.name = 'WAR' + ' ' +x.employee_id.name+ str(x.warning_date)

    @api.constrains('employee_id', 'warning','leval')
    def _emp_warnings(self):
        for warnings in self:
            if warnings.warning:
                first_warnings_ids = warnings.env['hr.warnings'].search(
                    [('employee_id', '=', warnings.employee_id.id),
                     ('warning', '=', warnings.warning.id),
                     ('leval', '=', warnings.leval),
                   ])

                if len(first_warnings_ids) >1:
                    for x in first_warnings_ids:
                            raise Warning(_("This Employee Already Took Thes warnings"))


    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.warnings') or ' '
        res = super(warning_management, self).create(values)
        return res

    @api.one
    def warning_seen(self):
        self.state = 'seen'

    @api.one
    def warning_submit(self):
        self.state = 'confirm'

    @api.one
    def warning_hr_approval(self):
        self.state = 'hr'

    @api.one
    def warning_penalty_approval(self):
        self.state = 'penalty_approval'

    @api.one
    def warning_refuse(self):
        self.state = 'refuse'

    @api.one
    def warning_reset(self):
        self.state = 'draft'


    @api.depends('deduct_dayes','wage')
    def _get_penalty(self):
        for deduct in self:
            pre_day = self.wage/30
            deduct_cost = self.deduct_dayes*pre_day
            self.deduct_amount = deduct_cost


class warning_warnings(models.Model):
    _name = 'warning.warning'
    _description = 'Warning Management'
    name = fields.Char('warnings' ,required=True)
    penalty_ids = fields.One2many('penalty.penalty','warnings_id',string = 'Penalty')

class penalty_penalty(models.Model):
    _name = 'penalty.penalty'
    _description = 'penalty Management'
    name = fields.Char('Penalty Name' ,required=True)
    leval = fields.Selection(
        [('first', ' first penalty'),
         ('second', ' second penalty'),
         ('third', ' third penalty'),
         ('Fourth', 'Fourth penalty'),
         ('fifth', ' fifth penalty')], string='leval',required=True)

    deduct = fields.Boolean( string = 'Deduct From Salary')
    deduct_dayes= fields.Float( string = 'Deduct Days ')
    warnings_id = fields.Many2one( 'warning.warning', string ='Warnings')







