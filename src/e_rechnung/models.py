from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from e_rechnung.utils import round_decimal


@dataclass
class Company:
    name: str = ""
    address_line1: str = ""
    address_line2: str = ""
    postcode: str = ""
    city: str = ""
    country_code: str = "DE"
    vat_id: str = ""
    tax_number: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    iban: str = ""
    bic: str = ""
    bank_name: str = ""
    logo_path: str = ""
    legal_info: str = ""
    invoice_prefix: str = "RE-"
    default_payment_days: int = 14
    default_vat_rate: Decimal = field(default_factory=lambda: Decimal("19.00"))
    default_currency: str = "EUR"


@dataclass
class InvoiceLine:
    line_id: int = 1
    article_number: str = ""
    description: str = ""
    quantity: Decimal = field(default_factory=lambda: Decimal("1.000"))
    unit_code: str = "HUR"
    unit_price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    line_total: Decimal = field(default_factory=lambda: Decimal("0.00"))
    vat_category_code: str = "S"
    vat_rate: Decimal = field(default_factory=lambda: Decimal("19.00"))
    sort_order: int = 0

    def calculate_line_total(self) -> None:
        self.line_total = round_decimal(self.quantity * self.unit_price)


@dataclass
class Invoice:
    number: str = ""
    type_code: str = "380"
    issue_date: date | None = None
    due_date: date | None = None
    delivery_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    currency: str = "EUR"
    customer_name: str = ""
    customer_address: dict | None = None
    customer_vat_id: str = ""
    buyer_reference: str = ""
    customer_contact_email: str = ""
    total_net: Decimal = field(default_factory=lambda: Decimal("0.00"))
    vat_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_gross: Decimal = field(default_factory=lambda: Decimal("0.00"))
    payment_means_code: str = "58"
    payment_terms: str = ""
    skonto_percent: Decimal | None = None
    skonto_days: int | None = None
    prepaid_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    due_payable_amount: Decimal | None = None
    order_reference: str = ""
    contract_reference: str = ""
    preceding_invoice_number: str = ""
    preceding_invoice_date: date | None = None
    note: str = ""
    lines: list[InvoiceLine] = field(default_factory=list)

    def calculate_totals(self) -> None:
        tax_groups: dict[tuple[str, Decimal], Decimal] = {}
        self.total_net = Decimal("0.00")

        for line in self.lines:
            line.calculate_line_total()
            self.total_net += line.line_total
            key = (line.vat_category_code, line.vat_rate)
            tax_groups[key] = tax_groups.get(key, Decimal("0.00")) + line.line_total

        self.vat_amount = Decimal("0.00")
        for (_, rate), basis in tax_groups.items():
            self.vat_amount += round_decimal(basis * rate / 100)

        self.total_gross = self.total_net + self.vat_amount
        prepaid = self.prepaid_amount or Decimal("0.00")
        self.due_payable_amount = self.total_gross - prepaid

    def get_tax_breakdown(self) -> list[dict]:
        tax_groups: dict[tuple[str, Decimal], Decimal] = {}
        for line in self.lines:
            key = (line.vat_category_code, line.vat_rate)
            tax_groups[key] = tax_groups.get(key, Decimal("0.00")) + line.line_total
        result = []
        for (cat_code, rate), basis in sorted(tax_groups.items()):
            result.append(
                {
                    "category_code": cat_code,
                    "rate": rate,
                    "basis_amount": round_decimal(basis),
                    "tax_amount": round_decimal(basis * rate / 100),
                }
            )
        return result


@dataclass
class ValidationError:
    field: str
    message: str
    severity: str  # "error" | "warning"
