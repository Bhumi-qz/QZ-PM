from odoo import fields, models


class ProjectProfitabilityReport(models.Model):
    _name = "x_project_profitability_report"
    _description = "Project Profitability Report"

    name = fields.Char(string="Name")
    budget = fields.Float(string="Budget")
    actual_cost = fields.Float(string="Actual Cost")
    hourly_cost = fields.Float(string="Hourly Cost")
    profitability_pct = fields.Float(string="Profitability Percentage")
    project_id = fields.Many2one("project.project", string="Project")
    remaining_budget = fields.Float(string="Remaining Budget")
    snapshot_date = fields.Date(string="Date")
    total_hours = fields.Float(string="Total Hours Spent")