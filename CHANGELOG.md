# Changelog

## [0.2.0] - 2026-03-23

### Neue Felder (IKB-Schnittstellenabstimmung)

- `SapHead.invoiceKindDescription` — Beschreibung der Rechnungsart (z.B. "Rechnung", "Gutschrift")
- `SapPosition.unitDescription` — Beschreibung der Mengeneinheit (z.B. "Stunden", "Stueck")
- `SapPosition.mwart` — Steuerart: A = Ausgangssteuer, V = Vorsteuer

### SAP invoiceKind-Mapping

`SAP_KIND_MAP` mit den bestaetigten IKB-Werten befuellt:

| invoiceKind | type_code | Bedeutung              |
|-------------|-----------|------------------------|
| I           | 380       | Rechnung               |
| M           | 381       | Gutschrift             |
| C           | 384       | Storno zur Rechnung    |
| R           | 383       | Storno zur Gutschrift  |
| (leer)      | 380       | Default                |

"O" (Angebot) wird nicht gemappt — Angebote sind kein E-Rechnungs-Dokumenttyp.

### ZUGFeRD Header

`doc.header.name` unterscheidet jetzt alle vier Dokumenttypen:
RECHNUNG, GUTSCHRIFT, STORNORECHNUNG, STORNOGUTSCHRIFT.

## [0.1.0] - 2026-03-21

Initiale Version:

- REST-API mit FastAPI (stateless, alle Daten im Request)
- ZUGFeRD-Export (PDF/A-3b mit Factur-X XML, EXTENDED-Profil)
- XRechnung-Export (UBL 2.1 XML)
- Kombinierter Export als ZIP
- Validierungs-Endpoint
- SAP-Feldnamen als Eingabe mit Mapping auf UN/CEFACT-Codes
- Gemischte Steuersaetze, Skonto, Leistungszeitraum
- 100% Test-Coverage (Production Code)
