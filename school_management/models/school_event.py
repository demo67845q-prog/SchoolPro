import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolEvent(models.Model):
    _name = 'school.event'
    _description = 'School Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc'

    name = fields.Char(string='Event Name', required=True, tracking=True)
    code = fields.Char(string='Event Code', readonly=True, copy=False,
                       default=lambda self: _('New'))
    date = fields.Date(string='Event Date', required=True, default=fields.Date.today)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year')
    class_ids = fields.Many2many('school.class', 'school_event_class_rel',
                                 'event_id', 'class_id', string='Participating Classes')
    event_type = fields.Selection([
        ('sports', 'Sports'),
        ('cultural', 'Cultural'),
        ('academic', 'Academic'),
        ('science', 'Science Fair'),
        ('art', 'Art & Craft'),
        ('debate', 'Debate / Quiz'),
        ('other', 'Other'),
    ], string='Event Type', default='other', required=True)
    venue = fields.Char(string='Venue')
    organizer_id = fields.Many2one('school.teacher', string='Organized By')
    description = fields.Html(string='Description')
    image_1 = fields.Binary(string='Photo 1', attachment=True)
    image_2 = fields.Binary(string='Photo 2', attachment=True)
    image_3 = fields.Binary(string='Photo 3', attachment=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    winner_ids = fields.One2many('school.event.winner', 'event_id', string='Winners')
    winner_count = fields.Integer(compute='_compute_winner_count', string='Winners')

    def _compute_winner_count(self):
        for rec in self:
            rec.winner_count = len(rec.winner_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('school.event') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'ongoing'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_winners(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Event Winners',
            'res_model': 'school.event.winner',
            'view_mode': 'list,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id},
        }


class SchoolEventWinner(models.Model):
    _name = 'school.event.winner'
    _description = 'Event Winner'
    _rec_name = 'student_id'
    _order = 'position'

    event_id = fields.Many2one('school.event', string='Event', required=True, ondelete='cascade')
    student_id = fields.Many2one('school.student', string='Student', required=True)
    class_id = fields.Many2one('school.class', string='Class', related='student_id.class_id', store=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year',
                                       related='event_id.academic_year_id', store=True)
    position = fields.Selection([
        ('1', '1st Place'),
        ('2', '2nd Place'),
        ('3', '3rd Place'),
    ], string='Position', required=True)
    category = fields.Char(string='Category / Sub-Event')
    remarks = fields.Text(string='Remarks')

    def action_print_certificate(self):
        return self.env.ref('school_management.action_report_event_certificate').report_action(self)
