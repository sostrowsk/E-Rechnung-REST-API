# E-Rechnung REST API

REST API zur Erzeugung von ZUGFeRD-PDFs und XRechnung-XMLs aus SAP-Rechnungsdaten.

Die API fungiert als **stateless Rendering-Engine**: SAP sendet Rechnungsdaten per JSON,
die API liefert fertige PDF/XML-Dokumente zurueck. Die Verkaeuferdaten (Company) werden
mit jedem Request im JSON mitgeliefert.

[English version](README.md)

## Quickstart

```bash
# Abhaengigkeiten installieren
uv pip install -e ".[dev]"

# Server starten
uvicorn e_rechnung.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

## Dokumentation

| URL | Beschreibung |
|---|---|
| `http://localhost:8000/docs` | Swagger UI (interaktiv) |
| `http://localhost:8000/redoc` | ReDoc (uebersichtlich) |
| `http://localhost:8000/openapi.json` | OpenAPI 3.1 Schema |

## Endpoints

### `POST /api/v1/invoice/export?format={zugferd|xrechnung|both}`

Erzeugt aus SAP-Rechnungsdaten ein Exportdokument.

| Parameter | Wert | Response Content-Type |
|---|---|---|
| `zugferd` | PDF/A-3b mit eingebettetem Factur-X XML | `application/pdf` |
| `xrechnung` | UBL 2.1 XML | `application/xml` |
| `both` | ZIP-Archiv mit PDF + XML | `application/zip` |

**Beispiel:**

```bash
curl -X POST "http://localhost:8000/api/v1/invoice/export?format=zugferd" \
  -H "Content-Type: application/json" \
  -d @tests/data/dummy.json \
  -o rechnung.pdf
```

**Fehlerfall (422):**

```json
[
  {"field": "kunde.name", "message": "Kundenname erforderlich", "severity": "error"},
  {"field": "rechnung.issue_date", "message": "Rechnungsdatum erforderlich", "severity": "error"}
]
```

### `POST /api/v1/invoice/validate?format={zugferd|xrechnung}`

Validiert SAP-Rechnungsdaten ohne Export.

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

Health-Check: prueft Firmenkonfiguration.

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

## SAP JSON-Format

Die API akzeptiert das SAP-native JSON-Format. Felder koennen als String oder Zahl
uebergeben werden. Unbekannte Felder werden ignoriert.

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

Eine vollstaendige Beispieldatei mit allen SAP-Feldern liegt unter `tests/data/dummy.json`.
Das leere Template unter `tests/data/beispiel.json`.

## Feld-Mapping SAP &rarr; ZUGFeRD/XRechnung

### Kopfdaten (head)

| SAP-Feld | Intern | Beschreibung |
|---|---|---|
| `invoiceNumber` | `number` | Mit Company-Prefix (z.B. `RE-90001`) |
| `invoiceDate` | `issue_date` | YYYYMMDD oder YYYY-MM-DD |
| `dueDate` | `due_date` | Faelligkeitsdatum |
| `invoiceKind` | `type_code` | Via `SAP_KIND_MAP`, Default: `380` (Rechnung) |
| `invoiceCurrency` | `currency` | ISO 4217, Default: `EUR` |
| `invoiceZtermText` | `payment_terms` | Zahlungsbedingungen Freitext |
| `refInvoiceNumber` | `preceding_invoice_number` | Referenz bei Gutschriften |
| `aufnr` | `order_reference` | SAP-Auftragsnummer |
| `subjectFreetext` | `note` | Bemerkung |
| `contactMail` | `customer_contact_email` | Pflicht fuer XRechnung |

### Positionen (position)

| SAP-Feld | Intern | Beschreibung |
|---|---|---|
| `invoicePos` | `sort_order`, `line_id` | Positionsnummer |
| `workPoolFreeText` | `description` | Leistungsbeschreibung |
| `amount` | `quantity` | Menge |
| `unit` | `unit_code` | Via `SAP_UNIT_MAP` (s.u.) |
| `unitPrice` | `unit_price` | Einzelpreis netto |
| `taxPercent` | `vat_rate` | Steuersatz |
| `taxCode` | `vat_category_code` | Via `SAP_TAX_CODE_MAP` |
| `workPoolDateFrom/To` | `period_start/end` | Min/Max ueber alle Positionen |

### Debitor (debtor)

| SAP-Feld | Intern | Beschreibung |
|---|---|---|
| `debtorName1` + `debtorName2` | `customer_name` | Zusammengefuegt |
| `debtorStreet` + `debtorHouseNum1` | `customer_address.address_line1` | Zusammengefuegt |
| `debtorPostCode1` | `customer_address.postcode` | PLZ |
| `debtorCity1` | `customer_address.city` | Ort |
| `debtorCountry` | `customer_address.country_code` | Laendercode |
| `debtorStceg` | `customer_vat_id` | USt-IdNr. |
| `debtorKunnr` | `buyer_reference` | Kundennummer / Leitweg-ID |

## Mapping-Tabellen

Die Mapping-Dicts in `src/e_rechnung/api/mapper.py` sind erweiterbar:

### SAP_UNIT_MAP (Mengeneinheiten)

| SAP | UN/CEFACT | Bedeutung |
|---|---|---|
| `ST` | `C62` | Stueck |
| `STD` | `HUR` | Stunde |
| `H` | `HUR` | Stunde |
| `TAG` | `DAY` | Tag |
| `MON` | `MON` | Monat |
| `KG` | `KGM` | Kilogramm |
| `M` | `MTR` | Meter |
| `L` | `LTR` | Liter |
| `PAU` | `LS` | Pauschale |

Unbekannte Einheiten werden 1:1 durchgereicht.

### SAP_TAX_CODE_MAP (Steuerkennzeichen)

Aktuell leer, Fallback ueber `taxPercent`:
- `19%` oder `7%` &rarr; `S` (Normaler/ermaessigter Steuersatz)
- `0%` &rarr; `Z` (Steuerbefreit)

### SAP_KIND_MAP (Rechnungsart)

Aktuell leer, Default: `380` (Rechnung). Erweiterbar z.B.:
- `"G"` &rarr; `"381"` (Gutschrift)

## Konfiguration

### Voraussetzung

Die API erwartet **Company** (Verkaeuferdaten) als `company`-Feld im JSON-Payload jedes Requests.
Ohne gueltige Company liefert die API `503 Service Unavailable`.

## Tests

```bash
# Nur Mapper-Tests
uv run pytest tests/test_mapper.py -v

# API-Integrationstests
uv run pytest tests/test_api.py -v

# Alle Tests
uv run pytest

# Mit Coverage
uv run pytest --cov=e_rechnung --cov-report=term-missing
```
