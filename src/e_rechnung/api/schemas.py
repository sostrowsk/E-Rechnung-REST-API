from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field


class ExportFormat(str, enum.Enum):
    ZUGFERD = "zugferd"
    XRECHNUNG = "xrechnung"
    BOTH = "both"


class SapPosition(BaseModel):
    """Rechnungsposition aus SAP."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore", coerce_numbers_to_str=True)

    invoice_pos: str = Field("0", alias="invoicePos", description="Positionsnummer (z.B. 10, 20, 30)")
    work_pool_free_text: str = Field("", alias="workPoolFreeText", description="Positionstext / Leistungsbeschreibung")
    amount: str = Field("1", alias="amount", description="Menge")
    unit: str = Field("ST", alias="unit", description="Mengeneinheit SAP (ST, STD, TAG, PAU, ...)")
    unit_description: str = Field(
        "", alias="unitDescription", description="Beschreibung der Mengeneinheit (z.B. 'Stunden', 'Stueck')"
    )
    unit_price: str = Field("0", alias="unitPrice", description="Einzelpreis netto")
    tax_percent: str = Field("19", alias="taxPercent", description="Steuersatz in Prozent")
    tax_code: str = Field("", alias="taxCode", description="SAP-Steuerkennzeichen (optional)")
    mwart: str = Field("", alias="mwart", description="Steuerart: A=Ausgangssteuer, V=Vorsteuer")
    work_pool_date_from: str = Field("", alias="workPoolDateFrom", description="Leistungszeitraum von (YYYYMMDD)")
    work_pool_date_to: str = Field("", alias="workPoolDateTo", description="Leistungszeitraum bis (YYYYMMDD)")
    revenue_account: str = Field("", alias="revenueAccount", description="Erloeskonto (nicht gemappt)")
    kostl: str = Field("", alias="kostl", description="Kostenstelle (nicht gemappt)")


class SapDebtor(BaseModel):
    """Rechnungsempfaenger (Debitor) aus SAP."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore", coerce_numbers_to_str=True)

    debtor_kunnr: str = Field("", alias="debtorKunnr", description="SAP-Kundennummer / Buyer Reference")
    debtor_name1: str = Field("", alias="debtorName1", description="Name Zeile 1")
    debtor_name2: str = Field("", alias="debtorName2", description="Name Zeile 2 (optional)")
    debtor_street: str = Field("", alias="debtorStreet", description="Strasse")
    debtor_house_num1: str = Field("", alias="debtorHouseNum1", description="Hausnummer")
    debtor_post_code1: str = Field("", alias="debtorPostCode1", description="Postleitzahl")
    debtor_city1: str = Field("", alias="debtorCity1", description="Ort")
    debtor_country: str = Field("DE", alias="debtorCountry", description="Laendercode ISO 3166-1 alpha-2")
    debtor_stceg: str = Field("", alias="debtorStceg", description="USt-IdNr. des Debitors")


class SapCompany(BaseModel):
    """Verkaeuferdaten (Company) aus SAP."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(description="Firmenname")
    address_line1: str = Field("", alias="addressLine1", description="Adresszeile 1")
    address_line2: str = Field("", alias="addressLine2", description="Adresszeile 2 (optional)")
    postcode: str = Field("", description="Postleitzahl")
    city: str = Field("", description="Ort")
    country_code: str = Field("DE", alias="countryCode", description="Laendercode ISO 3166-1 alpha-2")
    vat_id: str = Field("", alias="vatId", description="USt-IdNr.")
    tax_number: str = Field("", alias="taxNumber", description="Steuernummer (falls keine USt-IdNr.)")
    contact_name: str = Field("", alias="contactName", description="Ansprechpartner Name")
    contact_phone: str = Field("", alias="contactPhone", description="Ansprechpartner Telefon")
    contact_email: str = Field("", alias="contactEmail", description="Ansprechpartner E-Mail")
    iban: str = Field("", description="IBAN")
    bic: str = Field("", description="BIC")
    bank_name: str = Field("", alias="bankName", description="Bankname")
    invoice_prefix: str = Field("RE-", alias="invoicePrefix", description="Rechnungsnummer-Praefix")


class SapHead(BaseModel):
    """Rechnungskopfdaten aus SAP."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore", coerce_numbers_to_str=True)

    invoice_number: str = Field(alias="invoiceNumber", description="SAP-Rechnungsnummer")
    invoice_date: str = Field(alias="invoiceDate", description="Rechnungsdatum (YYYYMMDD oder YYYY-MM-DD)")
    due_date: str = Field("", alias="dueDate", description="Faelligkeitsdatum (YYYYMMDD oder YYYY-MM-DD)")
    invoice_kind: str = Field(
        "",
        alias="invoiceKind",
        description="Rechnungsart: I=Rechnung, M=Gutschrift, C=Storno Rechnung, R=Storno Gutschrift, O=Angebot",
    )
    invoice_kind_description: str = Field(
        "", alias="invoiceKindDescription", description="Beschreibung der Rechnungsart (z.B. 'Rechnung', 'Gutschrift')"
    )
    invoice_currency: str = Field("EUR", alias="invoiceCurrency", description="Waehrungscode ISO 4217")
    invoice_zterm_text: str = Field("", alias="invoiceZtermText", description="Zahlungsbedingungen Freitext")
    ref_invoice_number: str = Field(
        "", alias="refInvoiceNumber", description="Referenz auf Ursprungsrechnung (bei Gutschriften)"
    )
    aufnr: str = Field("", alias="aufnr", description="SAP-Auftragsnummer / Order Reference")
    subject_freetext: str = Field("", alias="subjectFreetext", description="Betreff / Bemerkung")
    contact_mail: str = Field("", alias="contactMail", description="E-Mail Ansprechpartner Kaeufer")
    bukrs: str = Field("", alias="bukrs", description="Buchungskreis (nicht gemappt)")
    lzbkz: str = Field("", alias="lzbkz", description="Zahlsperre (nicht gemappt)")
    create_name: str = Field("", alias="createName", description="Ersteller (nicht gemappt)")
    create_date: str = Field("", alias="createDate", description="Erstelldatum (nicht gemappt)")
    create_time: str = Field("", alias="createTime", description="Erstellzeit (nicht gemappt)")


class SapInvoiceRequest(BaseModel):
    """Kompletter SAP-Rechnungsdatensatz mit Kopf, Positionen, Debitor und Firma."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    head: SapHead
    position: list[SapPosition] = Field(alias="position", description="Rechnungspositionen")
    debtor: SapDebtor
    company: SapCompany


class ValidationErrorDetail(BaseModel):
    """Einzelner Validierungsfehler oder -warnung."""

    field: str = Field(description="Betroffenes Feld (z.B. 'kunde.name', 'rechnung.issue_date')")
    message: str = Field(description="Fehlerbeschreibung")
    severity: str = Field(description="'error' (blockiert Export) oder 'warning' (Hinweis)")
