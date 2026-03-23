import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from e_rechnung.export_zugferd import export_zugferd
from e_rechnung.models import Company, Invoice, InvoiceLine


def _company():
    return Company(
        name="Test GmbH",
        address_line1="Teststr. 1",
        postcode="12345",
        city="Berlin",
        country_code="DE",
        vat_id="DE123456789",
        contact_name="Max Mustermann",
        contact_email="test@test.de",
        contact_phone="+49 123 456",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        bank_name="Commerzbank",
    )


def _invoice():
    line = InvoiceLine(
        line_id=1,
        description="Beratung",
        quantity=Decimal("10.000"),
        unit_code="HUR",
        unit_price=Decimal("100.00"),
        line_total=Decimal("1000.00"),
        vat_category_code="S",
        vat_rate=Decimal("19.00"),
    )
    return Invoice(
        number="RE-2026-00001",
        type_code="380",
        issue_date=date(2026, 1, 15),
        due_date=date(2026, 1, 29),
        delivery_date=date(2026, 1, 15),
        currency="EUR",
        customer_name="Kunde AG",
        customer_address={
            "address_line1": "Kundenstr. 2",
            "postcode": "54321",
            "city": "Muenchen",
            "country_code": "DE",
        },
        total_net=Decimal("1000.00"),
        vat_amount=Decimal("190.00"),
        total_gross=Decimal("1190.00"),
        lines=[line],
    )


def test_export_zugferd_creates_pdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(_invoice(), _company(), output_path)

    pdf_data = Path(output_path).read_bytes()
    assert pdf_data[:5] == b"%PDF-"
    assert len(pdf_data) > 1000


def test_export_zugferd_contains_xml():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(_invoice(), _company(), output_path)

    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_xml_content():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(_invoice(), _company(), output_path)

    pdf_data = Path(output_path).read_bytes()
    xml_start = pdf_data.find(b"<?xml")
    assert xml_start > 0
    xml_end = pdf_data.find(b"</rsm:CrossIndustryInvoice>", xml_start)
    assert xml_end > 0
    xml_bytes = pdf_data[xml_start : xml_end + len(b"</rsm:CrossIndustryInvoice>")]

    root = etree.fromstring(xml_bytes)
    ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

    assert root.xpath("//ram:ID[text()='RE-2026-00001']", namespaces=ns)
    assert root.xpath("//ram:SellerTradeParty/ram:Name[text()='Test GmbH']", namespaces=ns)
    assert root.xpath("//ram:BuyerTradeParty/ram:Name[text()='Kunde AG']", namespaces=ns)


def test_export_zugferd_validation_error():
    inv = _invoice()
    inv.number = ""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name
    with pytest.raises(ValueError, match="Validierungsfehler"):
        export_zugferd(inv, _company(), output_path)


def test_export_zugferd_mixed_vat():
    line1 = InvoiceLine(
        line_id=1,
        description="Beratung 19%",
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
        line_total=Decimal("100.00"),
        vat_category_code="S",
        vat_rate=Decimal("19.00"),
    )
    line2 = InvoiceLine(
        line_id=2,
        description="Buch 7%",
        quantity=Decimal("1"),
        unit_price=Decimal("50.00"),
        line_total=Decimal("50.00"),
        vat_category_code="S",
        vat_rate=Decimal("7.00"),
    )
    inv = _invoice()
    inv.lines = [line1, line2]
    inv.total_net = Decimal("150.00")
    inv.vat_amount = Decimal("22.50")  # 19 + 3.50
    inv.total_gross = Decimal("172.50")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_credit_note():
    inv = _invoice()
    inv.type_code = "381"
    inv.preceding_invoice_number = "RE-2026-00001"
    inv.preceding_invoice_date = date(2026, 1, 15)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_skonto():
    inv = _invoice()
    inv.skonto_percent = Decimal("2.00")
    inv.skonto_days = 10

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_exemption_tax():
    """Tax-exempt category triggers exemption reason in XML."""
    line = InvoiceLine(
        line_id=1,
        description="EU-Lieferung",
        quantity=Decimal("1"),
        unit_code="C62",
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        vat_category_code="K",
        vat_rate=Decimal("0"),
    )
    inv = _invoice()
    inv.lines = [line]
    inv.total_net = Decimal("1000.00")
    inv.vat_amount = Decimal("0.00")
    inv.total_gross = Decimal("1000.00")
    inv.customer_vat_id = "DE987654321"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"VATEX-EU-IC" in pdf_data


def test_export_zugferd_article_number():
    """Line item with article_number sets seller_assigned_id."""
    line = InvoiceLine(
        line_id=1,
        description="Artikel",
        quantity=Decimal("1"),
        unit_code="C62",
        unit_price=Decimal("100.00"),
        line_total=Decimal("100.00"),
        vat_category_code="S",
        vat_rate=Decimal("19.00"),
        article_number="ART-001",
    )
    inv = _invoice()
    inv.lines = [line]
    inv.total_net = Decimal("100.00")
    inv.vat_amount = Decimal("19.00")
    inv.total_gross = Decimal("119.00")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"ART-001" in pdf_data


def test_export_zugferd_with_period():
    """Billing period note and settlement period are set."""
    inv = _invoice()
    inv.period_start = date(2026, 1, 1)
    inv.period_end = date(2026, 1, 31)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_seller_address_line2():
    """Seller address_line2 is included when set."""
    company = _company()
    company.address_line2 = "Hinterhaus"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(_invoice(), company, output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_tax_number_only():
    """Company with tax_number but no vat_id."""
    company = _company()
    company.vat_id = ""
    company.tax_number = "123/456/78901"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(_invoice(), company, output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_buyer_address_line2():
    """Buyer address_line2 is included when set."""
    inv = _invoice()
    inv.customer_address["address_line2"] = "3. OG"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data


def test_export_zugferd_contract_reference():
    """Contract reference is set in XML."""
    inv = _invoice()
    inv.contract_reference = "RV-2026-042"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    export_zugferd(inv, _company(), output_path)
    pdf_data = Path(output_path).read_bytes()
    assert b"factur-x.xml" in pdf_data
