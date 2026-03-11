import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolAttendanceBulkWizard(models.TransientModel):
    _name = 'school.attendance.bulk.wizard'
    _description = 'Bulk Attendance Marking Wizard'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    section_id = fields.Many2one('school.section', string='Section',
                                 domain="[('class_id', '=', class_id)]", required=True)
    teacher_id = fields.Many2one('school.teacher', string='Marked By')
    line_ids = fields.One2many('school.attendance.bulk.line', 'wizard_id', string='Students')
    default_status = fields.Selection([
        ('present', 'Present'), ('absent', 'Absent'),
    ], string='Mark All As', default='present')

    @api.onchange('class_id', 'section_id', 'date')
    def _onchange_section(self):
        if self.section_id:
            students = self.env['school.student'].search([
                ('section_id', '=', self.section_id.id),
                ('state', '=', 'active'),
            ], order='roll_number, name')
            # Check for existing attendance
            existing = {
                a.student_id.id: a.status
                for a in self.env['school.attendance'].search([
                    ('date', '=', self.date),
                    ('section_id', '=', self.section_id.id),
                ])
            }
            lines = []
            for student in students:
                lines.append((0, 0, {
                    'student_id': student.id,
                    'roll_number': student.roll_number or '',
                    'status': existing.get(student.id, 'present'),
                }))
            self.line_ids = lines

    @api.onchange('default_status')
    def _onchange_default_status(self):
        for line in self.line_ids:
            line.status = self.default_status

    def action_save(self):
        self.ensure_one()
        Attendance = self.env['school.attendance']
        saved = 0
        for line in self.line_ids:
            existing = Attendance.search([
                ('student_id', '=', line.student_id.id),
                ('date', '=', self.date),
            ])
            vals = {
                'student_id': line.student_id.id,
                'date': self.date,
                'status': line.status,
                'reason': line.reason,
                'teacher_id': self.teacher_id.id if self.teacher_id else False,
                'marked_by': self.env.user.id,
            }
            if existing:
                existing.write(vals)
            else:
                Attendance.create(vals)
            saved += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attendance Saved'),
                'message': _('{} records saved for {}.').format(saved, self.date),
                'type': 'success',
            }
        }


class SchoolAttendanceBulkLine(models.TransientModel):
    _name = 'school.attendance.bulk.line'
    _description = 'Attendance Bulk Line'
    _order = 'roll_number, student_id'

    wizard_id = fields.Many2one('school.attendance.bulk.wizard', ondelete='cascade')
    student_id = fields.Many2one('school.student', string='Student', readonly=True)
    roll_number = fields.Char(string='Roll No', readonly=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
    ], string='Status', default='present', required=True)
    reason = fields.Char(string='Reason')
