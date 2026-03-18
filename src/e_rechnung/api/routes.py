from __future__ import annotations

import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from e_rechnung.api.mapper import map_sap_company, map_sap_to_invoice
from e_rechnung.api.schemas import (
    ExportFormat,
    SapInvoiceRequest,
    ValidationErrorDetail,
)
from e_rechnung.export_xrechnung import export_xrechnung
from e_rechnung.export_zugferd import export_zugferd
from e_rechnung.validators import (
    has_critical_errors,
    validate_for_xrechnung,
    validate_for_zugferd,
)

router = APIRouter(prefix="/api/v1", tags=["E-Rechnung"])


def _validate(invoice, company, fmt: ExportFormat) -> list[ValidationErrorDetail]:
    if fmt == ExportFormat.XRECHNUNG:
        errors = validate_for_xrechnung(invoice, company)
    elif fmt == ExportFormat.BOTH:
        errors = validate_for_xrechnung(invoice, company)
    else:
        errors = validate_for_zugferd(invoice, company)
    return [
        ValidationErrorDetail(field=e.field, message=e.message, severity=e.severity)
        for e in errors
    ]


@router.post(
    "/invoice/export",
    summary="Rechnung exportieren",
    description=(
        "Erzeugt aus SAP-Rechnungsdaten eine ZUGFeRD-PDF, XRechnung-XML oder beides als ZIP.\n\n"
        "Alle benoetigten Daten (inkl. Verkaeuferdaten/Company) werden im Request mitgesendet. "
        "Die API ist vollstaendig stateless.\n\n"
        "**Responses:**\n"
        "- `200` zugferd: `application/pdf` (PDF/A-3b mit eingebettetem Factur-X XML)\n"
        "- `200` xrechnung: `application/xml` (UBL 2.1 XML)\n"
        "- `200` both: `application/zip` (ZIP mit PDF + XML)\n"
        "- `422`: Validierungsfehler (JSON-Array mit Fehlerdetails)"
    ),
    responses={
        200: {"description": "Exportierte Rechnung (PDF, XML oder ZIP)"},
        422: {
            "description": "Validierungsfehler",
            "content": {"application/json": {"example": [
                {"field": "kunde.name", "message": "Kundenname erforderlich", "severity": "error"},
            ]}},
        },
    },
)
def export_invoice(
    request: SapInvoiceRequest,
    format: ExportFormat = Query(ExportFormat.ZUGFERD, description="Exportformat"),
):
    company = map_sap_company(request.company)
    invoice = map_sap_to_invoice(request, company)

    # Validate
    errors = _validate(invoice, company, format)
    critical = [e for e in errors if e.severity == "error"]
    if critical:
        raise HTTPException(status_code=422, detail=[e.model_dump() for e in critical])

    with tempfile.TemporaryDirectory() as tmpdir:
        if format == ExportFormat.ZUGFERD:
            path = str(Path(tmpdir) / "invoice.pdf")
            export_zugferd(invoice, company, path)
            data = Path(path).read_bytes()
            return Response(content=data, media_type="application/pdf")

        if format == ExportFormat.XRECHNUNG:
            path = str(Path(tmpdir) / "invoice.xml")
            export_xrechnung(invoice, company, path)
            data = Path(path).read_bytes()
            return Response(content=data, media_type="application/xml")

        # both
        pdf_path = str(Path(tmpdir) / "invoice.pdf")
        xml_path = str(Path(tmpdir) / "invoice.xml")
        export_zugferd(invoice, company, pdf_path)
        export_xrechnung(invoice, company, xml_path)

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(pdf_path, f"{invoice.number}.pdf")
            zf.write(xml_path, f"{invoice.number}.xml")
        return Response(content=buf.getvalue(), media_type="application/zip")


@router.post(
    "/invoice/validate",
    summary="Rechnung validieren",
    description=(
        "Prueft SAP-Rechnungsdaten gegen die ZUGFeRD- bzw. XRechnung-Validierungsregeln, "
        "ohne einen Export zu erzeugen.\n\n"
        "Gibt eine Liste aller Fehler und Warnungen zurueck."
    ),
    responses={
        200: {
            "description": "Validierungsergebnis",
            "content": {"application/json": {"example": {
                "valid": False,
                "errors": [
                    {"field": "kunde.name", "message": "Kundenname erforderlich", "severity": "error"},
                    {"field": "firma.contact_name", "message": "Ansprechpartner erforderlich", "severity": "warning"},
                ],
            }}},
        },
    },
)
def validate_invoice(
    request: SapInvoiceRequest,
    format: ExportFormat = Query(ExportFormat.ZUGFERD, description="Zielformat fuer Validierung"),
):
    company = map_sap_company(request.company)
    invoice = map_sap_to_invoice(request, company)
    errors = _validate(invoice, company, format)
    return {
        "valid": not any(e.severity == "error" for e in errors),
        "errors": [e.model_dump() for e in errors],
    }


@router.get(
    "/health",
    summary="Health-Check",
    description="Einfacher Health-Check der API.",
    responses={
        200: {
            "description": "Service-Status",
            "content": {"application/json": {"example": {"status": "ok"}}},
        },
    },
)
def health():
    return {"status": "ok"}
