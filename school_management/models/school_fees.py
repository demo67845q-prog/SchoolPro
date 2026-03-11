import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolFeeCategory(models.Model):
    _name = 'school.fee.category'
    _description = 'Fee Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)


class SchoolFeeStructure(models.Model):
    _name = 'school.fee.structure'
    _description = 'Fee Structure'
    _order = 'academic_year_id, class_id'

    name = fields.Char(string='Name', required=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    line_ids = fields.One2many('school.fee.structure.line', 'structure_id', string='Fee Lines')
    total_amount = fields.Float(compute='_compute_total', string='Total Amount', store=True)
    description = fields.Text(string='Notes')

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))


class SchoolFeeStructureLine(models.Model):
    _name = 'school.fee.structure.line'
    _description = 'Fee Structure Line'
    _order = 'sequence'

    structure_id = fields.Many2one('school.fee.structure', string='Fee Structure',
                                   ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    category_id = fields.Many2one('school.fee.category', string='Fee Category', required=True)
    name = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount', required=True)
    is_optional = fields.Boolean(string='Optional')
    due_date = fields.Date(string='Due Date')


class SchoolFeeInvoice(models.Model):
    _name = 'school.fee.invoice'
    _description = 'Student Fee Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'reference'

    reference = fields.Char(string='Invoice Ref', readonly=True, copy=False,
                            default=lambda self: _('New'))
    student_id = fields.Many2one('school.student', string='Student', required=True, tracking=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year', required=True)
    class_id = fields.Many2one('school.class', string='Class', related='student_id.class_id', store=True)
    date = fields.Date(string='Invoice Date', default=fields.Date.today, required=True)
    due_date = fields.Date(string='Due Date', required=True)
    fee_structure_id = fields.Many2one('school.fee.structure', string='Fee Structure')
    line_ids = fields.One2many('school.fee.invoice.line', 'invoice_id', string='Fee Lines')
    payment_ids = fields.One2many('school.fee.payment', 'invoice_id', string='Payments')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    total_amount = fields.Float(compute='_compute_amounts', string='Total Amount', store=True)
    amount_paid = fields.Float(compute='_compute_amounts', string='Amount Paid', store=True)
    amount_due = fields.Float(compute='_compute_amounts', string='Amount Due', store=True)
    late_fee = fields.Float(string='Late Fee', default=0.0)

    @api.depends('line_ids.amount', 'payment_ids.amount', 'late_fee')
    def _compute_amounts(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount')) + rec.late_fee
            rec.amount_paid = sum(p.amount for p in rec.payment_ids if p.state == 'confirmed')
            rec.amount_due = rec.total_amount - rec.amount_paid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('school.fee.invoice') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'pending'})

    def action_cancel(self):
        if any(inv.state == 'paid' for inv in self):
            raise UserError(_('Cannot cancel a fully paid invoice.'))
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_register_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'school.fee.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_student_id': self.student_id.id,
                'default_amount': self.amount_due,
            },
        }

    def _apply_late_fee(self, penalty_amount):
        """Called by cron to apply late fee penalty."""
        today = fields.Date.today()
        overdue = self.search([
            ('state', 'in', ('pending', 'partial')),
            ('due_date', '<', today),
        ])
        for inv in overdue:
            inv.write({'late_fee': inv.late_fee + penalty_amount, 'state': 'overdue'})


class SchoolFeeInvoiceLine(models.Model):
    _name = 'school.fee.invoice.line'
    _description = 'Fee Invoice Line'
    _order = 'sequence'

    invoice_id = fields.Many2one('school.fee.invoice', string='Invoice',
                                 ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one('school.fee.category', string='Category')
    name = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount', required=True)


class SchoolFeePayment(models.Model):
    _name = 'school.fee.payment'
    _description = 'Fee Payment'
    _inherit = ['mail.thread']
    _order = 'date desc'

    receipt_no = fields.Char(string='Receipt No', readonly=True, copy=False,
                             default=lambda self: _('New'))
    invoice_id = fields.Many2one('school.fee.invoice', string='Invoice', required=True)
    student_id = fields.Many2one('school.student', string='Student',
                                 related='invoice_id.student_id', store=True)
    date = fields.Date(string='Payment Date', default=fields.Date.today, required=True)
    amount = fields.Float(string='Amount', required=True)
    payment_mode = fields.Selection([
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('dd', 'Demand Draft'),
    ], string='Payment Mode', default='cash', required=True)
    transaction_ref = fields.Char(string='Transaction Reference')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    collected_by = fields.Many2one('res.users', string='Collected By', default=lambda self: self.env.user)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('receipt_no', _('New')) == _('New'):
                vals['receipt_no'] = self.env['ir.sequence'].next_by_code('school.fee.payment') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.write({'state': 'confirmed'})
            invoice = rec.invoice_id
            if invoice.amount_due <= 0:
                invoice.write({'state': 'paid'})
            elif invoice.amount_paid > 0:
                invoice.write({'state': 'partial'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
