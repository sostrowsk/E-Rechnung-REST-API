from fastapi import FastAPI

from e_rechnung.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-Rechnung API",
        version="0.1.0",
        description=(
            "REST API zur Erzeugung von ZUGFeRD-PDFs und XRechnung-XMLs aus SAP-Rechnungsdaten.\n\n"
            "Die API fungiert als **stateless Rendering-Engine**: SAP sendet Rechnungsdaten "
            "inkl. Verkaeuferdaten (Company) per JSON, die API liefert fertige PDF/XML-Dokumente zurueck.\n\n"
            "**Swagger UI:** `/docs`  \n"
            "**ReDoc:** `/redoc`  \n"
            "**OpenAPI JSON:** `/openapi.json`"
        ),
    )
    app.include_router(router)
    return app
