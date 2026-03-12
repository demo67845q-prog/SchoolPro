# -*- coding: utf-8 -*-
{
    'name': 'School Management System',
    'version': '18.0.1.0.0',
    'summary': 'Complete School ERP — Students, Teachers, Fees, Exams, Library, Transport',
    'description': """
School Management System for Odoo 18
======================================
* Student Admissions & Profiles
* Class, Section & Subject Management
* Teacher Management
* Timetable
* Attendance (Student & Teacher)
* Fee Structure, Invoices & Payments
* Examinations & Report Cards
* Homework & Submissions
* Library Management
* Transport Management
* Hostel Management
* Announcements & Notifications
* OWL Dashboard
* Reports: Student List, Fee Invoice, Report Card
* 9 Security Roles with Record Rules
    """,
    'author': 'Ankit',
    'category': 'Education',
    'sequence': 95,
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        # Security — load groups first
        'security/school_security_groups.xml',
        'security/ir.model.access.csv',
        'security/school_record_rules.xml',
        # Data
        'data/school_sequences.xml',
        'data/school_demo_data.xml',
        # Views
        'views/school_config_views.xml',
        'views/school_class_views.xml',
        'views/school_student_views.xml',
        'views/school_teacher_views.xml',
        'views/school_timetable_views.xml',
        'views/school_attendance_views.xml',
        'views/school_fees_views.xml',
        'views/school_exam_views.xml',
        'views/school_homework_views.xml',
        'views/school_library_views.xml',
        'views/school_transport_views.xml',
        'views/school_hostel_views.xml',
        'views/school_communication_views.xml',
        'views/school_dashboard_views.xml',
        # Reports
        'report/school_student_report.xml',
        'report/school_fee_receipt.xml',
        'report/school_report_card.xml',
        # Menus (last — all actions must exist)
        'views/school_menus.xml',
        # Cron
        'data/school_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'school_management/static/src/css/school_dashboard.css',
            'school_management/static/src/js/school_dashboard.js',
            'school_management/static/src/xml/school_dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'web_icon': 'school_management,static/description/icon.png',
}
