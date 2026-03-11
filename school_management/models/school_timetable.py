import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SchoolPeriod(models.Model):
    _name = 'school.period'
    _description = 'School Period'
    _order = 'sequence'

    name = fields.Char(string='Period Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    is_break = fields.Boolean(string='Is Break/Lunch')

    def _format_time(self, value):
        hours = int(value)
        minutes = int((value - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.end_time <= rec.start_time:
                raise ValidationError(_('End time must be after start time.'))


class SchoolTimetable(models.Model):
    _name = 'school.timetable'
    _description = 'Class Timetable'
    _order = 'section_id, day_of_week, period_id'

    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    section_id = fields.Many2one('school.section', string='Section',
                                 domain="[('class_id', '=', class_id)]", required=True)
    day_of_week = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'),
    ], string='Day', required=True)
    period_id = fields.Many2one('school.period', string='Period', required=True)
    subject_id = fields.Many2one('school.subject', string='Subject')
    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    room = fields.Char(string='Room/Lab')

    _sql_constraints = [
        ('timetable_unique', 'unique(academic_year_id, section_id, day_of_week, period_id)',
         'A timetable entry already exists for this section, day, and period!'),
    ]

    @api.constrains('teacher_id', 'academic_year_id', 'day_of_week', 'period_id')
    def _check_teacher_conflict(self):
        for rec in self:
            if not rec.teacher_id:
                continue
            conflict = self.search([
                ('id', '!=', rec.id),
                ('academic_year_id', '=', rec.academic_year_id.id),
                ('day_of_week', '=', rec.day_of_week),
                ('period_id', '=', rec.period_id.id),
                ('teacher_id', '=', rec.teacher_id.id),
            ])
            if conflict:
                raise ValidationError(_(
                    'Teacher %s already has a class at this time!'
                ) % rec.teacher_id.name)
