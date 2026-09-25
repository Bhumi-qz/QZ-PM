{
    'name': "Profitability Dashboard",
    'version': '19.0.2.12.0',
    'category': 'Services/Project',
    'summary': "Project allocated revenue less timesheet employee costs, by customer and consultant.",
    'description': """
Profitability Dashboard
===================================
Adds:
  * Uses the project hourly rate and employee hourly cost supplied by dependencies.
  * A reporting model that counts allocated project revenue once and subtracts
    timesheet hours multiplied by employee cost, grouped by consultant/customer.
  * Two native Community spreadsheet dashboards under Human Resources:
    Consultant-wise and Customer-wise, with KPIs and profitability analysis.
  * A standard Pivot/Graph/List view on the underlying report model for
    further ad-hoc analysis (group by project, customer, month, etc).

Built on top of Odoo 19 Community's hr_timesheet app - no Enterprise
"Profitability" features are required.
    """,
    'author': "QZ",
    'license': 'LGPL-3',
    'depends': [
        'hr_timesheet',
        'project',
        'web',
        'spreadsheet_dashboard',
        'qz_customization',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/profitability_report_views.xml',
        'views/profitability_dashboard_views.xml',
        'data/profitability_dashboards.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'qz_profitability_reports/static/src/js/profitability_dashboard.js',
            'qz_profitability_reports/static/src/xml/profitability_dashboard.xml',
        ],
        'web.assets_backend': [
            'qz_profitability_reports/static/src/scss/profitability_dashboard.scss',
        ],
    },
    'installable': True,
    'application': False,
}
