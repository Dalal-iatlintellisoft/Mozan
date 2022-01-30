# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools, _
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
import datetime
# from cStringIO import StringIO
from datetime import *
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import os
# from odoo.exceptions import UserError
from odoo.exceptions import Warning as UserError

from dateutil import relativedelta
from io import BytesIO

class wizard_costing_report(models.Model):
    _name = 'wizard.costing.report'
    _description = 'Costing Product '

    start_date = fields.Date('Date From', required=True)
    end_date = fields.Date('Date To', required=True)
    product_id = fields.Many2one('product.product', 'Product')

    @api.multi
    def print_report(self):
        for report in self:
            # logo = report.env.user.company_id.company_header
            start_date = report.start_date
            end_date = report.end_date
            product_id = report.product_id.id
            if report.start_date > report.end_date:
                raise UserError(_("You must be enter start date less than end date !"))
            # report_title = ' Activiteis From ' + from_date + ' to ' + to_date
            file_name = _('Costing Report.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Costing Report')
            # image_data = BytesIO(base64.b64decode(logo))  # to convert it to base64 file
            # excel_sheet.insert_image('B1', 'logo.png', {'image_data': image_data})

            header_format = workbook.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#0080ff', 'border': 1})
            header_format_sequence = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            format = workbook.add_format({'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format = workbook.add_format({'bold': True, 'font_color': 'black', 'bg_color': 'white'})
            header_format.set_align('center')
            header_format.set_align('vertical center')
            header_format.set_text_wrap()
            format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1, 'font_size': '10'})
            title_format = workbook.add_format({'bold': True, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            title_format.set_align('center')
            format.set_align('left')
            header_format_sequence.set_align('center')
            format.set_text_wrap()
            format_details = workbook.add_format()
            sequence_format = workbook.add_format(
                {'bold': False, 'font_color': 'black', 'bg_color': 'white', 'border': 1})
            sequence_format.set_align('center')
            sequence_format.set_text_wrap()
            total_format = workbook.add_format(
                {'bold': True, 'font_color': 'black', 'bg_color': '#808080', 'border': 1, 'font_size': '10'})
            total_format.set_align('center')
            total_format.set_text_wrap()
            format.set_num_format('#,##0.00')
            sequence_id = 0
            col = 0
            row = 3
            first_row = 13
            total_qty_deliverd = 0
            # excel_sheet.write_merge(0, 5, 1, 5, report_title, style_header_thin_all_main1)
            # excel_sheet.merge_range(10, 1, 10, 5, report_title, title_format)
            excel_sheet.set_column(col, col, 5)
            excel_sheet.write(row, col, '#', header_format)
            col += 1
            excel_sheet.set_column(col, col, 15)
            excel_sheet.write(row, col, 'Date', header_format)
            col += 1
            excel_sheet.set_column(col, col, 45)
            excel_sheet.write(row, col, 'Product', header_format)
            col += 1
            excel_sheet.set_column(col, col, 15)
            excel_sheet.write(row, col, 'Virtual Cost', header_format)
            col += 1
            excel_sheet.set_column(col, col, 15)
            excel_sheet.write(row, col, 'Actual Cost', header_format)
            col += 1
            excel_sheet.set_column(col, col, 15)
            excel_sheet.write(row, col, 'Sales Cost', header_format)
            excel_sheet.merge_range(1, 1, 1, 4, 'Costing Report', title_format)
            report_title = ' Date From ' + start_date + ' to ' + end_date
            excel_sheet.merge_range(2, 2, 2, 4, report_title, title_format)
            if self.product_id:
                product_ids = self.env['product.log.category'].search(
                    [('date', '>=', start_date), ('date', '<=', end_date),('product_id', '=', product_id)])
            else:
                product_ids = self.env['product.log.category'].search(
                    [('date', '>=', start_date), ('date', '<=', end_date)])
            if product_ids:
                for log in product_ids:
                    name = log.product_id.name

                    # raise UserError(_("You must be enter start date less than end date(%s,) !")% (name))
                    date = log.date
                    actual_cost = log.actual_cost
                    virtual_cost = log.virtual_cost
                    sales_cost = log.sale_cost
                    # if name:
                    # raise UserError(_("You must be enter start date less than end date(%s,%s,%s,%s) !")% (name,actual_cost,virtual_cost,sales_cost))
                    col = 0
                    row += 1
                    sequence_id += 1
                    excel_sheet.write(row, col, sequence_id, sequence_format)
                    col += 1
                    if date:
                        excel_sheet.write(row, col, date, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if name:
                        excel_sheet.write(row, col, name, format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if virtual_cost:
                        excel_sheet.write(row, col,virtual_cost , format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if actual_cost:
                        excel_sheet.write(row, col, actual_cost , format)
                    else:
                        excel_sheet.write(row, col, '', format)
                    col += 1
                    if sales_cost:
                        excel_sheet.write(row, col, sales_cost, format)





            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['costing.report.excel']
            res_id = wizardmodel.create({'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'costing.report.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


class costing_report_excel(models.TransientModel):
    _name = 'costing.report.excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
