{
    "name": "QZ Studio Field Cleanup",
    "version": "19.0.1.0.0",
    "summary": "Replaces ad-hoc Studio x_ fields with properly named fields "
                "and migrates their data",
    "description": """
QZ Studio Field Cleanup
========================
Adds cleanly-named fields (x_ prefix stripped, many2one suffixed with
_id, many2many/one2many suffixed with _ids) alongside the original Odoo
Studio custom fields, then copies existing data from the old x_ fields
into the new ones via a post_init_hook (direct SQL column copy - fast
and bypasses any ORM constraints/compute logic on the old fields).

ASSUMPTIONS - please verify against your database before installing:
-----------------------------------------------------------------------
1. "Project Profitability Report" custom model technical name is assumed
   to be x_project_profitability_report.
2. "Budget Line" custom model technical name is assumed to be
   x_budget_line.
3. "Budget Report" custom model technical name is assumed to be
   x_budget_report.
4. The source row (x_name / Name / "General / Main" / char) had no clear
   model in the field list provided, so it has been assigned to
   x_budget_report.name. Confirm this is correct or move it in
   models/budget_report.py.

If any technical name above is wrong, either rename the _inherit value
in the matching file under models/, or update the model in Odoo Studio
first so it matches. The post_init_hook will log a warning and skip
(not crash) any table/column it can't find, so a wrong guess here is
safe to fix and re-run manually afterwards.
    """,
    "category": "Project",
    "depends": ["project", "analytic", "account", "hr_timesheet"],
    "data": [
        'data/server_action.xml',
        'views/view_inherits.xml'
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    'auto_install': False,
}
