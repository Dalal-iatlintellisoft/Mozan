# -*- coding: utf-8 -*-
###########

from odoo import fields, models, api, tools, _
from openerp.exceptions import ValidationError
import xlsxwriter
import base64
import datetime
# from cStringIO import StringIO
from datetime import *
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import os
from odoo.exceptions import UserError
from dateutil import relativedelta
from io import BytesIO

class WizardOvertime(models.Model):
    _name = 'wizard.paysheet'
    _description = 'Print Payslip'

    # payslip_report = fields.Binary(string='s')
    # payslip_report_name = fields.Char(string='Payslip Name', default='Pay sheet Report.xls')
    from_date = fields.Date(string='Date From', required=True)
        # default=time.strftime('%Y-%m-01'))
    to_date = fields.Date(string='Date To', required=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          )
    name = fields.Char(string="Payslip")

    @api.multi
    def print_report(self):
        for report in self:
            from_date = report.from_date
            to_date = report.to_date
            if self.from_date > self.to_date:
                raise UserError(_("You must be enter start date less than end date !"))
            report.name = 'Pay Sheet From ' + from_date + ' To ' + to_date
            report_title = 'Salaries From ' + from_date + ' To ' + to_date
            file_name = _('Pay Sheet.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Pay Sheet')
            excel_sheet.right_to_left()
            header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#808080', 'border': 1})
            header_format_sequence = workbook.add_format({'bold': False, 'font_color': 'black', 'bg_color': 'white','border': 1})
            format = workbook.add_format({'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format({'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            title_format.set_align('center')
            format.set_align('center')
            header_format_sequence.set_align('center')
            header_format.set_align('center')
            header_format.set_text_wrap()
            excel_sheet.set_row(5, 20)
            excel_sheet.set_column('F:U', 20,)
            format.set_text_wrap()
            format.set_num_format('#,##0.00')
            format_details = workbook.add_format()
            format_details.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 5
            first_row = 7
            excel_sheet.write(row, col, '#',  header_format)
            col += 1
            excel_sheet.write(row, col, 'Name', header_format)
            col += 1
            excel_sheet.write(row, col, 'Department', header_format)
            col += 1
            excel_sheet.write(row, col, 'Job Description', header_format)
            col += 1
            excel_sheet.write(row, col, 'Primary', header_format)
            col += 1
            excel_sheet.write(row, col, 'Cola', header_format)
            col += 1
            excel_sheet.write(row, col, 'Transportation', header_format)
            col += 1
            excel_sheet.write(row, col, 'Housing', header_format)
            col += 1
            excel_sheet.write(row, col, 'Soc In 8%', header_format)
            col += 1
            excel_sheet.write(row, col, 'Soc In 17%', header_format)
            # col += 1
            # excel_sheet.write(row, col, 'Zakat 2.5 %', header_format)
            col += 1
            excel_sheet.write(row, col, 'PIT 15%', header_format)
            col += 1
            excel_sheet.write(row, col, 'Short Loan', header_format)
            col += 1
            excel_sheet.write(row, col, 'Long Loan', header_format)
            col += 1
            excel_sheet.write(row, col, 'Stamp', header_format)
            col += 1
            excel_sheet.write(row, col, 'Total Ded', header_format)
            col += 1
            excel_sheet.write(row, col, 'Net Salaries ', header_format)
            col += 1
            excel_sheet.write(row, col, 'Gross', header_format)
            col += 1
            excel_sheet.write(row, col, 'Bonus', header_format)
            # col += 1
            # excel_sheet.write(row, col, 'Total Salary', header_format)

            excel_sheet.set_column(0, 4, 25)
            excel_sheet.set_row(1, 25)
            excel_sheet.merge_range(0, 0, 1, 10, 'Mozan CO. ', title_format)
            excel_sheet.merge_range(2, 0, 3, 10,report_title , title_format)
            excel_sheet.merge_range(3, 0, 4, 10,'' , title_format)
            payslip_month_ids = report.env['hr.payslip'].search(
                [('date_to', '<=', to_date), ('date_from', '>=', from_date), ('state', '=', 'done')])
            for payslip_period in payslip_month_ids:
                slip_id = payslip_period.id
                employee = payslip_period.employee_id.id
                employee_name = payslip_period.employee_id.name
                department_name = payslip_period.employee_id.department_id.name
                job_name = payslip_period.employee_id.job_id.name
                col = 0
                row += 1
                sequence_id += 1
                excel_sheet.write(row, col, sequence_id, header_format_sequence)
                col += 1

                if employee_name:
                    excel_sheet.write(row, col, employee_name, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if department_name:
                    excel_sheet.write(row, col, department_name, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if job_name:
                    excel_sheet.write(row, col, job_name, format)
                else:
                    excel_sheet.write(row, col, '', format)
                slip_ids = payslip_period.env['hr.payslip.line'].search([('slip_id', '=', slip_id),
                                                                         ('employee_id', '=', employee)])
                primary = 0.0
                cola = 0.0
                long_loan = 0.0
                transport = 0.0
                social_ins = 0.0
                sh_loan = 0.0
                net = 0.0
                penalties_deduction =0.0
                health_insurance = 0.0
                other_deduction = 0.0
                comp_socialIns = 0.0
                per_income = 0.0
                stamp = 0.0
                tot_deduction = 0.0
                net = 0.0
                incentive = 0.0
                Salary = 0.0
                housing = 0.0
                gross = 0.0



                for slip_line in slip_ids:
                    category = slip_line.code
                    if category == 'PRIMARY':
                        primary = slip_line.total
                        print('prim',primary)
                    if category == 'COLA':
                        cola = slip_line.total
                    if category == 'TANSPORT':
                        transport = slip_line.total
                    if category == 'HOUSING':
                        housing = slip_line.total
                    if category == 'SocialIns':
                        social_ins = slip_line.total
                    if category == 'comp_SocialIns':
                        comp_socialIns = slip_line.total
                    if category == 'pit':
                        per_income = slip_line.total
                    if category == 'SHLOAN':
                        sh_loan = slip_line.total
                    if category == 'LOLOAN':
                        long_loan = slip_line.total
                    if category == 'stamp':
                        stamp = slip_line.total
                    if category == 'tot_ded':
                        tot_deduction = slip_line.total
                    if category == 'NET':
                        net = slip_line.total
                    if category == 'GROSS':
                        gross = slip_line.total
                        print('dfghjk',gross)
                    if category == 'incen':
                        incentive = slip_line.total
                    if category == 'Warning':
                        penalties_deduction = slip_line.total
                    # if category == 'slry':
                    #     print('HHHHHHHHHHHHHHHHH')
                    #     Salary = slip_line.total


                    col = 4

                    if primary:
                        print('here',primary)
                        excel_sheet.write(row, col, primary, format)
                    col += 1
                    if cola:
                        excel_sheet.write(row, col, cola, format)
                    col += 1
                    if transport:
                        excel_sheet.write(row, col, transport, format)
                    col += 1
                    if housing:
                        excel_sheet.write(row, col, housing, format)
                    col += 1
                    if social_ins:
                        excel_sheet.write(row, col, social_ins, format)
                    col +=1
                    excel_sheet.write(row, col, comp_socialIns, format)
                    col += 1
                    excel_sheet.write(row, col, per_income, format)
                    col += 1
                    excel_sheet.write(row, col, sh_loan, format)
                    col += 1
                    excel_sheet.write(row, col, long_loan, format)
                    col += 1
                    excel_sheet.write(row, col, stamp, format)
                    col += 1
                    excel_sheet.write(row, col, tot_deduction, format)
                    col += 1
                    excel_sheet.write(row, col, net, format)
                    col += 1
                    excel_sheet.write(row, col, gross, format)
                    col += 1
                    excel_sheet.write(row, col, incentive, format)



        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()
        wizardmodel = self.env['payslip.report.excel']
        res_id = wizardmodel.create({'name': file_name, 'file_download': file_download})
        return {
            'name': 'Files to Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payslip.report.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': res_id.id,
        }

    ############################################
    class payslip_report_excel(models.TransientModel):
        _name = 'payslip.report.excel'

        name = fields.Char('File Name', size=256, readonly=True)
        file_download = fields.Binary('File to Download', readonly=True)
