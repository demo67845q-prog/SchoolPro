import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolAttendance(models.Model):
    _name = 'school.attendance'
    _description = 'Student Attendance'
    _order = 'date desc, student_id'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    class_id = fields.Many2one('school.class', string='Class', related='student_id.class_id', store=True)
    section_id = fields.Many2one('school.section', string='Section', related='student_id.section_id', store=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year',
                                       related='student_id.academic_year_id', store=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
    ], string='Status', required=True, default='present')
    time_in = fields.Float(string='Time In')
    time_out = fields.Float(string='Time Out')
    reason = fields.Text(string='Reason (if absent)')
    marked_by = fields.Many2one('res.users', string='Marked By', default=lambda self: self.env.user)
    teacher_id = fields.Many2one('school.teacher', string='Teacher')

    _sql_constraints = [
        ('attendance_unique', 'unique(student_id, date)',
         'Attendance already recorded for this student on this date!'),
    ]


class SchoolTeacherAttendance(models.Model):
    _name = 'school.teacher.attendance'
    _description = 'Teacher Attendance'
    _order = 'date desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', required=True, ondelete='cascade')
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
    ], string='Status', required=True, default='present')
    time_in = fields.Float(string='Time In')
    time_out = fields.Float(string='Time Out')
    reason = fields.Text(string='Reason')
    marked_by = fields.Many2one('res.users', string='Marked By', default=lambda self: self.env.user)

    _sql_constraints = [
        ('teacher_attendance_unique', 'unique(teacher_id, date)',
         'Attendance already recorded for this teacher on this date!'),
    ]
