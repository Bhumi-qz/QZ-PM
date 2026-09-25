from odoo import fields, models

class BudgetReport(models.Model):
    _inherit = "budget.report"

    plan2_id = fields.Many2one("account.analytic.account", string="Project")
