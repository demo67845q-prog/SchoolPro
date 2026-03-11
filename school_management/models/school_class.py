import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SchoolSubject(models.Model):
    _name = 'school.subject'
    _description = 'School Subject'
    _order = 'name'

    name = fields.Char(string='Subject Name', required=True)
    code = fields.Char(string='Subject Code', required=True)
    description = fields.Text(string='Description')
    subject_type = fields.Selection([
        ('theory', 'Theory'),
        ('practical', 'Practical'),
        ('language', 'Language'),
        ('elective', 'Elective'),
    ], string='Type', default='theory')
    is_active = fields.Boolean(string='Active', default=True)
    max_marks = fields.Float(string='Maximum Marks', default=100)
    pass_marks = fields.Float(string='Pass Marks', default=35)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Subject code must be unique!'),
    ]


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _order = 'sequence, name'

    name = fields.Char(string='Class Name', required=True)
    code = fields.Char(string='Class Code')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)
    section_ids = fields.One2many('school.section', 'class_id', string='Sections')
    subject_ids = fields.Many2many('school.subject', 'school_class_subject_rel',
                                   'class_id', 'subject_id', string='Subjects')
    section_count = fields.Integer(compute='_compute_section_count', string='Sections')
    student_count = fields.Integer(compute='_compute_student_count', string='Students')

    @api.depends('section_ids')
    def _compute_section_count(self):
        for rec in self:
            rec.section_count = len(rec.section_ids)

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['school.student'].search_count([
                ('class_id', '=', rec.id), ('state', '=', 'active')
            ])


class SchoolSection(models.Model):
    _name = 'school.section'
    _description = 'Class Section'
    _order = 'class_id, name'

    name = fields.Char(string='Section Name', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True, ondelete='cascade')
    teacher_id = fields.Many2one('school.teacher', string='Class Teacher')
    capacity = fields.Integer(string='Capacity', default=40)
    room_number = fields.Char(string='Room Number')
    is_active = fields.Boolean(string='Active', default=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year')
    student_count = fields.Integer(compute='_compute_student_count', string='Students')
    display_name = fields.Char(compute='_compute_display', store=True)

    @api.depends('class_id', 'name')
    def _compute_display(self):
        for rec in self:
            rec.display_name = f"{rec.class_id.name} - {rec.name}" if rec.class_id else rec.name

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['school.student'].search_count([
                ('section_id', '=', rec.id), ('state', '=', 'active')
            ])

    @api.constrains('student_count', 'capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.student_count > rec.capacity:
                raise ValidationError(_(
                    'Section %s has exceeded its capacity of %d students.'
                ) % (rec.display_name, rec.capacity))
