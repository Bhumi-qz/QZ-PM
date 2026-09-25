from odoo import fields, models


class BudgetLine(models.Model):
    _inherit = "budget.line"

    plan2_id = fields.Many2one(
        "account.analytic.account", string="Project", index=True
    )
