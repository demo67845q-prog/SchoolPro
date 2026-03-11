import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SchoolHostel(models.Model):
    _name = 'school.hostel'
    _description = 'Hostel'
    _order = 'name'

    name = fields.Char(string='Hostel Name', required=True)
    hostel_type = fields.Selection([
        ('boys', 'Boys'), ('girls', 'Girls'), ('mixed', 'Mixed'),
    ], string='Type', default='boys')
    warden_id = fields.Many2one('res.partner', string='Warden')
    warden_phone = fields.Char(string='Warden Phone')
    address = fields.Text(string='Address')
    total_rooms = fields.Integer(compute='_compute_room_stats', string='Total Rooms', store=True)
    occupied_rooms = fields.Integer(compute='_compute_room_stats', string='Occupied Rooms', store=True)
    room_ids = fields.One2many('school.hostel.room', 'hostel_id', string='Rooms')
    is_active = fields.Boolean(string='Active', default=True)
    monthly_fee = fields.Float(string='Monthly Fee')

    @api.depends('room_ids')
    def _compute_room_stats(self):
        for rec in self:
            rec.total_rooms = len(rec.room_ids)
            rec.occupied_rooms = len(rec.room_ids.filtered(lambda r: r.is_occupied))


class SchoolHostelRoom(models.Model):
    _name = 'school.hostel.room'
    _description = 'Hostel Room'
    _order = 'hostel_id, room_number'

    hostel_id = fields.Many2one('school.hostel', string='Hostel', ondelete='cascade', required=True)
    room_number = fields.Char(string='Room Number', required=True)
    room_type = fields.Selection([
        ('single', 'Single'), ('double', 'Double'),
        ('triple', 'Triple'), ('dormitory', 'Dormitory'),
    ], string='Room Type', default='double')
    capacity = fields.Integer(string='Capacity', default=2)
    floor = fields.Integer(string='Floor')
    is_occupied = fields.Boolean(compute='_compute_occupied', string='Occupied', store=True)
    allocation_ids = fields.One2many('school.hostel.allocation', 'room_id', string='Allocations')
    current_occupancy = fields.Integer(compute='_compute_occupied', string='Current Occupancy', store=True)
    monthly_fee = fields.Float(string='Room Fee')
    facilities = fields.Text(string='Facilities')

    @api.depends('allocation_ids', 'allocation_ids.state')
    def _compute_occupied(self):
        for rec in self:
            active_alloc = rec.allocation_ids.filtered(lambda a: a.state == 'active')
            rec.current_occupancy = len(active_alloc)
            rec.is_occupied = rec.current_occupancy >= rec.capacity


class SchoolHostelAllocation(models.Model):
    _name = 'school.hostel.allocation'
    _description = 'Hostel Allocation'
    _order = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', required=True, ondelete='cascade')
    hostel_id = fields.Many2one('school.hostel', string='Hostel', required=True)
    room_id = fields.Many2one('school.hostel.room', string='Room',
                              domain="[('hostel_id', '=', hostel_id)]", required=True)
    bed_number = fields.Char(string='Bed/Bunk Number')
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year')
    start_date = fields.Date(string='Check-in Date', default=fields.Date.today)
    end_date = fields.Date(string='Check-out Date')
    state = fields.Selection([
        ('active', 'Active'), ('vacated', 'Vacated'),
    ], string='Status', default='active')
    monthly_fee = fields.Float(related='room_id.monthly_fee', string='Monthly Fee', store=True)
    notes = fields.Text(string='Notes')

    @api.constrains('room_id', 'state')
    def _check_capacity(self):
        for rec in self:
            if rec.state == 'active':
                room = rec.room_id
                active_count = self.search_count([
                    ('room_id', '=', room.id),
                    ('state', '=', 'active'),
                    ('id', '!=', rec.id),
                ])
                if active_count >= room.capacity:
                    raise ValidationError(_(
                        'Room %s is at full capacity!'
                    ) % room.room_number)
