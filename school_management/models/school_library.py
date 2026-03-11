import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolLibraryBook(models.Model):
    _name = 'school.library.book'
    _description = 'Library Book'
    _rec_name = 'title'
    _order = 'title'

    title = fields.Char(string='Book Title', required=True)
    isbn = fields.Char(string='ISBN')
    author = fields.Char(string='Author', required=True)
    publisher = fields.Char(string='Publisher')
    category = fields.Char(string='Category/Genre')
    language = fields.Char(string='Language', default='English')
    edition = fields.Char(string='Edition')
    publication_year = fields.Integer(string='Year')
    total_copies = fields.Integer(string='Total Copies', default=1)
    available_copies = fields.Integer(compute='_compute_available', string='Available', store=True)
    issued_copies = fields.Integer(compute='_compute_available', string='Issued', store=True)
    location = fields.Char(string='Shelf/Location')
    cover_image = fields.Binary(string='Cover', attachment=True)
    description = fields.Text(string='Description')
    issue_ids = fields.One2many('school.library.issue', 'book_id', string='Issue Records')
    is_active = fields.Boolean(string='Active', default=True)

    @api.depends('issue_ids', 'issue_ids.state', 'total_copies')
    def _compute_available(self):
        for rec in self:
            issued = len(rec.issue_ids.filtered(lambda i: i.state == 'issued'))
            rec.issued_copies = issued
            rec.available_copies = rec.total_copies - issued


class SchoolLibraryIssue(models.Model):
    _name = 'school.library.issue'
    _description = 'Book Issue Record'
    _order = 'issue_date desc'

    book_id = fields.Many2one('school.library.book', string='Book', required=True, ondelete='restrict')
    student_id = fields.Many2one('school.student', string='Student')
    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    member_name = fields.Char(string='Member', compute='_compute_member', store=True)
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today, required=True)
    due_date = fields.Date(string='Due Date', required=True)
    return_date = fields.Date(string='Return Date')
    fine_amount = fields.Float(string='Fine Amount', default=0.0)
    fine_paid = fields.Boolean(string='Fine Paid')
    state = fields.Selection([
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    ], string='Status', default='issued')
    notes = fields.Text(string='Notes')
    issued_by = fields.Many2one('res.users', string='Issued By', default=lambda self: self.env.user)

    @api.depends('student_id', 'teacher_id')
    def _compute_member(self):
        for rec in self:
            rec.member_name = (rec.student_id.name if rec.student_id
                               else rec.teacher_id.name if rec.teacher_id else '')

    def action_return(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state != 'issued':
                raise UserError(_('Book is not in issued state.'))
            fine = 0.0
            if today > rec.due_date:
                days_overdue = (today - rec.due_date).days
                fine = days_overdue * 2.0  # ₹2 per day fine
            rec.write({
                'state': 'returned',
                'return_date': today,
                'fine_amount': fine,
            })

    @api.model
    def _cron_mark_overdue(self):
        today = fields.Date.today()
        overdue = self.search([('state', '=', 'issued'), ('due_date', '<', today)])
        overdue.write({'state': 'overdue'})
