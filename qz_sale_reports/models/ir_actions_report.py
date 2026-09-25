import base64
from functools import lru_cache
from io import BytesIO

from odoo import fields, models
from odoo.tools import file_open
from odoo.tools.misc import format_date
from odoo.tools.pdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


@lru_cache(maxsize=16)
def _asset_bytes(name):
    with file_open('qz_sale_reports/static/src/' + name, 'rb') as stream:
        return stream.read()


@lru_cache(maxsize=1)
def _register_fonts():
    for name in ('Light', 'Medium', 'Bold'):
        pdfmetrics.registerFont(TTFont(
            'QZPoppins' + name, BytesIO(_asset_bytes('fonts/Poppins-' + name + '.ttf')),
        ))


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _qz_reference_pdf(self, content, order, amc=False):
        """Apply reference branding while preserving AMC pages and sales body text."""
        _register_fonts()
        reader = PdfReader(BytesIO(content))
        writer = PdfWriter()
        for index, page in enumerate(reader.pages):
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            artwork = BytesIO()
            drawing = canvas.Canvas(artwork, pagesize=(width, height))
            mm = width / 210
            if index == 0 and not amc:
                drawing.drawImage(
                    ImageReader(BytesIO(_asset_bytes('img/cover.png'))),
                    0, 0, width=width, height=height,
                )
                drawing.setFillColorRGB(.15, .15, .15)

                def centered(text, top, size, max_width=178):
                    font = 'QZPoppinsMedium'
                    while size > 10 and pdfmetrics.stringWidth(text, font, size) > max_width * mm:
                        size -= .5
                    drawing.setFont(font, size)
                    drawing.drawCentredString(width / 2, height - top * mm, text)

                centered(order.company_id.name or '', 163.3, 24)
                centered('Odoo ERP Implementation Proposal', 179.8, 24)
                centered(order.partner_id.name or '', 195.65, 22)
                if order.partner_id.image_1920:
                    drawing.drawImage(
                        ImageReader(BytesIO(base64.b64decode(order.partner_id.image_1920))),
                        width / 2 - 20 * mm, height - 221 * mm,
                        width=40 * mm, height=24 * mm, preserveAspectRatio=True,
                        anchor='c', mask='auto',
                    )
                date = fields.Date.to_date(order.date_order)
                centered(format_date(order.env, date, date_format='EEEE, d MMMM yyyy'), 232, 12)
                # The supplied artwork contains the original QZ cover branding.
                # Customer-specific content remains live text, not a screenshot.
                drawing.showPage()
                drawing.save()
                writer.add_page(PdfReader(BytesIO(artwork.getvalue())).pages[0])
            else:
                if amc:
                    drawing.drawImage(
                        ImageReader(BytesIO(_asset_bytes('img/amc_corner.png'))),
                        163.49 * mm, height - 46.94 * mm,
                        width=46.50 * mm, height=46.94 * mm, mask='auto',
                    )
                    drawing.drawImage(
                        ImageReader(BytesIO(_asset_bytes('img/amc_corner_logo.png'))),
                        178.95 * mm, height - 33.02 * mm,
                        width=24.98 * mm, height=24.98 * mm, mask='auto',
                    )
                else:
                    drawing.saveState()
                    drawing.setFillAlpha(.55)
                    drawing.drawImage(
                        ImageReader(BytesIO(_asset_bytes('img/corner_circle.png'))),
                        168.275 * mm, height - 41.275 * mm,
                        width=102.447 * mm, height=102.447 * mm, mask='auto',
                    )
                    drawing.restoreState()
                    drawing.drawImage(
                        ImageReader(BytesIO(_asset_bytes('img/corner_logo.png'))),
                        186.275 * mm, height - 23.92 * mm,
                        width=16.3 * mm, height=16.3 * mm, mask='auto',
                    )
                drawing.showPage()
                drawing.save()
                page.merge_page(PdfReader(BytesIO(artwork.getvalue())).pages[0])
                writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        return output

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)
        if report.report_name not in (
                'qz_sale_reports.report_sale_proposal', 'qz_sale_reports.report_amc',
        ):
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        if res_ids and len(res_ids) > 1:
            # Separate rendering keeps each cover, customer and page count local
            # to its quotation, regardless of wkhtmltopdf outline splitting.
            collected = {}
            for record_id in dict.fromkeys(res_ids):
                collected.update(self._render_qweb_pdf_prepare_streams(
                    report_ref, data, res_ids=[record_id],
                ))
            return collected
        streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        for order in self.env['sale.order'].browse(res_ids or []):
            item = streams.get(order.id)
            if item and item.get('stream'):
                original = item['stream']
                item['stream'] = self._qz_reference_pdf(
                    original.getvalue(), order,
                    amc=report.report_name == 'qz_sale_reports.report_amc',
                )
                original.close()
                if report.report_name == 'qz_sale_reports.report_sale_proposal' and order.qz_add_amc and order.qz_attach_amc:
                    amc_content, _ = self._render_qweb_pdf(
                        'qz_sale_reports.report_amc', res_ids=order.ids,
                    )
                    proposal = item['stream']
                    writer = PdfWriter()
                    for content in (proposal.getvalue(), amc_content):
                        for page in PdfReader(BytesIO(content)).pages:
                            writer.add_page(page)
                    combined = BytesIO()
                    writer.write(combined)
                    combined.seek(0)
                    item['stream'] = combined
                    proposal.close()
        return streams
