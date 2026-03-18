from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from lxml import etree

from e_rechnung.models import Company, Invoice
from e_rechnung.validators import has_critical_errors, validate_for_xrechnung

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

_EXEMPTION_REASONS = {
    "K": "Intra-Community supply",
    "G": "Export supply",
    "AE": "Reverse charge",
    "E": "Exempt from tax",
}


def export_xrechnung(invoice: Invoice, company: Company, output_path: str) -> None:
    errors = validate_for_xrechnung(invoice, company)
    if has_critical_errors(errors):
        msg = "\n".join(f"{e.field}: {e.message}" for e in errors if e.severity == "error")
        raise ValueError(f"Validierungsfehler:\n{msg}")

    addr = invoice.customer_address or {}
    tax_breakdown = invoice.get_tax_breakdown()

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("xrechnung.xml")

    xml_str = template.render(
        invoice=invoice,
        company=company,
        addr=addr,
        tax_breakdown=tax_breakdown,
        exemption_reasons=_EXEMPTION_REASONS,
    )

    etree.fromstring(xml_str.encode("utf-8"))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
