import pytest

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
        contact_name="Max Mustermann",
        contact_email="max@test.de",
        contact_phone="+49 30 12345",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        bank_name="Commerzbank",
        invoice_prefix="RE-",
    )
