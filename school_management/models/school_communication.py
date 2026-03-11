import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolAnnouncement(models.Model):
    _name = 'school.announcement'
    _description = 'School Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    title = fields.Char(string='Title', required=True, tracking=True)
    content = fields.Html(string='Content', required=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    expiry_date = fields.Date(string='Expiry Date')
    audience = fields.Selection([
        ('all', 'All'),
        ('students', 'Students Only'),
        ('teachers', 'Teachers Only'),
        ('parents', 'Parents Only'),
        ('class', 'Specific Class'),
    ], string='Audience', default='all', required=True)
    class_id = fields.Many2one('school.class', string='Class',
                               invisible="audience != 'class'")
    priority = fields.Selection([
        ('normal', 'Normal'),
        ('important', 'Important'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    author_id = fields.Many2one('res.users', string='Author', default=lambda self: self.env.user)
    views_count = fields.Integer(string='Views', default=0)
    is_active = fields.Boolean(compute='_compute_is_active', string='Active')

    @api.depends('state', 'expiry_date')
    def _compute_is_active(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_active = (
                rec.state == 'published'
                and (not rec.expiry_date or rec.expiry_date >= today)
            )

    def action_publish(self):
        self.write({'state': 'published'})

    def action_archive_ann(self):
        self.write({'state': 'archived'})


class SchoolNotification(models.Model):
    _name = 'school.notification'
    _description = 'School Notification'
    _order = 'date desc'

    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    notif_type = fields.Selection([
        ('attendance', 'Attendance Alert'),
        ('fee', 'Fee Reminder'),
        ('exam', 'Exam Notice'),
        ('homework', 'Homework'),
        ('general', 'General'),
        ('result', 'Result'),
    ], string='Type', default='general')
    recipient_type = fields.Selection([
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
    ], string='Recipient Type')
    student_id = fields.Many2one('school.student', string='Student')
    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    user_id = fields.Many2one('res.users', string='User')
    is_read = fields.Boolean(string='Read', default=False)
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'),
    ], string='Priority', default='normal')
