# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, Warning
from dateutil.relativedelta import relativedelta


class delay_loan(models.TransientModel):
    _name = 'delay.loan'
    _description = 'Delay loan  for all selected employees'

    date_from = fields.Date('Date From',default=fields.Date.today(), required=True)
    date_to = fields.Date('Date To', required=True)
    loan_id = fields.Many2one('hr.loan', string='Loan')

    @api.one
    def compute_delay_loan(self):
        for rec in self:
            loan_line = rec.env['hr.loan.line']
            loan_id = rec.loan_id
            paid_amount = 0
            if loan_id:
                loan_line_rec = loan_id.loan_line_ids.search([('paid_date','>=',rec.date_from),('paid_date','<=',rec.date_to)
                ,('employee_id', '=', loan_id.employee_id.id), ('loan_id.state', '=', 'account_confirm')])
                if not loan_line_rec:
                    raise UserError(_('Date You have entered doesnt exist in Loan before'))
                else:
                    employee_id = loan_id.employee_id
                    loan_line_ids = loan_line.search([('employee_id', '=', employee_id.id), ('paid_date', '<=', rec.date_to)
                    ,('paid_date', '>=', rec.date_from), ('stopped', '=', False), ('paid', '=', False), ('loan_id.state', '=', 'account_confirm')])
                    if loan_line_ids:
                        for loan_line_id in loan_line_ids:
                            paid_amount += loan_line_id.paid_amount
                            paid_date = loan_line_id.paid_date
                            loan_update_id = loan_line_id.id
                            self._cr.execute(
                                "update hr_loan_line set stopped=%s where loan_id=%s and paid_date =%s and id = %s",
                                (True, loan_id.id, paid_date, loan_update_id))
                        per_loan = loan_line.search([('employee_id', '=',employee_id.id), ('loan_id.state', '=', 'account_confirm')
                                                     ],order="paid_date asc")
                        for per in per_loan[-1]:
                            date_pay = per.paid_date
                            date_pay = datetime.strptime(str(date_pay), '%Y-%m-%d') + relativedelta(months=1)
                            loan_id = per.loan_id
                            installment = per.loan_id.loan_amount / per.loan_id.no_month
                            new_month = paid_amount / installment
                            counter = 0
                            loan_diff = paid_amount - installment * int(new_month)
                            if loan_diff > installment:
                                new_month += 1
                                x = loan_diff - installment
                            else:
                                x = loan_diff

                            for i in range(1, int(new_month + 1)):
                                if i != new_month + 1:
                                    loan_line.create({
                                        'paid_date': date_pay,
                                        'paid_amount': round(installment, 2),
                                        'employee_id': per.employee_id.id,
                                        'loan_id': loan_id.id})
                                    date_pay = date_pay + relativedelta(months=1)
                            if loan_diff > 0:
                                loan_line.create({
                                    'paid_date': date_pay,
                                    'paid_amount': x,
                                    'employee_id': per.employee_id.id,
                                    'loan_id': loan_id.id})
                                counter += 1

    @api.one
    def cancel_delay_loan(self):
        for rec in self:
            loan_line = rec.env['hr.loan.line']
            loan_id = rec.loan_id
            installment = rec.loan_id.loan_amount / rec.loan_id.no_month
            total_delay_amount = 0
            total_amount = 0
            if loan_id:
                loan_line_rec = loan_id.loan_line_ids.search(
                    [('paid_date', '>=', rec.date_from), ('paid_date', '<=', rec.date_to)
                        , ('loan_id.state', '=', 'account_confirm'), ('employee_id', '=', loan_id.employee_id.id)])
                if not loan_line_rec:
                    raise UserError(_('Date You have entered doesnt exist in Loan'))
                else:
                    payslip_line = rec.env['hr.payslip'].search([('employee_id','=',loan_id.employee_id.id)
                    ,('date_from','>=',rec.date_from),('date_to','<=',rec.date_to),('state','=','done')])
                    if payslip_line:
                        raise UserError(_('You cant cancel the delay'))
                    else:
                        delay_loan_line = loan_line.search(
                            [('employee_id', '=', loan_id.employee_id.id), ('stopped', '=', True),
                             ('loan_id', '=', loan_id.id)
                                , ('paid_date', '>=', rec.date_from), ('paid_date', '<=', rec.date_to)])
                        for x in delay_loan_line:
                            installment = x.loan_id.loan_amount / x.loan_id.no_month
                            total_delay_amount += x.paid_amount

                        loan_line_ids = loan_line.search(
                            [('employee_id', '=', loan_id.employee_id.id), ('loan_id', '=', loan_id.id),
                             ('paid', '=', False),  ('loan_id.state', '=', 'account_confirm')])
                        frist_id = loan_line_ids and min(loan_line_ids)
                        paid_date = frist_id.paid_date
                        for y in loan_line_ids:
                            line_id = y.id
                            total_amount += y.paid_amount
                            self._cr.execute("delete from  hr_loan_line  where id=%s", (line_id,))
                        for x in delay_loan_line:
                            line_id = x.id
                            self._cr.execute("delete from  hr_loan_line  where id=%s", (line_id,))
                        loan_amount = total_amount - total_delay_amount
                        if loan_amount ==0:
                            loan_amount = total_delay_amount
                        new_month = loan_amount / installment
                        counter = 0
                        loan_diff = loan_amount - installment * int(new_month)
                        paid_date = datetime.strptime(str(paid_date), '%Y-%m-%d')
                        if loan_diff > installment:
                            new_month += 1
                            loan_diff = loan_diff - installment
                        else:
                            loan_diff = loan_diff
                        for i in range(0, int(new_month)):
                            if i != new_month:
                                loan_line.create({
                                    'paid_date': paid_date,
                                    'paid_amount': round(installment, 2),
                                    'employee_id': loan_id.employee_id.id,
                                    'loan_id': loan_id.id})
                                paid_date = paid_date + relativedelta(months=1)
                        if loan_diff > 0:
                            loan_line.create({
                                'paid_date': paid_date,
                                'paid_amount': loan_diff,
                                'employee_id': loan_id.employee_id.id,
                                'loan_id': loan_id.id})
                            counter += 1

