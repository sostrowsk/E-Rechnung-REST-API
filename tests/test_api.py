from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from e_rechnung.api.app import create_app

COMPANY_DATA = {
    "name": "Test GmbH",
    "addressLine1": "Teststr. 1",
    "postcode": "12345",
    "city": "Berlin",
    "countryCode": "DE",
    "vatId": "DE123456789",
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX",
    "bankName": "Commerzbank",
    "contactName": "Max Mustermann",
    "contactEmail": "max@test.de",
    "contactPhone": "+49 30 12345",
    "invoicePrefix": "RE-",
}

SAP_PAYLOAD = {
    "head": {
        "invoiceNumber": "SAP001",
        "invoiceDate": "20260315",
        "dueDate": "20260415",
        "invoiceCurrency": "EUR",
        "invoiceZtermText": "30 Tage netto",
        "contactMail": "kunde@firma.de",
        "aufnr": "4500012345",
    },
    "position": [
        {
            "invoicePos": "10",
            "workPoolFreeText": "Beratung März 2026",
            "amount": "10",
            "unit": "STD",
            "unitPrice": "150.00",
            "taxPercent": "19",
        },
    ],
    "debtor": {
        "debtorKunnr": "KUNNR-001",
        "debtorName1": "Kunde AG",
        "debtorStreet": "Kundenstr.",
        "debtorHouseNum1": "42",
        "debtorPostCode1": "80331",
        "debtorCity1": "München",
        "debtorCountry": "DE",
        "debtorStceg": "DE987654321",
    },
    "company": COMPANY_DATA,
}


@pytest.fixture
def client():
    return TestClient(create_app())


class TestExportEndpoint:
    def test_zugferd_export(self, client):
        resp = client.post("/api/v1/invoice/export?format=zugferd", json=SAP_PAYLOAD)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"

    def test_xrechnung_export(self, client):
        resp = client.post("/api/v1/invoice/export?format=xrechnung", json=SAP_PAYLOAD)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert b"Invoice" in resp.content

    def test_both_export(self, client):
        resp = client.post("/api/v1/invoice/export?format=both", json=SAP_PAYLOAD)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        zf = zipfile.ZipFile(BytesIO(resp.content))
        names = zf.namelist()
        assert any(n.endswith(".pdf") for n in names)
        assert any(n.endswith(".xml") for n in names)

    def test_validation_error_422(self, client):
        payload = {
            "head": {
                "invoiceNumber": "",
                "invoiceDate": "",
            },
            "position": [],
            "debtor": {},
            "company": COMPANY_DATA,
        }
        resp = client.post("/api/v1/invoice/export?format=zugferd", json=payload)
        assert resp.status_code == 422


class TestValidateEndpoint:
    def test_valid_invoice(self, client):
        resp = client.post("/api/v1/invoice/validate?format=zugferd", json=SAP_PAYLOAD)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True

    def test_invalid_invoice(self, client):
        payload = {
            "head": {
                "invoiceNumber": "",
                "invoiceDate": "",
            },
            "position": [],
            "debtor": {},
            "company": COMPANY_DATA,
        }
        resp = client.post("/api/v1/invoice/validate?format=zugferd", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert len(body["errors"]) > 0


class TestSapJsonFormat:
    def test_numeric_fields_accepted(self, client):
        """SAP sends numbers for invoiceNumber, amount, unitPrice, taxPercent etc."""
        payload = {
            "head": {
                "invoiceNumber": 12345,
                "invoiceDate": "20260315",
                "dueDate": "20260415",
                "refInvoiceNumber": 0,
                "invoiceCurrency": "EUR",
                "contactMail": "kunde@firma.de",
            },
            "position": [
                {
                    "invoicePos": 10,
                    "workPoolFreeText": "Beratung",
                    "amount": 10,
                    "unit": "STD",
                    "unitPrice": 150,
                    "taxPercent": 19,
                },
            ],
            "debtor": {
                "debtorKunnr": "KUNNR-001",
                "debtorName1": "Kunde AG",
                "debtorStreet": "Kundenstr.",
                "debtorHouseNum1": "42",
                "debtorPostCode1": "80331",
                "debtorCity1": "München",
                "debtorCountry": "DE",
                "debtorStceg": "DE987654321",
            },
            "company": COMPANY_DATA,
        }
        resp = client.post("/api/v1/invoice/validate?format=zugferd", json=payload)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_extra_fields_ignored(self, client):
        """SAP sends extra fields like siId, debtorTitle etc. — must be ignored."""
        payload = {
            "head": {
                "siId": 0,
                "invoiceNumber": "SAP001",
                "invoiceDate": "20260315",
                "invoiceStatus": "NEW",
                "finishDate": "",
                "finishTime": "",
                "changeEssential": "",
                "changeMode": "",
                "kunnr": "",
                "contactNr": "",
                "contactName": "",
                "contactPhone": "",
                "contactMail": "kunde@firma.de",
                "invoiceLanguage": "",
                "invoicePerson": "",
                "invoiceDepartment": "",
                "bodyFreetext": "",
                "processComment": "",
            },
            "position": [
                {
                    "siId": 0,
                    "invoicePos": 10,
                    "workPoolFreeText": "Beratung",
                    "workPoolId": 0,
                    "amount": 10,
                    "unit": "STD",
                    "unitDescription": "Stunden",
                    "unitPrice": 150,
                    "taxPercent": 19,
                },
            ],
            "debtor": {
                "siId": 0,
                "debtorTitle": "Herr",
                "debtorKunnr": "KUNNR-001",
                "debtorName1": "Kunde AG",
                "debtorSort1": "",
                "debtorSort2": "",
                "debtorStreet": "Kundenstr.",
                "debtorHouseNum1": "42",
                "debtorPostCode1": "80331",
                "debtorCity1": "München",
                "debtorCountry": "DE",
                "debtorRegion": "",
                "debtorRemark": "",
                "debtorLzbkz": "",
                "debtorAltkn": "",
                "debtorStceg": "DE987654321",
                "debtorKtokd": "",
            },
            "company": COMPANY_DATA,
        }
        resp = client.post("/api/v1/invoice/validate?format=zugferd", json=payload)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_beispiel_json_parseable(self, client):
        """The empty SAP template beispiel.json should parse without error."""
        beispiel = Path(__file__).parent / "data" / "beispiel.json"
        payload = json.loads(beispiel.read_text())
        resp = client.post("/api/v1/invoice/validate?format=zugferd", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "valid" in body
        assert "errors" in body


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
