# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
# from odoo.exceptions import UserError
from odoo.exceptions import Warning as UserError

from dateutil import relativedelta
from io import BytesIO

class wizard_sale_report(models.Model):
    _name = 'wizard.sale.report'
    _description = 'Print Products and its sale order'

    start_date = fields.Datetime('Start Date', required=True)
    end_date = fields.Datetime('End Date', required=True)

    @api.multi
    def print_report(self):
        for report in self:
            # logo = report.env.user.company_id.company_header
            start_date = report.start_date
            end_date = report.end_date
            if report.start_date > report.end_date:
                raise UserError(_("You must be enter start date less than end date !"))
            # report_title = ' Activiteis From ' + from_date + ' to ' + to_date
            file_name = _('Sale Order.xlsx')
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            excel_sheet = workbook.add_worksheet('Sale Order')
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
            format_details.set_num_format('#,##0.00')
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
            excel_sheet.set_column(col, col, 25)
            excel_sheet.write(row, col, 'Product', header_format)
            col += 1
            excel_sheet.set_column(col, col, 10)
            excel_sheet.write(row, col, '# of Sales', header_format)
            col += 1
            excel_sheet.set_column(col, col, 20)
            excel_sheet.write(row, col, 'Total Amount', header_format)
            report_title = ' Sales From ' + start_date + ' to ' + end_date
            excel_sheet.merge_range(1, 1, 1, 4, report_title, title_format)

            self.env.cr.execute('''SELECT p.name,sum(line.product_uom_qty),sum(line.price_subtotal)  FROM sale_order AS s 
                                        INNER JOIN sale_order_line  AS line ON line.order_id = s.id
                                        INNER JOIN product_product AS p ON line.product_id = p.id WHERE s.confirmation_date >=%s AND s.confirmation_date <=%s AND s.state = 'sale' GROUP BY p.name ''',(start_date,end_date))
            for rec in self.env.cr.fetchall():
                name = rec[0]
                product_uom_qty = rec[1]
                price_subtotal = rec[2]


                col = 0
                row += 1
                sequence_id += 1
                excel_sheet.write(row, col, sequence_id, sequence_format)
                col += 1
                if name:
                    excel_sheet.write(row, col, name, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if product_uom_qty:
                    excel_sheet.write(row, col, product_uom_qty, format)
                else:
                    excel_sheet.write(row, col, '', format)
                col += 1
                if price_subtotal:
                    excel_sheet.write(row, col, price_subtotal, format)
                else:
                    excel_sheet.write(row, col, '', format)





            workbook.close()
            file_download = base64.b64encode(fp.getvalue())
            fp.close()
            wizardmodel = self.env['sales.report.excel']
            res_id = wizardmodel.create({'name': file_name, 'file_download': file_download})
            return {
                'name': 'Files to Download',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sales.report.excel',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': res_id.id,
            }


class sales_report_excel(models.TransientModel):
    _name = 'sales.report.excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('File to Download', readonly=True)
