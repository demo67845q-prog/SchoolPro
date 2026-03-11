import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolHomework(models.Model):
    _name = 'school.homework'
    _description = 'Homework Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, class_id'

    name = fields.Char(string='Title', required=True, tracking=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    section_id = fields.Many2one('school.section', string='Section',
                                 domain="[('class_id', '=', class_id)]")
    subject_id = fields.Many2one('school.subject', string='Subject', required=True)
    teacher_id = fields.Many2one('school.teacher', string='Assigned By', required=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year', required=True)
    assigned_date = fields.Date(string='Assigned Date', default=fields.Date.today)
    due_date = fields.Date(string='Due Date', required=True)
    description = fields.Html(string='Assignment Description')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    submission_ids = fields.One2many('school.homework.submission', 'homework_id', string='Submissions')
    submission_count = fields.Integer(compute='_compute_submission_count', string='Submissions')

    def _compute_submission_count(self):
        for rec in self:
            rec.submission_count = len(rec.submission_ids)

    def action_assign(self):
        self.write({'state': 'assigned'})

    def action_close(self):
        self.write({'state': 'closed'})


class SchoolHomeworkSubmission(models.Model):
    _name = 'school.homework.submission'
    _description = 'Homework Submission'
    _order = 'submitted_date desc'

    homework_id = fields.Many2one('school.homework', string='Homework',
                                  ondelete='cascade', required=True)
    student_id = fields.Many2one('school.student', string='Student', required=True)
    submitted_date = fields.Date(string='Submitted Date', default=fields.Date.today)
    attachment_ids = fields.Many2many('ir.attachment', string='Submitted Files')
    notes = fields.Text(string='Student Notes')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('late', 'Submitted Late'),
        ('not_submitted', 'Not Submitted'),
    ], string='Status', default='pending')
    grade = fields.Char(string='Grade')
    teacher_remarks = fields.Text(string='Teacher Remarks')

    _sql_constraints = [
        ('submission_unique', 'unique(homework_id, student_id)',
         'Submission already exists for this student!'),
    ]
