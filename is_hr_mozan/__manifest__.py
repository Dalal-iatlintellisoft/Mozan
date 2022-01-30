{
    'name': 'Hr Mozan ',
    'version': '1.1',
    'author': 'Intellisoft',
    'sequence': 4,
    'category': 'Human Resources',
    'description': """
Mozan hr custminzation loan , attrndance ,overtime,leaves

	""",

    'depends': ['hr', 'hr_holidays', 'hr_payroll', 'hr_payroll_account', 'hr_attendance', 'account'],
    'data': [
        'security/hr_french_security.xml',

        'wizard/holiday_batch_view.xml',
        'data/payroll_rule_data.xml',
        'views/is_hr_mozan_view.xml',
        'views/delay_loan_view.xml',
        # 'views/is_hr_mozan_loan_view.xml',
        'views/is_hr_mozan_loan_view1.xml',
        'views/is_hr_overtime_view.xml',
        'views/is_warnings_view.xml',
        'views/is_hr_payslip_view.xml',
        'views/is_hr_leaves.xml',

        # 'views/is_hr_mozan_trip.xml',
        'views/is_health_insurance_view.xml',
        'views/mozan_custody_view.xml',
        'views/end_srevices_view.xml',
        'views/hr_incentive_view.xml',
        'wizard/pay_sheet_view.xml',
        'wizard/wizard_overtime_view.xml',
        'report/hr_report.xml',
        'report/leave_request.xml',
        # 'report/external_layout.xml',
        'report/custody_request_report.xml',
        'report/custody_return_report.xml',
        'report/custody_receiving_report.xml',
        'report/end_duty.xml',
        'data/hr_contract_sequence.xml',
        'data/hr_employee_sequence.xml',



        # 'report/form_emp_explanation_2.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
