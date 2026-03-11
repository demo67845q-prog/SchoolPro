import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolFeeReminderWizard(models.TransientModel):
    _name = 'school.fee.reminder.wizard'
    _description = 'Fee Reminder Wizard'

    class_id = fields.Many2one('school.class', string='Class')
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year')
    reminder_type = fields.Selection([
        ('all_pending', 'All Pending Invoices'),
        ('overdue', 'Overdue Only'),
        ('class', 'Specific Class'),
    ], string='Send Reminder To', default='all_pending', required=True)
    message = fields.Text(string='Custom Message',
                          default='Dear Parent, your child has pending school fees. Please pay at the earliest.')
    preview_count = fields.Integer(compute='_compute_preview', string='Students to Notify')

    @api.depends('reminder_type', 'class_id', 'academic_year_id')
    def _compute_preview(self):
        for rec in self:
            invoices = rec._get_invoices()
            rec.preview_count = len(invoices.mapped('student_id'))

    def _get_invoices(self):
        domain = [('state', 'in', ('pending', 'partial', 'overdue'))]
        if self.reminder_type == 'overdue':
            domain = [('state', '=', 'overdue')]
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        if self.academic_year_id:
            domain.append(('academic_year_id', '=', self.academic_year_id.id))
        return self.env['school.fee.invoice'].search(domain)

    def action_send_reminders(self):
        invoices = self._get_invoices()
        sent = 0
        for invoice in invoices:
            student = invoice.student_id
            # Create in-app notification
            self.env['school.notification'].create({
                'title': 'Fee Payment Reminder',
                'message': self.message or 'Please pay pending fees.',
                'notif_type': 'fee',
                'student_id': student.id,
                'recipient_type': 'parent',
            })
            # Send chatter message on invoice
            invoice.message_post(
                body=self.message,
                subject='Fee Payment Reminder',
            )
            sent += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminders Sent'),
                'message': _('{} reminders sent.').format(sent),
                'type': 'success',
            }
        }
