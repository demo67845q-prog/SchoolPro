import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SchoolDashboard(models.AbstractModel):
    _name = 'school.dashboard'
    _description = 'School Dashboard Data Provider'

    @api.model
    def get_admin_kpis(self):
        """KPIs for admin/principal dashboard."""
        Student = self.env['school.student']
        Teacher = self.env['school.teacher']
        today = fields.Date.today()

        total_students = Student.search_count([('state', '=', 'active')])
        total_teachers = Teacher.search_count([('state', '=', 'active')])

        # Attendance today
        total_att = self.env['school.attendance'].search_count([('date', '=', today)])
        present = self.env['school.attendance'].search_count([
            ('date', '=', today), ('status', '=', 'present')
        ])
        attendance_pct = (present / total_att * 100) if total_att else 0

        # Fee collection this month
        import datetime
        month_start = today.replace(day=1)
        fee_collected = sum(
            self.env['school.fee.payment'].search([
                ('state', '=', 'confirmed'),
                ('date', '>=', month_start),
            ]).mapped('amount')
        )
        fee_due = sum(
            self.env['school.fee.invoice'].search([
                ('state', 'in', ('pending', 'partial', 'overdue'))
            ]).mapped('amount_due')
        )

        # Exams this month
        upcoming_exams = self.env['school.exam'].search_count([
            ('state', 'in', ('published', 'ongoing')),
            ('date_start', '>=', today),
        ])

        # Announcements
        announcements = self.env['school.announcement'].search([
            ('state', '=', 'published'),
        ], limit=5, order='date desc')

        # Attendance trend (last 7 days)
        attendance_trend = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            tot = self.env['school.attendance'].search_count([('date', '=', day)])
            prs = self.env['school.attendance'].search_count([
                ('date', '=', day), ('status', '=', 'present')
            ])
            attendance_trend.append({
                'date': day.strftime('%a'),
                'total': tot,
                'present': prs,
                'pct': round((prs / tot * 100) if tot else 0, 1),
            })

        # Class-wise student count
        classes = self.env['school.class'].search([])
        class_stats = [
            {'name': c.name, 'count': c.student_count}
            for c in classes if c.student_count
        ]

        return {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'attendance_today': round(attendance_pct, 1),
            'fee_collected_month': fee_collected,
            'fee_due_total': fee_due,
            'upcoming_exams': upcoming_exams,
            'announcements': [
                {'title': a.title, 'priority': a.priority, 'date': str(a.date)}
                for a in announcements
            ],
            'attendance_trend': attendance_trend,
            'class_stats': class_stats,
        }

    @api.model
    def get_teacher_kpis(self):
        """KPIs for teacher dashboard."""
        user = self.env.user
        teacher = self.env['school.teacher'].search([('user_id', '=', user.id)], limit=1)
        if not teacher:
            return {}

        today = fields.Date.today()
        import datetime
        dow = str(today.weekday())  # 0=Monday

        # Today's classes from timetable
        today_classes = self.env['school.timetable'].search([
            ('teacher_id', '=', teacher.id),
            ('day_of_week', '=', dow),
        ], order='period_id')

        # Pending homework
        pending_hw = self.env['school.homework'].search_count([
            ('teacher_id', '=', teacher.id),
            ('state', '=', 'assigned'),
            ('due_date', '>=', today),
        ])

        # Attendance to mark today
        sections = teacher.section_ids
        attendance_done = self.env['school.attendance'].search_count([
            ('date', '=', today),
            ('section_id', 'in', sections.ids),
        ])

        return {
            'teacher_name': teacher.name,
            'today_classes': [
                {
                    'period': tc.period_id.name,
                    'subject': tc.subject_id.name if tc.subject_id else '',
                    'section': tc.section_id.display_name,
                }
                for tc in today_classes
            ],
            'pending_homework': pending_hw,
            'attendance_done': attendance_done > 0,
            'class_count': teacher.class_count,
        }

    @api.model
    def get_student_kpis(self, student_id=None):
        """KPIs for student dashboard."""
        if student_id:
            student = self.env['school.student'].browse(student_id)
        else:
            user = self.env.user
            student = self.env['school.student'].search([('user_id', '=', user.id)], limit=1)
        if not student:
            return {}

        return {
            'student_name': student.name,
            'class': student.class_id.name if student.class_id else '',
            'section': student.section_id.name if student.section_id else '',
            'attendance_percent': round(student.attendance_percent, 1),
            'fee_due': student.fee_due,
        }

    @api.model
    def get_fee_summary(self):
        """Fee collection summary by month (last 6 months)."""
        import datetime
        today = fields.Date.today()
        summary = []
        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - datetime.timedelta(days=i * 28)
            month_date = month_date.replace(day=1)
            next_month = (month_date.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            collected = sum(
                self.env['school.fee.payment'].search([
                    ('state', '=', 'confirmed'),
                    ('date', '>=', month_date),
                    ('date', '<', next_month),
                ]).mapped('amount')
            )
            summary.append({
                'month': month_date.strftime('%b %Y'),
                'collected': collected,
            })
        return summary
