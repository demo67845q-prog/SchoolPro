import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolTeacher(models.Model):
    _name = 'school.teacher'
    _description = 'Teacher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # ── Identity ──────────────────────────────────────────────────────
    employee_id = fields.Char(string='Employee ID', readonly=True, copy=False,
                              default=lambda self: _('New'))
    name = fields.Char(string='Full Name', required=True, tracking=True)
    photo = fields.Binary(string='Photo', attachment=True)
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ], string='Gender')
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-'),
    ], string='Blood Group')
    nationality = fields.Many2one('res.country', string='Nationality')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')

    # ── Contact ──────────────────────────────────────────────────────
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email', required=True)
    address = fields.Text(string='Address')

    # ── Professional ─────────────────────────────────────────────────
    designation = fields.Char(string='Designation')
    qualification = fields.Char(string='Highest Qualification')
    specialization = fields.Char(string='Specialization')
    experience_years = fields.Integer(string='Experience (Years)')
    joining_date = fields.Date(string='Joining Date', default=fields.Date.today)
    state = fields.Selection([
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('resigned', 'Resigned'),
        ('terminated', 'Terminated'),
    ], string='Status', default='active', tracking=True)

    # ── Allocation ───────────────────────────────────────────────────
    subject_ids = fields.Many2many('school.subject', 'school_teacher_subject_rel',
                                   'teacher_id', 'subject_id', string='Subjects')
    section_ids = fields.One2many('school.section', 'teacher_id', string='Class Teacher Of')
    user_id = fields.Many2one('res.users', string='Portal User')

    # ── Stats ────────────────────────────────────────────────────────
    class_count = fields.Integer(compute='_compute_class_count', string='Classes')
    attendance_percent = fields.Float(compute='_compute_attendance_percent', string='Attendance %')

    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.section_ids)

    def _compute_attendance_percent(self):
        for rec in self:
            total = self.env['school.teacher.attendance'].search_count([('teacher_id', '=', rec.id)])
            present = self.env['school.teacher.attendance'].search_count([
                ('teacher_id', '=', rec.id), ('status', '=', 'present')
            ])
            rec.attendance_percent = (present / total * 100) if total else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id', _('New')) == _('New'):
                vals['employee_id'] = self.env['ir.sequence'].next_by_code('school.teacher') or _('New')
        return super().create(vals_list)
