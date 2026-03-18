from datetime import date
from decimal import Decimal

from e_rechnung.models import Company, Invoice, InvoiceLine
from e_rechnung.validators import has_critical_errors, validate_for_xrechnung, validate_for_zugferd


def _valid_company():
    return Company(
        name="Test GmbH", address_line1="Teststr. 1", postcode="12345",
        city="Berlin", vat_id="DE123456789", contact_name="Max Mustermann",
        contact_email="test@test.de", contact_phone="+49 123 456",
        iban="DE89370400440532013000",
    )


def _valid_invoice():
    line = InvoiceLine(
        description="Beratung", quantity=Decimal("1.000"),
        unit_price=Decimal("100.00"), line_total=Decimal("100.00"),
    )
    return Invoice(
        number="RE-2026-00001", issue_date=date(2026, 1, 15),
        due_date=date(2026, 1, 29),
        customer_name="Kunde AG",
        customer_address={
            "address_line1": "Kundenstr. 2",
            "postcode": "54321",
            "city": "Muenchen",
            "country_code": "DE",
        },
        customer_vat_id="DE987654321",
        buyer_reference="04011000-12345-67",
        customer_contact_email="kunde@test.de",
        total_net=Decimal("100.00"), vat_amount=Decimal("19.00"),
        total_gross=Decimal("119.00"),
        lines=[line],
    )


def test_valid_zugferd():
    errors = validate_for_zugferd(_valid_invoice(), _valid_company())
    assert not has_critical_errors(errors)


def test_missing_company_name():
    company = _valid_company()
    company.name = ""
    errors = validate_for_zugferd(_valid_invoice(), company)
    assert has_critical_errors(errors)
    assert any("Firmenname" in e.message for e in errors)


def test_missing_iban():
    company = _valid_company()
    company.iban = ""
    errors = validate_for_zugferd(_valid_invoice(), company)
    assert any("IBAN" in e.message for e in errors)


def test_missing_customer_name():
    inv = _valid_invoice()
    inv.customer_name = ""
    errors = validate_for_zugferd(inv, _valid_company())
    assert has_critical_errors(errors)


def test_missing_invoice_number():
    inv = _valid_invoice()
    inv.number = ""
    errors = validate_for_zugferd(inv, _valid_company())
    assert has_critical_errors(errors)


def test_no_positions():
    inv = _valid_invoice()
    inv.lines = []
    errors = validate_for_zugferd(inv, _valid_company())
    assert has_critical_errors(errors)


def test_tax_id_or_vat_id_required():
    company = _valid_company()
    company.vat_id = ""
    company.tax_number = ""
    errors = validate_for_zugferd(_valid_invoice(), company)
    assert has_critical_errors(errors)

    company.tax_number = "123/456/78901"
    errors = validate_for_zugferd(_valid_invoice(), company)
    assert not has_critical_errors(errors)


def test_xrechnung_needs_buyer_reference():
    inv = _valid_invoice()
    inv.buyer_reference = ""
    errors = validate_for_xrechnung(inv, _valid_company())
    assert any("Leitweg-ID" in e.message for e in errors)


def test_xrechnung_needs_buyer_email():
    inv = _valid_invoice()
    inv.customer_contact_email = ""
    errors = validate_for_xrechnung(inv, _valid_company())
    assert any("E-Mail" in e.message for e in errors)


def test_customer_address_missing_fields():
    inv = _valid_invoice()
    inv.customer_address = {"country_code": "DE"}
    errors = validate_for_zugferd(inv, _valid_company())
    fields = [e.field for e in errors]
    assert "kunde.address_line1" in fields
    assert "kunde.postcode" in fields
    assert "kunde.city" in fields


def test_valid_xrechnung():
    errors = validate_for_xrechnung(_valid_invoice(), _valid_company())
    assert not has_critical_errors(errors)
