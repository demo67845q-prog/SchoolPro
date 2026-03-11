import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolAcademicYear(models.Model):
    _name = 'school.academic.year'
    _description = 'Academic Year'
    _order = 'date_start desc'

    name = fields.Char(string='Academic Year', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    is_active = fields.Boolean(string='Current Year', default=False)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Academic year name must be unique!'),
    ]

    def action_set_active(self):
        self.search([('is_active', '=', True)]).write({'is_active': False})
        self.write({'is_active': True})


class SchoolConfig(models.Model):
    _name = 'school.config'
    _description = 'School Configuration'

    name = fields.Char(string='School Name', required=True)
    code = fields.Char(string='School Code')
    logo = fields.Binary(string='School Logo', attachment=True)
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    principal_id = fields.Many2one('res.users', string='Principal')
    academic_year_id = fields.Many2one('school.academic.year', string='Current Academic Year')
    admission_prefix = fields.Char(string='Admission No Prefix', default='ADM')
    student_id_prefix = fields.Char(string='Student ID Prefix', default='STU')
    about = fields.Html(string='About School')

    @api.model
    def get_school_config(self):
        config = self.search([], limit=1)
        return config or self.create({'name': 'My School'})
