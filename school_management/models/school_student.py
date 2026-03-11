import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'admission_no desc'

    # ── Identity ──────────────────────────────────────────────────────
    admission_no = fields.Char(string='Admission No', readonly=True, copy=False,
                               default=lambda self: _('New'))
    student_id = fields.Char(string='Student ID', readonly=True, copy=False)
    name = fields.Char(string='Full Name', required=True, tracking=True)
    photo = fields.Binary(string='Photo', attachment=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age')
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ], string='Gender', required=True)
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-'),
    ], string='Blood Group')
    nationality = fields.Many2one('res.country', string='Nationality')
    religion = fields.Char(string='Religion')
    mother_tongue = fields.Char(string='Mother Tongue')

    # ── Academic ─────────────────────────────────────────────────────
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year',
                                       required=True, tracking=True)
    class_id = fields.Many2one('school.class', string='Class', required=True, tracking=True)
    section_id = fields.Many2one('school.section', string='Section',
                                 domain="[('class_id', '=', class_id)]", tracking=True)
    roll_number = fields.Char(string='Roll Number')
    admission_date = fields.Date(string='Admission Date', default=fields.Date.today)

    # ── State ────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('transferred', 'Transferred'),
        ('suspended', 'Suspended'),
        ('alumni', 'Alumni'),
    ], string='Status', default='draft', tracking=True)

    # ── Contact ──────────────────────────────────────────────────────
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State/Province')
    country_id = fields.Many2one('res.country', string='Country')
    pincode = fields.Char(string='Pin Code')

    # ── Parents ──────────────────────────────────────────────────────
    father_name = fields.Char(string="Father's Name")
    father_occupation = fields.Char(string="Father's Occupation")
    father_phone = fields.Char(string="Father's Phone")
    father_email = fields.Char(string="Father's Email")
    mother_name = fields.Char(string="Mother's Name")
    mother_occupation = fields.Char(string="Mother's Occupation")
    mother_phone = fields.Char(string="Mother's Phone")
    guardian_name = fields.Char(string='Guardian Name')
    guardian_relation = fields.Char(string='Guardian Relation')
    guardian_phone = fields.Char(string='Guardian Phone')
    parent_user_id = fields.Many2one('res.users', string='Parent Portal User')

    # ── Medical ──────────────────────────────────────────────────────
    medical_conditions = fields.Text(string='Medical Conditions / Allergies')
    emergency_contact = fields.Char(string='Emergency Contact Name')
    emergency_phone = fields.Char(string='Emergency Phone')
    doctor_name = fields.Char(string="Doctor's Name")
    doctor_phone = fields.Char(string="Doctor's Phone")

    # ── Previous School ──────────────────────────────────────────────
    previous_school = fields.Char(string='Previous School')
    previous_class = fields.Char(string='Previous Class')
    transfer_certificate = fields.Char(string='TC Number')
    reason_for_leaving = fields.Text(string='Reason for Leaving')

    # ── Documents ────────────────────────────────────────────────────
    document_ids = fields.One2many('school.student.document', 'student_id', string='Documents')
    document_count = fields.Integer(compute='_compute_document_count', string='Documents')

    # ── Links ────────────────────────────────────────────────────────
    user_id = fields.Many2one('res.users', string='Portal User')
    fee_invoice_ids = fields.One2many('school.fee.invoice', 'student_id', string='Fee Invoices')
    attendance_ids = fields.One2many('school.attendance', 'student_id', string='Attendance')
    attendance_percent = fields.Float(compute='_compute_attendance_percent', string='Attendance %')
    fee_due = fields.Float(compute='_compute_fee_due', string='Fee Due')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_of_birth:
                delta = today - rec.date_of_birth
                rec.age = delta.days // 365
            else:
                rec.age = 0

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def _compute_attendance_percent(self):
        for rec in self:
            total = self.env['school.attendance'].search_count([('student_id', '=', rec.id)])
            present = self.env['school.attendance'].search_count([
                ('student_id', '=', rec.id), ('status', '=', 'present')
            ])
            rec.attendance_percent = (present / total * 100) if total else 0.0

    def _compute_fee_due(self):
        for rec in self:
            invoices = self.env['school.fee.invoice'].search([
                ('student_id', '=', rec.id), ('state', 'in', ('draft', 'pending'))
            ])
            rec.fee_due = sum(inv.amount_due for inv in invoices)

    @api.model_create_multi
    def create(self, vals_list):
        config = self.env['school.config'].get_school_config()
        prefix = config.admission_prefix or 'ADM'
        stu_prefix = config.student_id_prefix or 'STU'
        for vals in vals_list:
            if vals.get('admission_no', _('New')) == _('New'):
                vals['admission_no'] = self.env['ir.sequence'].next_by_code('school.student') or _('New')
            vals['student_id'] = f"{stu_prefix}/{vals['admission_no']}"
        return super().create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_transfer(self):
        self.write({'state': 'transferred'})

    def action_alumni(self):
        self.write({'state': 'alumni'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_promote(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.promotion.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_student_ids': self.ids},
        }


class SchoolStudentDocument(models.Model):
    _name = 'school.student.document'
    _description = 'Student Document'

    student_id = fields.Many2one('school.student', string='Student', ondelete='cascade', required=True)
    name = fields.Char(string='Document Name', required=True)
    doc_type = fields.Selection([
        ('birth_certificate', 'Birth Certificate'),
        ('transfer_certificate', 'Transfer Certificate'),
        ('marksheet', 'Previous Mark Sheet'),
        ('id_proof', 'ID Proof'),
        ('address_proof', 'Address Proof'),
        ('photo', 'Photograph'),
        ('medical', 'Medical Certificate'),
        ('other', 'Other'),
    ], string='Document Type', default='other')
    file = fields.Binary(string='File', attachment=True, required=True)
    file_name = fields.Char(string='File Name')
    date_uploaded = fields.Date(string='Upload Date', default=fields.Date.today)
    notes = fields.Text(string='Notes')
