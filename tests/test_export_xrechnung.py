import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from e_rechnung.export_xrechnung import export_xrechnung
from e_rechnung.models import Company, Invoice, InvoiceLine

UBL_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS = {"inv": UBL_NS, "cbc": CBC_NS, "cac": CAC_NS}


def _company():
    return Company(
        name="Test GmbH", address_line1="Teststr. 1",
        postcode="12345", city="Berlin", country_code="DE",
        vat_id="DE123456789", contact_name="Max Mustermann",
        contact_email="test@test.de", contact_phone="+49 123 456",
        iban="DE89370400440532013000", bic="COBADEFFXXX",
    )


def _invoice():
    line = InvoiceLine(
        line_id=1, description="IT-Beratung", quantity=Decimal("8.000"),
        unit_code="HUR", unit_price=Decimal("150.00"),
        line_total=Decimal("1200.00"), vat_category_code="S",
        vat_rate=Decimal("19.00"),
    )
    return Invoice(
        number="RE-2026-00042", type_code="380",
        issue_date=date(2026, 3, 1), due_date=date(2026, 3, 15),
        delivery_date=date(2026, 3, 1), currency="EUR",
        customer_name="Behoerde XY",
        customer_address={
            "address_line1": "Amtsstr. 5",
            "postcode": "10115",
            "city": "Berlin",
            "country_code": "DE",
        },
        buyer_reference="04011000-12345-67",
        customer_contact_email="rechnung@behoerde.de",
        total_net=Decimal("1200.00"), vat_amount=Decimal("228.00"),
        total_gross=Decimal("1428.00"), lines=[line],
    )


def test_export_xrechnung_creates_xml():
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        output_path = f.name

    export_xrechnung(_invoice(), _company(), output_path)

    xml_data = Path(output_path).read_text(encoding="utf-8")
    assert '<?xml version="1.0"' in xml_data
    assert "Invoice" in xml_data


def test_export_xrechnung_structure():
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        output_path = f.name

    export_xrechnung(_invoice(), _company(), output_path)

    tree = etree.parse(output_path)
    root = tree.getroot()

    assert root.tag == f"{{{UBL_NS}}}Invoice"

    cust_id = root.find(f"{{{CBC_NS}}}CustomizationID")
    assert cust_id is not None
    assert "xrechnung" in cust_id.text.lower()

    inv_id = root.find(f"{{{CBC_NS}}}ID")
    assert inv_id.text == "RE-2026-00042"

    buyer_ref = root.find(f"{{{CBC_NS}}}BuyerReference")
    assert buyer_ref is not None
    assert buyer_ref.text == "04011000-12345-67"


def test_export_xrechnung_parties():
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        output_path = f.name

    export_xrechnung(_invoice(), _company(), output_path)
    tree = etree.parse(output_path)

    seller = tree.xpath("//cac:AccountingSupplierParty//cbc:Name", namespaces=NS)
    assert any("Test GmbH" in e.text for e in seller)

    buyer = tree.xpath("//cac:AccountingCustomerParty//cbc:Name", namespaces=NS)
    assert any("Behoerde XY" in e.text for e in buyer)


def test_export_xrechnung_line_items():
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        output_path = f.name

    export_xrechnung(_invoice(), _company(), output_path)
    tree = etree.parse(output_path)

    lines = tree.xpath("//cac:InvoiceLine", namespaces=NS)
    assert len(lines) == 1

    qty = lines[0].find(f"{{{CBC_NS}}}InvoicedQuantity")
    assert qty is not None
    assert qty.get("unitCode") == "HUR"


def test_export_xrechnung_validation_error():
    inv = _invoice()
    inv.buyer_reference = ""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        output_path = f.name
    with pytest.raises(ValueError, match="Validierungsfehler"):
        export_xrechnung(inv, _company(), output_path)


def test_export_xrechnung_credit_note_reference():
    inv = _invoice()
    inv.type_code = "381"
    inv.preceding_invoice_number = "RE-2026-00001"
    inv.preceding_invoice_date = date(2026, 1, 15)

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        output_path = f.name

    export_xrechnung(inv, _company(), output_path)
    tree = etree.parse(output_path)

    ref = tree.xpath("//cac:BillingReference//cbc:ID", namespaces=NS)
    assert len(ref) == 1
    assert ref[0].text == "RE-2026-00001"
