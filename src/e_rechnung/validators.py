from __future__ import annotations

from decimal import Decimal

from e_rechnung.models import Company, Invoice, ValidationError


def validate_for_zugferd(invoice: Invoice, company: Company) -> list[ValidationError]:
    errors: list[ValidationError] = []

    # Company checks
    if not company.name:
        errors.append(ValidationError("firma.name", "Firmenname erforderlich", "error"))
    if not company.address_line1:
        errors.append(ValidationError("firma.address_line1", "Firmenadresse erforderlich", "error"))
    if not company.postcode:
        errors.append(ValidationError("firma.postcode", "PLZ erforderlich", "error"))
    if not company.city:
        errors.append(ValidationError("firma.city", "Ort erforderlich", "error"))
    if not company.vat_id and not company.tax_number:
        errors.append(ValidationError("firma.vat_id", "USt-IdNr. oder Steuernummer erforderlich", "error"))
    if not company.contact_name:
        errors.append(ValidationError("firma.contact_name", "Ansprechpartner erforderlich", "warning"))
    if not company.contact_email:
        errors.append(ValidationError("firma.contact_email", "E-Mail erforderlich", "warning"))
    if not company.contact_phone:
        errors.append(ValidationError("firma.contact_phone", "Telefon erforderlich", "warning"))
    if not company.iban:
        errors.append(ValidationError("firma.iban", "IBAN erforderlich", "error"))

    # Buyer checks (from snapshot)
    if not invoice.customer_name:
        errors.append(ValidationError("kunde.name", "Kundenname erforderlich", "error"))
    else:
        addr = invoice.customer_address or {}
        if not addr.get("address_line1"):
            errors.append(ValidationError("kunde.address_line1", "Kundenadresse erforderlich", "error"))
        if not addr.get("postcode"):
            errors.append(ValidationError("kunde.postcode", "Kunden-PLZ erforderlich", "error"))
        if not addr.get("city"):
            errors.append(ValidationError("kunde.city", "Kundenort erforderlich", "error"))

    # Invoice checks
    if not invoice.number:
        errors.append(ValidationError("rechnung.number", "Rechnungsnummer erforderlich", "error"))
    if not invoice.issue_date:
        errors.append(ValidationError("rechnung.issue_date", "Rechnungsdatum erforderlich", "error"))
    if not invoice.lines:
        errors.append(ValidationError("rechnung.positionen", "Mindestens eine Position erforderlich", "error"))
    if invoice.total_net <= Decimal("0"):
        errors.append(ValidationError("rechnung.total_net", "Nettobetrag muss positiv sein", "error"))

    return errors


def validate_for_xrechnung(invoice: Invoice, company: Company) -> list[ValidationError]:
    errors = validate_for_zugferd(invoice, company)

    if not invoice.buyer_reference:
        errors.append(
            ValidationError(
                "kunde.buyer_reference", "Leitweg-ID (Buyer Reference) erforderlich fuer XRechnung", "error"
            )
        )
    if not invoice.customer_contact_email:
        errors.append(ValidationError("kunde.contact_email", "Kaeufer-E-Mail erforderlich fuer XRechnung", "error"))

    return errors


def has_critical_errors(errors: list[ValidationError]) -> bool:
    return any(e.severity == "error" for e in errors)
