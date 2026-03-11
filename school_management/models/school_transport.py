import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SchoolTransportRoute(models.Model):
    _name = 'school.transport.route'
    _description = 'Bus Route'
    _order = 'name'

    name = fields.Char(string='Route Name', required=True)
    route_number = fields.Char(string='Route Number')
    description = fields.Text(string='Description')
    vehicle_id = fields.Many2one('school.transport.vehicle', string='Vehicle')
    driver_id = fields.Many2one('res.partner', string='Driver')
    driver_phone = fields.Char(string='Driver Phone')
    conductor_name = fields.Char(string='Conductor')
    stop_ids = fields.One2many('school.transport.stop', 'route_id', string='Stops')
    is_active = fields.Boolean(string='Active', default=True)
    morning_start_time = fields.Float(string='Morning Departure')
    afternoon_start_time = fields.Float(string='Afternoon Departure')


class SchoolTransportVehicle(models.Model):
    _name = 'school.transport.vehicle'
    _description = 'School Vehicle'
    _order = 'name'

    name = fields.Char(string='Vehicle Name', required=True)
    registration_no = fields.Char(string='Registration Number', required=True)
    vehicle_type = fields.Selection([
        ('bus', 'Bus'), ('van', 'Van'), ('auto', 'Auto'),
    ], string='Type', default='bus')
    capacity = fields.Integer(string='Seating Capacity')
    model = fields.Char(string='Vehicle Model')
    year = fields.Integer(string='Manufacturing Year')
    insurance_expiry = fields.Date(string='Insurance Expiry')
    fitness_expiry = fields.Date(string='Fitness Certificate Expiry')
    is_active = fields.Boolean(string='Active', default=True)


class SchoolTransportStop(models.Model):
    _name = 'school.transport.stop'
    _description = 'Bus Stop'
    _order = 'route_id, sequence'

    route_id = fields.Many2one('school.transport.route', string='Route',
                               ondelete='cascade', required=True)
    name = fields.Char(string='Stop Name', required=True)
    sequence = fields.Integer(string='Order', default=10)
    arrival_time = fields.Float(string='Arrival Time')
    landmark = fields.Char(string='Landmark')
    monthly_fee = fields.Float(string='Monthly Fee')


class SchoolTransportAssignment(models.Model):
    _name = 'school.transport.assignment'
    _description = 'Student Transport Assignment'
    _order = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    route_id = fields.Many2one('school.transport.route', string='Route', required=True)
    stop_id = fields.Many2one('school.transport.stop', string='Pickup/Drop Stop',
                              domain="[('route_id', '=', route_id)]")
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year')
    pickup_type = fields.Selection([
        ('both', 'Both Way'), ('morning', 'Morning Only'), ('evening', 'Evening Only'),
    ], string='Service', default='both')
    is_active = fields.Boolean(string='Active', default=True)
    monthly_fee = fields.Float(related='stop_id.monthly_fee', string='Monthly Fee', store=True)

    _sql_constraints = [
        ('assignment_unique', 'unique(student_id, academic_year_id)',
         'Student already has a transport assignment for this academic year!'),
    ]
