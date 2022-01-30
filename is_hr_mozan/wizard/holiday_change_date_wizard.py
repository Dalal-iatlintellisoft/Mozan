# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, Warning
import babel
import time

from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class holiday_change_date(models.TransientModel):
    _name = 'holiday.change.date'

    date = fields.Datetime('Back Date', required=True)

    @api.multi
    def compute_grant_sheet(self):
        for report in self:
            date = report.date
            active_id = report.env.context.get('active_id')
            if active_id:
                for hol in self.env['hr.holidays'].search([('id', '=', active_id)]):
                    hol.date_to = date
                    hol.number_of_days_temp = hol._get_number_of_days(hol.date_from, hol.date_to, hol.employee_id.id)
