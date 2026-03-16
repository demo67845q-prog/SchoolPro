from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date

MONTH_SELECTION = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'),
    ('4', 'April'), ('5', 'May'), ('6', 'June'),
    ('7', 'July'), ('8', 'August'), ('9', 'September'),
    ('10', 'October'), ('11', 'November'), ('12', 'December'),
]


class SchoolFeeGenerateWizard(models.TransientModel):
    _name = 'school.fee.generate.wizard'
    _description = 'Generate Monthly Fee Invoices'

    schedule_id = fields.Many2one('school.fee.schedule', string='Fee Schedule', required=True,
                                   domain=[('is_active', '=', True)])
    month = fields.Selection(MONTH_SELECTION, string='Month', required=True)
    class_ids = fields.Many2many('school.class', string='Classes',
                                  help='Leave empty to generate for all classes')
    preview_count = fields.Integer(string='Students', compute='_compute_preview_count')

    @api.depends('schedule_id', 'month', 'class_ids')
    def _compute_preview_count(self):
        for wiz in self:
            if not wiz.schedule_id or not wiz.month:
                wiz.preview_count = 0
                continue
            students = wiz._get_eligible_students()
            wiz.preview_count = len(students)

    def _get_eligible_students(self):
        """Return students eligible for invoice generation."""
        domain = [('state', 'in', ('active', 'draft'))]
        if self.class_ids:
            domain.append(('class_id', 'in', self.class_ids.ids))
        return self.env['school.student'].search(domain)

    def _get_invoice_year(self, month_int):
        """Determine the calendar year for the given month based on academic year dates."""
        ay = self.schedule_id.academic_year_id
        ay_start = ay.date_start
        ay_end = ay.date_end
        # If month falls on or after the start month, use start year; else use end year
        if month_int >= ay_start.month:
            return ay_start.year
        return ay_end.year

    def action_generate_invoices(self):
        self.ensure_one()
        if not self.schedule_id or not self.month:
            raise UserError(_('Please select a fee schedule and month.'))

        month_int = int(self.month)
        schedule = self.schedule_id
        academic_year = schedule.academic_year_id

        # Get schedule lines for selected month
        schedule_lines = self.env['school.fee.schedule.line'].search([
            ('schedule_id', '=', schedule.id),
            ('month', '=', self.month),
        ])
        if not schedule_lines:
            raise UserError(_('No fee rules defined for %s in this schedule.') %
                            dict(MONTH_SELECTION).get(self.month))

        students = self._get_eligible_students()
        if not students:
            raise UserError(_('No eligible students found.'))

        inv_year = self._get_invoice_year(month_int)
        due_day = min(schedule.due_day, 28)  # safety for short months
        due_date = date(inv_year, month_int, due_day)
        invoice_date = date(inv_year, month_int, 1)

        created_count = 0
        FeeInvoice = self.env['school.fee.invoice']
        FeeInvoiceLine = self.env['school.fee.invoice.line']

        for student in students:
            # Skip if invoice already exists for same student + month + academic year
            existing = FeeInvoice.search([
                ('student_id', '=', student.id),
                ('month', '=', self.month),
                ('academic_year_id', '=', academic_year.id),
            ], limit=1)
            if existing:
                continue

            # Build invoice lines from schedule lines + fee structure
            inv_lines = []
            for sline in schedule_lines:
                # Skip new-student-only fees for active students
                if sline.only_new_students and student.state != 'draft':
                    continue

                # Find amount from fee structure
                struct_line = self.env['school.fee.structure.line'].search([
                    ('structure_id.academic_year_id', '=', academic_year.id),
                    ('structure_id.class_id', '=', student.class_id.id),
                    ('category_id', '=', sline.category_id.id),
                ], limit=1)
                if not struct_line:
                    continue

                inv_lines.append((0, 0, {
                    'category_id': sline.category_id.id,
                    'name': sline.category_id.name,
                    'amount': struct_line.amount,
                }))

            if not inv_lines:
                continue

            invoice = FeeInvoice.create({
                'student_id': student.id,
                'academic_year_id': academic_year.id,
                'date': invoice_date,
                'due_date': due_date,
                'month': self.month,
                'schedule_id': schedule.id,
                'line_ids': inv_lines,
            })
            invoice.action_confirm()
            created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fee Generation Complete'),
                'message': _('%d invoices created for %s.') % (
                    created_count, dict(MONTH_SELECTION).get(self.month)),
                'sticky': False,
                'type': 'success',
            },
        }
