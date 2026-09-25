from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.depends("unit_amount", "project_id", "project_id.hourly_rate")
    def compute_revenue(self):
        """Keep stored timesheet revenue synchronized with its project rate.

        The original customization depended on a non-stored related field.
        Depending on the source project field directly makes Odoo invalidate and
        recompute revenue when either hours, project, or billing rate changes.
        """
        for line in self:
            line.revenue = (line.unit_amount or 0.0) * (
                line.project_id.hourly_rate or 0.0
            )
