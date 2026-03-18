# E-Rechnung REST API

REST API for generating ZUGFeRD PDFs and XRechnung XMLs from SAP invoice data.

The API acts as a **stateless rendering engine**: SAP sends invoice data as JSON,
the API returns ready-made PDF/XML documents. Seller data (Company) is passed
inline with each request.

[Deutsche Version](README.de.md)

## Quickstart

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Start server
uvicorn e_rechnung.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

## Documentation

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | Swagger UI (interactive) |
| `http://localhost:8000/redoc` | ReDoc (overview) |
| `http://localhost:8000/openapi.json` | OpenAPI 3.1 Schema |

## Endpoints

### `POST /api/v1/invoice/export?format={zugferd|xrechnung|both}`

Generates an export document from SAP invoice data.

| Parameter | Output | Response Content-Type |
|---|---|---|
| `zugferd` | PDF/A-3b with embedded Factur-X XML | `application/pdf` |
| `xrechnung` | UBL 2.1 XML | `application/xml` |
| `both` | ZIP archive with PDF + XML | `application/zip` |

**Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/invoice/export?format=zugferd" \
  -H "Content-Type: application/json" \
  -d @tests/data/dummy.json \
  -o rechnung.pdf
```

**Error response (422):**

```json
[
  {"field": "kunde.name", "message": "Kundenname erforderlich", "severity": "error"},
  {"field": "rechnung.issue_date", "message": "Rechnungsdatum erforderlich", "severity": "error"}
]
```

### `POST /api/v1/invoice/validate?format={zugferd|xrechnung}`

Validates SAP invoice data without generating output.

```bash
curl -X POST "http://localhost:8000/api/v1/invoice/validate?format=zugferd" \
  -H "Content-Type: application/json" \
  -d @tests/data/dummy.json
```

**Response:**

```json
{
  "valid": true,
  "errors": []
}
```

### `GET /api/v1/health`

Health check: verifies company configuration.

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "company_configured": true,
  "company_name": "Mustermann IT-Consulting"
}
```

## SAP JSON Format

The API accepts SAP-native JSON. Fields can be passed as strings or numbers.
Unknown fields are ignored.

```json
{
  "head": {
    "invoiceNumber": 90001,
    "invoiceDate": "20260315",
    "dueDate": "20260414",
    "invoiceCurrency": "EUR",
    "invoiceZtermText": "Zahlbar innerhalb von 30 Tagen ohne Abzug",
    "aufnr": "4500067890",
    "contactMail": "max.mustermann@muster-gmbh.de",
    "subjectFreetext": "Leistungen gemaess Rahmenvertrag RV-2026-042"
  },
  "position": [
    {
      "invoicePos": 10,
      "workPoolFreeText": "IT-Beratung Senior Consultant",
      "amount": 80,
      "unit": "STD",
      "unitPrice": 150,
      "taxPercent": 19,
      "workPoolDateFrom": "20260301",
      "workPoolDateTo": "20260315"
    }
  ],
  "debtor": {
    "debtorKunnr": "10042",
    "debtorName1": "Muster GmbH",
    "debtorStreet": "Musterstrasse",
    "debtorHouseNum1": "42",
    "debtorPostCode1": "80331",
    "debtorCity1": "Muenchen",
    "debtorCountry": "DE",
    "debtorStceg": "DE123456789"
  }
}
```

A complete example with all SAP fields is at `tests/data/dummy.json`.
An empty template is at `tests/data/beispiel.json`.

## Field Mapping SAP &rarr; ZUGFeRD/XRechnung

### Header (head)

| SAP Field | Internal | Description |
|---|---|---|
| `invoiceNumber` | `number` | Prefixed with company prefix (e.g. `RE-90001`) |
| `invoiceDate` | `issue_date` | YYYYMMDD or YYYY-MM-DD |
| `dueDate` | `due_date` | Payment due date |
| `invoiceKind` | `type_code` | Via `SAP_KIND_MAP`, default: `380` (invoice) |
| `invoiceCurrency` | `currency` | ISO 4217, default: `EUR` |
| `invoiceZtermText` | `payment_terms` | Payment terms free text |
| `refInvoiceNumber` | `preceding_invoice_number` | Reference for credit notes |
| `aufnr` | `order_reference` | SAP order number |
| `subjectFreetext` | `note` | Remark |
| `contactMail` | `customer_contact_email` | Required for XRechnung |

### Line Items (position)

| SAP Field | Internal | Description |
|---|---|---|
| `invoicePos` | `sort_order`, `line_id` | Position number |
| `workPoolFreeText` | `description` | Service description |
| `amount` | `quantity` | Quantity |
| `unit` | `unit_code` | Via `SAP_UNIT_MAP` (see below) |
| `unitPrice` | `unit_price` | Net unit price |
| `taxPercent` | `vat_rate` | Tax rate |
| `taxCode` | `vat_category_code` | Via `SAP_TAX_CODE_MAP` |
| `workPoolDateFrom/To` | `period_start/end` | Min/max across all positions |

### Debtor (debtor)

| SAP Field | Internal | Description |
|---|---|---|
| `debtorName1` + `debtorName2` | `customer_name` | Concatenated |
| `debtorStreet` + `debtorHouseNum1` | `customer_address.address_line1` | Concatenated |
| `debtorPostCode1` | `customer_address.postcode` | Postal code |
| `debtorCity1` | `customer_address.city` | City |
| `debtorCountry` | `customer_address.country_code` | Country code |
| `debtorStceg` | `customer_vat_id` | VAT ID |
| `debtorKunnr` | `buyer_reference` | Customer number / Leitweg-ID |

## Mapping Tables

The mapping dicts in `src/e_rechnung/api/mapper.py` are extensible:

### SAP_UNIT_MAP (Units of Measure)

| SAP | UN/CEFACT | Meaning |
|---|---|---|
| `ST` | `C62` | Piece |
| `STD` | `HUR` | Hour |
| `H` | `HUR` | Hour |
| `TAG` | `DAY` | Day |
| `MON` | `MON` | Month |
| `KG` | `KGM` | Kilogram |
| `M` | `MTR` | Meter |
| `L` | `LTR` | Liter |
| `PAU` | `LS` | Lump sum |

Unknown units are passed through as-is.

### SAP_TAX_CODE_MAP (Tax Codes)

Currently empty, falls back to `taxPercent`:
- `19%` or `7%` &rarr; `S` (Standard/reduced rate)
- `0%` &rarr; `Z` (Zero-rated)

### SAP_KIND_MAP (Invoice Type)

Currently empty, default: `380` (invoice). Extensible, e.g.:
- `"G"` &rarr; `"381"` (Credit note)

## Configuration

### Prerequisites

The API requires **Company** (seller data) to be passed in each request via the `company` field in the JSON payload.
Without a valid company, the API returns `503 Service Unavailable`.

## Tests

```bash
# Mapper tests only
uv run pytest tests/test_mapper.py -v

# API integration tests
uv run pytest tests/test_api.py -v

# All tests
uv run pytest

# With coverage
uv run pytest --cov=e_rechnung --cov-report=term-missing
```
