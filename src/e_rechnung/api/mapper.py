from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from e_rechnung.api.schemas import SapCompany, SapInvoiceRequest
from e_rechnung.models import Company, Invoice, InvoiceLine

# SAP unit codes -> UN/CEFACT unit codes
SAP_UNIT_MAP: dict[str, str] = {
    "ST": "C62",
    "STD": "HUR",
    "H": "HUR",
    "TAG": "DAY",
    "MON": "MON",
    "KG": "KGM",
    "M": "MTR",
    "L": "LTR",
    "PAU": "LS",
}

# SAP tax codes -> ZUGFeRD/XRechnung VAT category codes
# Extend as needed, e.g. "IC": "K", "RC": "AE"
SAP_TAX_CODE_MAP: dict[str, str] = {}

# SAP invoice kind -> type code
# Extend as needed, e.g. "R": "380", "G": "381"
SAP_KIND_MAP: dict[str, str] = {}


def parse_sap_date(value: str) -> date | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    # YYYYMMDD format
    if len(cleaned) == 8 and cleaned.isdigit():
        return date(int(cleaned[:4]), int(cleaned[4:6]), int(cleaned[6:8]))
    # ISO format YYYY-MM-DD
    if len(cleaned) == 10 and cleaned[4] == "-" and cleaned[7] == "-":
        return date.fromisoformat(cleaned)
    raise ValueError(f"Unbekanntes Datumsformat: {value!r}")


def map_unit_code(sap_unit: str) -> str:
    return SAP_UNIT_MAP.get(sap_unit.upper(), sap_unit)


def map_tax_code(tax_code: str, tax_percent: Decimal) -> str:
    if tax_code and tax_code in SAP_TAX_CODE_MAP:
        return SAP_TAX_CODE_MAP[tax_code]
    if tax_percent == Decimal("0"):
        return "Z"
    return "S"


def _nonempty(value: str) -> str:
    """Treat SAP's numeric zero (coerced to '0') and blank strings as empty."""
    return "" if value in ("", "0") else value


def map_sap_company(data: SapCompany) -> Company:
    return Company(
        name=data.name,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        postcode=data.postcode,
        city=data.city,
        country_code=data.country_code,
        vat_id=data.vat_id,
        tax_number=data.tax_number,
        contact_name=data.contact_name,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email,
        iban=data.iban,
        bic=data.bic,
        bank_name=data.bank_name,
        invoice_prefix=data.invoice_prefix,
    )


def map_sap_to_invoice(request: SapInvoiceRequest, company: Company) -> Invoice:
    head = request.head
    debtor = request.debtor

    # Build invoice number with company prefix
    inv_num = _nonempty(head.invoice_number)
    number = f"{company.invoice_prefix}{inv_num}" if inv_num else ""

    # Type code
    type_code = SAP_KIND_MAP.get(head.invoice_kind, "380") if head.invoice_kind else "380"

    # Customer name
    name_parts = [debtor.debtor_name1, debtor.debtor_name2]
    customer_name = " ".join(p for p in name_parts if p).strip()

    # Customer address
    street_parts = [debtor.debtor_street, debtor.debtor_house_num1]
    address_line1 = " ".join(p for p in street_parts if p).strip()
    customer_address = {
        "address_line1": address_line1,
        "postcode": debtor.debtor_post_code1,
        "city": debtor.debtor_city1,
        "country_code": debtor.debtor_country or "DE",
    }

    # Build lines
    lines: list[InvoiceLine] = []
    period_starts: list[date] = []
    period_ends: list[date] = []

    for pos in request.position:
        try:
            quantity = Decimal(pos.amount)
        except (InvalidOperation, ValueError):
            quantity = Decimal("1")

        try:
            unit_price = Decimal(pos.unit_price)
        except (InvalidOperation, ValueError):
            unit_price = Decimal("0")

        try:
            vat_rate = Decimal(pos.tax_percent)
        except (InvalidOperation, ValueError):
            vat_rate = Decimal("19")

        sort_order = int(pos.invoice_pos) if pos.invoice_pos.isdigit() else 0

        line = InvoiceLine(
            line_id=sort_order,
            description=pos.work_pool_free_text,
            quantity=quantity,
            unit_code=map_unit_code(pos.unit),
            unit_price=unit_price,
            vat_rate=vat_rate,
            vat_category_code=map_tax_code(pos.tax_code, vat_rate),
            sort_order=sort_order,
        )
        lines.append(line)

        # Collect period dates
        d_from = parse_sap_date(pos.work_pool_date_from)
        d_to = parse_sap_date(pos.work_pool_date_to)
        if d_from:
            period_starts.append(d_from)
        if d_to:
            period_ends.append(d_to)

    invoice = Invoice(
        number=number,
        type_code=type_code,
        issue_date=parse_sap_date(head.invoice_date),
        due_date=parse_sap_date(head.due_date),
        currency=head.invoice_currency or "EUR",
        payment_terms=head.invoice_zterm_text,
        order_reference=_nonempty(head.aufnr),
        note=head.subject_freetext,
        customer_contact_email=head.contact_mail,
        preceding_invoice_number=_nonempty(head.ref_invoice_number),
        customer_name=customer_name,
        customer_address=customer_address,
        customer_vat_id=debtor.debtor_stceg,
        buyer_reference=debtor.debtor_kunnr,
        period_start=min(period_starts) if period_starts else None,
        period_end=max(period_ends) if period_ends else None,
        lines=lines,
    )

    invoice.calculate_totals()
    return invoice
