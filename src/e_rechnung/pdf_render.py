from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from e_rechnung.models import Company, Invoice
from e_rechnung.utils import format_betrag

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def render_pdf(invoice: Invoice, company: Company) -> bytes:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.filters["betrag"] = format_betrag

    addr = invoice.customer_address or {}
    tax_breakdown = invoice.get_tax_breakdown()

    template = env.get_template("invoice.html")
    html_str = template.render(
        invoice=invoice,
        company=company,
        addr=addr,
        tax_breakdown=tax_breakdown,
    )
    return HTML(
        string=html_str,
        base_url=str(TEMPLATES_DIR),
    ).write_pdf(pdf_variant="pdf/a-3b")
