from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qz_amc_annual_hours = fields.Float(
        string='AMC Annual Hours',
        help='Total annual hours for this line, not hours per unit of quantity.',
    )
    qz_amc_annual_fee = fields.Monetary(
        string='AMC Annual Fee', related='price_subtotal',
        currency_field='currency_id', readonly=True,
    )

    def _qz_customisation_description(self):
        """Remove only the product heading, preserving the edited line description."""
        self.ensure_one()
        text = (self.name or '').strip()
        product = self.product_id.with_context(lang=self.order_id._get_lang())
        headings = {
            (product.name or '').strip(),
            (product.display_name or '').strip(),
            (product.with_context(display_default_code=False).display_name or '').strip(),
        }
        first_line, separator, description = text.partition('\n')
        if first_line.strip() in headings:
            return description.strip() if separator else ''
        return text

    @api.constrains('qz_amc_annual_hours')
    def _check_amc_hours(self):
        if any(line.qz_amc_annual_hours < 0 for line in self):
            raise ValidationError(_('AMC annual hours cannot be negative.'))
