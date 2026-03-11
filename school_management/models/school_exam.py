import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SchoolExam(models.Model):
    _name = 'school.exam'
    _description = 'Examination'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(string='Exam Name', required=True, tracking=True)
    exam_type = fields.Selection([
        ('unit_test', 'Unit Test'),
        ('midterm', 'Midterm'),
        ('quarterly', 'Quarterly'),
        ('halfyearly', 'Half Yearly'),
        ('annual', 'Annual'),
        ('practical', 'Practical'),
    ], string='Exam Type', required=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('result_declared', 'Result Declared'),
    ], string='Status', default='draft', tracking=True)
    schedule_ids = fields.One2many('school.exam.schedule', 'exam_id', string='Schedule')
    result_ids = fields.One2many('school.exam.result', 'exam_id', string='Results')
    description = fields.Text(string='Instructions')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end < rec.date_start:
                raise ValidationError(_('End date must be after start date.'))

    def action_publish(self):
        self.write({'state': 'published'})

    def action_start(self):
        self.write({'state': 'ongoing'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_declare_result(self):
        """Calculate results and rankings."""
        for exam in self:
            results = self.env['school.exam.result'].search([('exam_id', '=', exam.id)])
            results._compute_grade()
            # Rank by total marks
            sorted_results = sorted(results, key=lambda r: r.total_marks, reverse=True)
            for rank, result in enumerate(sorted_results, 1):
                result.rank = rank
            exam.write({'state': 'result_declared'})


class SchoolExamSchedule(models.Model):
    _name = 'school.exam.schedule'
    _description = 'Exam Schedule'
    _order = 'exam_date, start_time'

    exam_id = fields.Many2one('school.exam', string='Exam', ondelete='cascade', required=True)
    subject_id = fields.Many2one('school.subject', string='Subject', required=True)
    exam_date = fields.Date(string='Exam Date', required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    max_marks = fields.Float(string='Max Marks', required=True, default=100)
    pass_marks = fields.Float(string='Pass Marks', required=True, default=35)
    room = fields.Char(string='Exam Hall/Room')
    invigilator_id = fields.Many2one('school.teacher', string='Invigilator')


class SchoolExamResult(models.Model):
    _name = 'school.exam.result'
    _description = 'Exam Result'
    _order = 'exam_id, student_id'

    exam_id = fields.Many2one('school.exam', string='Exam', ondelete='cascade', required=True)
    student_id = fields.Many2one('school.student', string='Student', required=True)
    class_id = fields.Many2one('school.class', string='Class',
                               related='student_id.class_id', store=True)
    section_id = fields.Many2one('school.section', string='Section',
                                 related='student_id.section_id', store=True)
    mark_ids = fields.One2many('school.exam.mark', 'result_id', string='Subject Marks')
    total_marks = fields.Float(compute='_compute_totals', string='Total Marks', store=True)
    max_marks = fields.Float(compute='_compute_totals', string='Max Marks', store=True)
    percentage = fields.Float(compute='_compute_totals', string='Percentage %', store=True)
    grade = fields.Char(string='Grade', readonly=True)
    rank = fields.Integer(string='Rank', readonly=True)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('absent', 'Absent'),
    ], string='Result', readonly=True)
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('result_unique', 'unique(exam_id, student_id)',
         'Result already exists for this student and exam!'),
    ]

    @api.depends('mark_ids.marks_obtained', 'mark_ids.max_marks')
    def _compute_totals(self):
        for rec in self:
            rec.total_marks = sum(rec.mark_ids.mapped('marks_obtained'))
            rec.max_marks = sum(rec.mark_ids.mapped('max_marks'))
            rec.percentage = (rec.total_marks / rec.max_marks * 100) if rec.max_marks else 0

    def _compute_grade(self):
        grade_map = [
            (90, 'A+'), (80, 'A'), (70, 'B+'), (60, 'B'),
            (50, 'C'), (40, 'D'), (0, 'F'),
        ]
        for rec in self:
            pct = rec.percentage
            grade = 'F'
            for threshold, g in grade_map:
                if pct >= threshold:
                    grade = g
                    break
            # Check if any subject failed
            failed_subjects = rec.mark_ids.filtered(
                lambda m: m.marks_obtained < m.pass_marks
            )
            rec.grade = grade
            rec.result = 'fail' if failed_subjects or pct < 33 else 'pass'


class SchoolExamMark(models.Model):
    _name = 'school.exam.mark'
    _description = 'Subject Marks'
    _order = 'result_id, subject_id'

    result_id = fields.Many2one('school.exam.result', string='Result',
                                ondelete='cascade', required=True)
    subject_id = fields.Many2one('school.subject', string='Subject', required=True)
    schedule_id = fields.Many2one('school.exam.schedule', string='Schedule')
    max_marks = fields.Float(string='Max Marks', default=100)
    pass_marks = fields.Float(string='Pass Marks', default=35)
    marks_obtained = fields.Float(string='Marks Obtained')
    is_absent = fields.Boolean(string='Absent')
    grade = fields.Char(compute='_compute_mark_grade', string='Grade', store=True)

    @api.depends('marks_obtained', 'max_marks')
    def _compute_mark_grade(self):
        grade_map = [(90, 'A+'), (80, 'A'), (70, 'B+'), (60, 'B'), (50, 'C'), (40, 'D'), (0, 'F')]
        for rec in self:
            if rec.is_absent:
                rec.grade = 'AB'
                continue
            pct = (rec.marks_obtained / rec.max_marks * 100) if rec.max_marks else 0
            rec.grade = next((g for t, g in grade_map if pct >= t), 'F')
