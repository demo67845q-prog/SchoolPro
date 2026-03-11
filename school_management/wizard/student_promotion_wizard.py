import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolStudentPromotionWizard(models.TransientModel):
    _name = 'school.student.promotion.wizard'
    _description = 'Student Promotion Wizard'

    academic_year_id = fields.Many2one('school.academic.year', string='New Academic Year', required=True)
    from_class_id = fields.Many2one('school.class', string='From Class', required=True)
    from_section_id = fields.Many2one('school.section', string='From Section',
                                     domain="[('class_id', '=', from_class_id)]")
    to_class_id = fields.Many2one('school.class', string='To Class', required=True)
    to_section_id = fields.Many2one('school.section', string='To Section',
                                   domain="[('class_id', '=', to_class_id)]")
    student_ids = fields.Many2many('school.student', string='Students',
                                  domain="[('class_id', '=', from_class_id), ('state', '=', 'active')]")
    promote_all = fields.Boolean(string='Promote All Students', default=True)

    @api.onchange('from_class_id', 'from_section_id', 'promote_all')
    def _onchange_class(self):
        if self.promote_all and self.from_class_id:
            domain = [('class_id', '=', self.from_class_id.id), ('state', '=', 'active')]
            if self.from_section_id:
                domain.append(('section_id', '=', self.from_section_id.id))
            self.student_ids = self.env['school.student'].search(domain)

    def action_promote(self):
        self.ensure_one()
        students = self.student_ids
        if not students:
            raise UserError(_('No students selected for promotion.'))

        promoted = 0
        for student in students:
            student.write({
                'academic_year_id': self.academic_year_id.id,
                'class_id': self.to_class_id.id,
                'section_id': self.to_section_id.id if self.to_section_id else False,
            })
            promoted += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Promotion Complete'),
                'message': _('{} students promoted to {}.').format(promoted, self.to_class_id.name),
                'type': 'success',
                'sticky': False,
            }
        }
