from odoo import fields, models, api


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    cost = fields.Float(string="Cost", store=True, compute='compute_cost')
    customer_id = fields.Many2one(
        "res.partner", string="Customer", store=True, related='project_id.partner_id'
    )
    employee_cost = fields.Monetary(
        string="employee Hour cost",
        store=True,
        currency_field="currency_id", related='employee_id.hourly_cost'
    )
    hourly_rate_text = fields.Text(string="Hourly Rate", index=True, related='project_id.hourly_rate_text')
    project_hourly_rate = fields.Float(string="Project Hourly Rate", related='project_id.hourly_rate')
    project_total_hours = fields.Float(
        string="Project Total Hours", related='project_id.allocated_hours', store=True
    )
    revenue = fields.Float(string="Revenue", store=True, compute='compute_revenue')
    plan2_id = fields.Many2one("account.analytic.account", string="Project")

    @api.depends('employee_cost', 'unit_amount')
    def compute_cost(self):
        for res in self:
            res.cost = (res.unit_amount or 0.0) * (res.employee_cost or 0.0)

    @api.depends('project_hourly_rate', 'unit_amount')
    def compute_revenue(self):
        for res in self:
            res.revenue = (res.project_id.allocated_hours or 0.0) * (res.project_id.hourly_rate or 0.0)