from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from drafthorse.models.accounting import ApplicableTradeTax
from drafthorse.models.document import Document
from drafthorse.models.note import IncludedNote
from drafthorse.models.party import TaxRegistration
from drafthorse.models.payment import PaymentMeans, PaymentTerms
from drafthorse.models.tradelines import LineItem
from drafthorse.pdf import attach_xml

from e_rechnung.models import Company, Invoice, InvoiceLine
from e_rechnung.pdf_render import render_pdf
from e_rechnung.utils import FACTUR_X_GUIDELINE, PROFILE, round_decimal
from e_rechnung.validators import has_critical_errors, validate_for_zugferd


_EXEMPTION_MAP = {
    "K": ("VATEX-EU-IC", "Intra-Community supply"),
    "G": ("VATEX-EU-EXP", "Export supply"),
    "AE": ("VATEX-EU-AE", "Reverse charge"),
    "E": ("VATEX-EU-132", "Exempt from tax"),
}


def create_trade_tax(
    amount: Decimal, basis_amount: Decimal, category_code: str, vat_rate: Decimal,
) -> ApplicableTradeTax:
    trade_tax = ApplicableTradeTax()
    trade_tax.calculated_amount = round_decimal(amount)
    trade_tax.basis_amount = round_decimal(basis_amount)
    trade_tax.type_code = "VAT"
    trade_tax.category_code = category_code
    trade_tax.rate_applicable_percent = vat_rate
    if category_code in _EXEMPTION_MAP:
        code, reason = _EXEMPTION_MAP[category_code]
        trade_tax.exemption_reason_code = code
        trade_tax.exemption_reason = reason
    return trade_tax


def create_line_item(line: InvoiceLine) -> LineItem:
    item = LineItem()
    item.document.line_id = str(line.line_id)
    item.product.name = line.description
    if line.article_number:
        item.product.seller_assigned_id = line.article_number
    item.agreement.net.amount = line.unit_price
    item.agreement.net.basis_quantity = (Decimal("1"), line.unit_code)
    item.delivery.billed_quantity = (line.quantity, line.unit_code)
    item.settlement.trade_tax.type_code = "VAT"
    item.settlement.trade_tax.category_code = line.vat_category_code
    item.settlement.trade_tax.rate_applicable_percent = line.vat_rate
    item.settlement.monetary_summation.total_amount = round_decimal(line.line_total)
    return item


def export_zugferd(invoice: Invoice, company: Company, output_path: str) -> None:
    errors = validate_for_zugferd(invoice, company)
    if has_critical_errors(errors):
        msg = "\n".join(f"{e.field}: {e.message}" for e in errors if e.severity == "error")
        raise ValueError(f"Validierungsfehler:\n{msg}")

    pdf_bytes = render_pdf(invoice, company)

    doc = Document()
    doc.context.guideline_parameter.id = FACTUR_X_GUIDELINE

    # Header
    doc.header.id = invoice.number
    doc.header.type_code = invoice.type_code
    doc.header.name = "RECHNUNG" if invoice.type_code == "380" else "GUTSCHRIFT"
    doc.header.issue_date_time = invoice.issue_date

    # Billing period note
    if invoice.period_start and invoice.period_end:
        note = IncludedNote()
        note.content = (
            f"Leistungszeitraum: {invoice.period_start.strftime('%d.%m.%Y')} "
            f"bis {invoice.period_end.strftime('%d.%m.%Y')}"
        )
        note.subject_code = "AAI"
        doc.header.notes.add(note)

    # Seller
    doc.trade.agreement.seller.name = company.name
    doc.trade.agreement.seller.address.line_one = company.address_line1
    if company.address_line2:
        doc.trade.agreement.seller.address.line_two = company.address_line2
    doc.trade.agreement.seller.address.city_name = company.city
    doc.trade.agreement.seller.address.postcode = company.postcode
    doc.trade.agreement.seller.address.country_id = company.country_code

    if company.vat_id:
        tax_reg = TaxRegistration()
        tax_reg.id = ("VA", company.vat_id)
        doc.trade.agreement.seller.tax_registrations.add(tax_reg)
    if company.tax_number:
        tax_reg = TaxRegistration()
        tax_reg.id = ("FC", company.tax_number)
        doc.trade.agreement.seller.tax_registrations.add(tax_reg)

    if company.contact_name:
        doc.trade.agreement.seller.contact.person_name = company.contact_name
    if company.contact_phone:
        doc.trade.agreement.seller.contact.telephone.number = company.contact_phone
    if company.contact_email:
        doc.trade.agreement.seller.contact.email.address = company.contact_email

    # Buyer (from snapshot)
    addr = invoice.customer_address or {}
    doc.trade.agreement.buyer.name = invoice.customer_name
    if addr.get("address_line1"):
        doc.trade.agreement.buyer.address.line_one = addr["address_line1"]
    if addr.get("address_line2"):
        doc.trade.agreement.buyer.address.line_two = addr["address_line2"]
    if addr.get("city"):
        doc.trade.agreement.buyer.address.city_name = addr["city"]
    if addr.get("postcode"):
        doc.trade.agreement.buyer.address.postcode = addr["postcode"]
    if addr.get("country_code"):
        doc.trade.agreement.buyer.address.country_id = addr["country_code"]

    if invoice.buyer_reference:
        doc.trade.agreement.buyer_reference = invoice.buyer_reference

    if invoice.customer_vat_id:
        buyer_tax = TaxRegistration()
        buyer_tax.id = ("VA", invoice.customer_vat_id)
        doc.trade.agreement.buyer.tax_registrations.add(buyer_tax)

    # References
    if invoice.order_reference:
        doc.trade.agreement.buyer_order.issuer_assigned_id = invoice.order_reference
    if invoice.contract_reference:
        doc.trade.agreement.contract.issuer_assigned_id = invoice.contract_reference

    # Preceding invoice (for credit notes)
    if invoice.preceding_invoice_number:
        doc.trade.settlement.invoice_referenced_document.issuer_assigned_id = invoice.preceding_invoice_number
        if invoice.preceding_invoice_date:
            doc.trade.settlement.invoice_referenced_document.issue_date_time = invoice.preceding_invoice_date

    # Delivery
    doc.trade.delivery.event.occurrence = (
        invoice.delivery_date or invoice.period_end or invoice.issue_date
    )

    if invoice.period_start and invoice.period_end:
        doc.trade.settlement.period.start = invoice.period_start
        doc.trade.settlement.period.end = invoice.period_end

    # Currency
    doc.trade.settlement.currency_code = invoice.currency

    # Payment means
    payment_means = PaymentMeans()
    payment_means.type_code = invoice.payment_means_code
    if company.iban:
        payment_means.payee_account.iban = company.iban
    if company.bic:
        payment_means.payee_institution.bic = company.bic
    doc.trade.settlement.payment_means.add(payment_means)

    # Payment terms
    if invoice.due_date:
        terms = PaymentTerms()
        terms.due = invoice.due_date
        if invoice.payment_terms:
            terms.description = invoice.payment_terms
        else:
            terms.description = f"Zahlbar bis {invoice.due_date.strftime('%d.%m.%Y')}."

        # Skonto (EXTENDED profile)
        if invoice.skonto_percent and invoice.skonto_days and invoice.issue_date:
            terms.discount_terms.calculation_percent = invoice.skonto_percent
            terms.discount_terms.basis_date_time = invoice.issue_date
            terms.discount_terms.basis_period_measure = (invoice.skonto_days, "DAY")

        doc.trade.settlement.terms.add(terms)

    # Line items
    for line in invoice.lines:
        doc.trade.items.add(create_line_item(line))

    # Tax breakdown (mixed VAT support)
    for group in invoice.get_tax_breakdown():
        doc.trade.settlement.trade_tax.add(
            create_trade_tax(
                amount=group["tax_amount"],
                basis_amount=group["basis_amount"],
                category_code=group["category_code"],
                vat_rate=group["rate"],
            )
        )

    # Monetary summation
    ms = doc.trade.settlement.monetary_summation
    ms.line_total = round_decimal(invoice.total_net)
    ms.charge_total = Decimal("0.00")
    ms.allowance_total = Decimal("0.00")
    ms.tax_basis_total = round_decimal(invoice.total_net)
    ms.tax_total = (round_decimal(invoice.vat_amount), invoice.currency)
    ms.grand_total = round_decimal(invoice.total_gross)
    prepaid = invoice.prepaid_amount or Decimal("0.00")
    ms.prepaid_total = round_decimal(prepaid)
    due = invoice.due_payable_amount if invoice.due_payable_amount is not None else invoice.total_gross
    ms.due_amount = round_decimal(due)

    # Serialize
    xml_data = doc.serialize(schema="FACTUR-X_EXTENDED")

    metadata = {
        "author": company.name,
        "keywords": "Factur-X, ZUGFeRD, Rechnung",
        "title": f"{company.name}: Rechnung {invoice.number}",
        "creator": "E-Rechnung App",
        "producer": "WeasyPrint + drafthorse",
        "subject": f"Factur-X Rechnung {invoice.number}",
    }

    zugferd_pdf = attach_xml(pdf_bytes, xml_data, level=PROFILE, metadata=metadata)

    with open(output_path, "wb") as f:
        f.write(zugferd_pdf)
