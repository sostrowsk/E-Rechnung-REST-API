from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from e_rechnung.api.mapper import (
    SAP_TAX_CODE_MAP,
    map_sap_company,
    map_sap_to_invoice,
    map_tax_code,
    map_unit_code,
    parse_sap_date,
)
from e_rechnung.api.schemas import SapCompany, SapDebtor, SapHead, SapInvoiceRequest, SapPosition
from e_rechnung.models import Company


@pytest.fixture
def company():
    return Company(
        name="Test GmbH",
        address_line1="Teststr. 1",
        postcode="12345",
        city="Berlin",
        country_code="DE",
        vat_id="DE123456789",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        bank_name="Commerzbank",
        contact_name="Max Mustermann",
        contact_email="max@test.de",
        contact_phone="+49 30 12345",
        invoice_prefix="RE-",
    )


SAP_COMPANY = SapCompany(
    name="Test GmbH",
    addressLine1="Teststr. 1",
    postcode="12345",
    city="Berlin",
    countryCode="DE",
    vatId="DE123456789",
    iban="DE89370400440532013000",
    bic="COBADEFFXXX",
    bankName="Commerzbank",
    contactName="Max Mustermann",
    contactEmail="max@test.de",
    contactPhone="+49 30 12345",
    invoicePrefix="RE-",
)


def _make_request(
    *,
    invoice_number="SAP001",
    invoice_date="20260315",
    due_date="20260415",
    position=None,
    debtor=None,
    **head_kwargs,
) -> SapInvoiceRequest:
    head = SapHead(
        invoiceNumber=invoice_number,
        invoiceDate=invoice_date,
        dueDate=due_date,
        **head_kwargs,
    )
    if position is None:
        position = [
            SapPosition(
                invoicePos="10",
                workPoolFreeText="Beratung",
                amount="10",
                unit="STD",
                unitPrice="150.00",
                taxPercent="19",
            ),
        ]
    if debtor is None:
        debtor = SapDebtor(
            debtorKunnr="KUNNR-001",
            debtorName1="Kunde AG",
            debtorStreet="Kundenstr.",
            debtorHouseNum1="42",
            debtorPostCode1="80331",
            debtorCity1="München",
            debtorCountry="DE",
            debtorStceg="DE987654321",
        )
    return SapInvoiceRequest(head=head, position=position, debtor=debtor, company=SAP_COMPANY)


# --- parse_sap_date ---


class TestParseSapDate:
    def test_yyyymmdd(self):
        assert parse_sap_date("20260315") == date(2026, 3, 15)

    def test_iso(self):
        assert parse_sap_date("2026-03-15") == date(2026, 3, 15)

    def test_empty(self):
        assert parse_sap_date("") is None
        assert parse_sap_date("  ") is None

    def test_invalid(self):
        with pytest.raises(ValueError, match="Unbekanntes Datumsformat"):
            parse_sap_date("15.03.2026")


# --- map_unit_code ---


class TestMapUnitCode:
    def test_known(self):
        assert map_unit_code("STD") == "HUR"
        assert map_unit_code("ST") == "C62"
        assert map_unit_code("TAG") == "DAY"
        assert map_unit_code("H") == "HUR"
        assert map_unit_code("PAU") == "LS"

    def test_case_insensitive(self):
        assert map_unit_code("std") == "HUR"

    def test_unknown_passthrough(self):
        assert map_unit_code("XYZ") == "XYZ"


# --- map_tax_code ---


class TestMapTaxCode:
    def test_standard_rate(self):
        assert map_tax_code("", Decimal("19")) == "S"
        assert map_tax_code("", Decimal("7")) == "S"

    def test_zero_rate(self):
        assert map_tax_code("", Decimal("0")) == "Z"

    def test_known_code(self):
        SAP_TAX_CODE_MAP["IC"] = "K"
        try:
            assert map_tax_code("IC", Decimal("0")) == "K"
        finally:
            del SAP_TAX_CODE_MAP["IC"]

    def test_unknown_code_fallback_to_percent(self):
        assert map_tax_code("XX", Decimal("19")) == "S"
        assert map_tax_code("XX", Decimal("0")) == "Z"


# --- map_sap_company ---


class TestMapSapCompany:
    def test_basic_mapping(self):
        result = map_sap_company(SAP_COMPANY)
        assert result.name == "Test GmbH"
        assert result.address_line1 == "Teststr. 1"
        assert result.postcode == "12345"
        assert result.city == "Berlin"
        assert result.vat_id == "DE123456789"
        assert result.iban == "DE89370400440532013000"
        assert result.invoice_prefix == "RE-"


# --- map_sap_to_invoice ---


class TestMapSapToInvoice:
    def test_basic_mapping(self, company):
        req = _make_request()
        inv = map_sap_to_invoice(req, company)

        assert inv.number == "RE-SAP001"
        assert inv.issue_date == date(2026, 3, 15)
        assert inv.due_date == date(2026, 4, 15)
        assert inv.type_code == "380"
        assert inv.currency == "EUR"

    def test_customer_name_concat(self, company):
        debtor = SapDebtor(
            debtorName1="Firma",
            debtorName2="GmbH & Co. KG",
            debtorStreet="Str.",
            debtorHouseNum1="1",
            debtorPostCode1="10115",
            debtorCity1="Berlin",
        )
        req = _make_request(debtor=debtor)
        inv = map_sap_to_invoice(req, company)
        assert inv.customer_name == "Firma GmbH & Co. KG"

    def test_customer_name_single(self, company):
        debtor = SapDebtor(
            debtorName1="Einzelname",
            debtorStreet="Str.",
            debtorHouseNum1="1",
            debtorPostCode1="10115",
            debtorCity1="Berlin",
        )
        req = _make_request(debtor=debtor)
        inv = map_sap_to_invoice(req, company)
        assert inv.customer_name == "Einzelname"

    def test_customer_address(self, company):
        req = _make_request()
        inv = map_sap_to_invoice(req, company)
        addr = inv.customer_address
        assert addr["address_line1"] == "Kundenstr. 42"
        assert addr["postcode"] == "80331"
        assert addr["city"] == "München"
        assert addr["country_code"] == "DE"

    def test_customer_vat_and_reference(self, company):
        req = _make_request()
        inv = map_sap_to_invoice(req, company)
        assert inv.customer_vat_id == "DE987654321"
        assert inv.buyer_reference == "KUNNR-001"

    def test_lines(self, company):
        req = _make_request()
        inv = map_sap_to_invoice(req, company)
        assert len(inv.lines) == 1
        line = inv.lines[0]
        assert line.description == "Beratung"
        assert line.quantity == Decimal("10")
        assert line.unit_code == "HUR"
        assert line.unit_price == Decimal("150.00")
        assert line.vat_rate == Decimal("19")
        assert line.vat_category_code == "S"
        assert line.sort_order == 10
        assert line.line_id == 10

    def test_totals_calculated(self, company):
        req = _make_request()
        inv = map_sap_to_invoice(req, company)
        assert inv.total_net == Decimal("1500.00")
        assert inv.vat_amount == Decimal("285.00")
        assert inv.total_gross == Decimal("1785.00")

    def test_multiple_lines(self, company):
        positions = [
            SapPosition(
                invoicePos="10",
                workPoolFreeText="Beratung",
                amount="10",
                unit="STD",
                unitPrice="100.00",
                taxPercent="19",
            ),
            SapPosition(
                invoicePos="20",
                workPoolFreeText="Material",
                amount="5",
                unit="ST",
                unitPrice="50.00",
                taxPercent="7",
            ),
        ]
        req = _make_request(position=positions)
        inv = map_sap_to_invoice(req, company)
        assert len(inv.lines) == 2
        assert inv.total_net == Decimal("1250.00")

    def test_period_from_positions(self, company):
        positions = [
            SapPosition(
                invoicePos="10",
                workPoolFreeText="Jan",
                amount="1",
                unitPrice="100",
                workPoolDateFrom="20260101",
                workPoolDateTo="20260131",
            ),
            SapPosition(
                invoicePos="20",
                workPoolFreeText="Feb",
                amount="1",
                unitPrice="100",
                workPoolDateFrom="20260201",
                workPoolDateTo="20260228",
            ),
        ]
        req = _make_request(position=positions)
        inv = map_sap_to_invoice(req, company)
        assert inv.period_start == date(2026, 1, 1)
        assert inv.period_end == date(2026, 2, 28)

    def test_no_period_when_missing(self, company):
        req = _make_request()
        inv = map_sap_to_invoice(req, company)
        assert inv.period_start is None
        assert inv.period_end is None

    def test_credit_note_mapping(self, company):
        req = _make_request(
            invoiceKind="M",
            refInvoiceNumber="RE-ORIG001",
        )
        inv = map_sap_to_invoice(req, company)
        assert inv.type_code == "381"
        assert inv.preceding_invoice_number == "RE-ORIG001"

    def test_invoice_kind_rechnung(self, company):
        req = _make_request(invoiceKind="I")
        inv = map_sap_to_invoice(req, company)
        assert inv.type_code == "380"

    def test_invoice_kind_storno_rechnung(self, company):
        req = _make_request(invoiceKind="C")
        inv = map_sap_to_invoice(req, company)
        assert inv.type_code == "384"

    def test_invoice_kind_storno_gutschrift(self, company):
        req = _make_request(invoiceKind="R")
        inv = map_sap_to_invoice(req, company)
        assert inv.type_code == "383"

    def test_payment_terms(self, company):
        req = _make_request(invoiceZtermText="30 Tage netto")
        inv = map_sap_to_invoice(req, company)
        assert inv.payment_terms == "30 Tage netto"

    def test_order_reference(self, company):
        req = _make_request(aufnr="4500012345")
        inv = map_sap_to_invoice(req, company)
        assert inv.order_reference == "4500012345"

    def test_note(self, company):
        req = _make_request(subjectFreetext="Wichtiger Hinweis")
        inv = map_sap_to_invoice(req, company)
        assert inv.note == "Wichtiger Hinweis"

    def test_contact_email(self, company):
        req = _make_request(contactMail="kunde@firma.de")
        inv = map_sap_to_invoice(req, company)
        assert inv.customer_contact_email == "kunde@firma.de"

    def test_iso_date_format(self, company):
        req = _make_request(invoice_date="2026-03-15")
        inv = map_sap_to_invoice(req, company)
        assert inv.issue_date == date(2026, 3, 15)

    def test_default_type_code(self, company):
        req = _make_request(invoiceKind="")
        inv = map_sap_to_invoice(req, company)
        assert inv.type_code == "380"

    def test_invalid_amount_fallback(self, company):
        pos = SapPosition(
            invoicePos="10",
            workPoolFreeText="Test",
            amount="abc",
            unit="STD",
            unitPrice="150.00",
            taxPercent="19",
        )
        req = _make_request(position=[pos])
        inv = map_sap_to_invoice(req, company)
        assert inv.lines[0].quantity == Decimal("1")

    def test_invalid_unit_price_fallback(self, company):
        pos = SapPosition(
            invoicePos="10",
            workPoolFreeText="Test",
            amount="10",
            unit="STD",
            unitPrice="xyz",
            taxPercent="19",
        )
        req = _make_request(position=[pos])
        inv = map_sap_to_invoice(req, company)
        assert inv.lines[0].unit_price == Decimal("0")

    def test_invalid_tax_percent_fallback(self, company):
        pos = SapPosition(
            invoicePos="10",
            workPoolFreeText="Test",
            amount="10",
            unit="STD",
            unitPrice="100",
            taxPercent="nope",
        )
        req = _make_request(position=[pos])
        inv = map_sap_to_invoice(req, company)
        assert inv.lines[0].vat_rate == Decimal("19")
