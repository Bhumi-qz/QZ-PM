from markupsafe import Markup, escape
from odoo import _, api
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html_sanitize
import base64
from functools import lru_cache

from odoo import fields, models
from odoo.tools import file_open


@lru_cache(maxsize=16)
def _asset_bytes(name):
    with file_open('qz_sale_reports/static/src/' + name, 'rb') as stream:
        return stream.read()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    qz_attach_amc = fields.Boolean(
        string='Attach AMC Agreement',
        default=False,
        help='Append the AMC Agreement when printing the Sales Proposal.',
    )
    qz_add_amc = fields.Boolean(
        string='Add AMC', default=False,
        help='Include the AMC Agreement in customer preview and signed attachments.',
    )

    qz_reviewed_by_id = fields.Many2one(
        'res.users', string='Reviewed By', readonly=True, copy=False, tracking=True,
    )
    qz_authorized_by_id = fields.Many2one(
        'res.users', string='Authorized By', readonly=True, copy=False, tracking=True,
    )

    qz_client_references_html = fields.Html(
        string='Client References',
        default='<p><img src="/qz_sale_reports/static/src/img/client_references.png" '
                'style="width:100%;height:auto;" alt="Client references"/></p>',
    )

    qz_doc_version = fields.Char('Document Version', default='1.1')
    qz_implementation_overview = fields.Html(
        string='Project Implementation Overview',

    )
    qz_propsed_solution_details = fields.Html(
        string='Proposed Solution Details and Scope',

    )
    qz_business_description = fields.Text('Business Description')
    qz_scope_html = fields.Html(string='Implementation Scope')
    qz_out_of_scope_html = fields.Html(string='Out of Scope Tasks')
    qz_assumptions_html = fields.Html(
        string='Project Assumptions'
    )
    qz_timeline = fields.Char('Implementation Timeline', help='For example: 14Ã¢â‚¬â€œ16 weeks.')
    qz_sales_validity = fields.Date('Proposal Valid Until', related='validity_date', readonly=False)
    qz_amc_annual_hours = fields.Float(
        string='AMC Annual Hours', compute='_compute_amc_totals',
    )
    qz_amc_annual_fee = fields.Monetary(
        string='AMC Annual Fee', compute='_compute_amc_totals',
        currency_field='currency_id',
    )
    qz_amc_carry_forward_percent = fields.Float(
        string='Unused AMC Hours Carry Forward (%)'
    )
    qz_amc_extra_hour_rate = fields.Monetary(
        string='AMC Additional Hour Rate', currency_field='currency_id',
    )
    qz_amc_validity = fields.Date(
        string='AMC Valid Until', related='validity_date', readonly=False,
    )

    def _qz_discount_lines(self):
        self.ensure_one()
        product = self.company_id.sale_discount_product_id
        return self.order_line.filtered(
            lambda line: not line.display_type and not line.is_downpayment
            and product and line.product_id == product
        )

    def _qz_proposal_lines(self, customisation=False):
        self.ensure_one()
        lines = self.order_line - self._qz_discount_lines()
        return lines.filtered(
            lambda line: not line.display_type and not line.is_downpayment
            and line.product_id
            and bool(line.product_id.customisation) == customisation
            and (customisation or line.product_id.type != 'service')
        )

    def _qz_signed_attachments(self):
        self.ensure_one()
        reports = self.env['ir.actions.report']
        proposal, _ = reports._render_qweb_pdf(
            'qz_sale_reports.report_sale_proposal', self.ids,
        )
        attachments = [('Sales Proposal - %s.pdf' % self.name, proposal)]
        if self.qz_add_amc and not self.qz_attach_amc:
            amc, _ = reports._render_qweb_pdf('qz_sale_reports.report_amc', self.ids)
            attachments.append(('AMC Agreement - %s.pdf' % self.name, amc))
        return attachments

    def message_post(self, **kwargs):
        # Replace only the signed-order PDF posted by Odoo's acceptance endpoint.
        # Confirmation emails and other chatter attachments keep their normal flow.
        if (len(self) == 1 and self.env.context.get('qz_accept_order_id') == self.id
                and self.signature and kwargs.get('attachments')
                and len(kwargs['attachments']) == 1
                and kwargs['attachments'][0][0] == '%s.pdf' % self.name):
            kwargs['attachments'] = self._qz_signed_attachments()
        return super().message_post(**kwargs)

    @api.depends(
        'order_line.qz_amc_annual_hours', 'order_line.price_subtotal',
        'order_line.display_type', 'order_line.is_downpayment',
    )
    def _compute_amc_totals(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda line: not line.display_type and not line.is_downpayment
            )
            order.update({'qz_amc_annual_hours': sum(lines.mapped('qz_amc_annual_hours')),
                          'qz_amc_annual_fee': sum(lines.mapped('price_subtotal'))})

    @api.constrains('qz_amc_carry_forward_percent', 'qz_amc_extra_hour_rate')
    def _check_amc_terms(self):
        for order in self:
            if not 0 <= order.qz_amc_carry_forward_percent <= 100:
                raise ValidationError(_('AMC carry-forward percentage must be between 0 and 100.'))
            if order.qz_amc_extra_hour_rate < 0:
                raise ValidationError(_('AMC additional hour rate cannot be negative.'))

    def action_qz_review(self):
        self.check_access('write')
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            raise AccessError(_('Only sales users can review proposals.'))
        self.filtered(lambda order: not order.qz_reviewed_by_id).write({
            'qz_reviewed_by_id': self.env.user.id,
        })
        return True

    def action_qz_authorize(self):
        self.check_access('write')
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            raise AccessError(_('Only sales users can authorize proposals.'))
        self.filtered(lambda order: not order.qz_authorized_by_id).write({
            'qz_authorized_by_id': self.env.user.id,
        })
        return True

    def _qz_document_html(self, field_name):
        self.ensure_one()
        content = str(html_sanitize(self[field_name] or ''))
        replacements = (
            ('{{customer_name}}', self.partner_id.name),
            ('{{company_name}}', self.company_id.name),
        )
        for token, value in replacements:
            content = content.replace(token, str(escape(value or '')))
        return Markup(content)

    def _qz_reference_asset(self, name):
        allowed = {
            'fonts/Poppins-Light.ttf': 'font/ttf',
            'fonts/Poppins-Medium.ttf': 'font/ttf',
            'fonts/Poppins-Bold.ttf': 'font/ttf',
        }
        if name not in allowed:
            raise ValueError('Unsupported proposal asset')
        return 'data:%s;base64,%s' % (
            allowed[name], base64.b64encode(_asset_bytes(name)).decode('ascii'),
        )
