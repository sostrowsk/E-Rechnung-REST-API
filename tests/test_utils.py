from decimal import Decimal

from e_rechnung.utils import format_betrag, format_invoice_number, round_decimal


def test_round_decimal_basic():
    assert round_decimal(Decimal("1.005")) == Decimal("1.01")
    assert round_decimal(Decimal("1.004")) == Decimal("1.00")


def test_round_decimal_from_string():
    assert round_decimal("3.14159", 3) == Decimal("3.142")


def test_round_decimal_from_int():
    assert round_decimal(42) == Decimal("42.00")


def test_round_decimal_zero_places():
    assert round_decimal(Decimal("3.5"), 0) == Decimal("4")


def test_round_decimal_negative():
    assert round_decimal(Decimal("-1.005")) == Decimal("-1.01")


def test_format_betrag_basic():
    assert format_betrag(Decimal("1234.56")) == "1.234,56"


def test_format_betrag_small():
    assert format_betrag(Decimal("0.50")) == "0,50"


def test_format_betrag_large():
    assert format_betrag(Decimal("1234567.89")) == "1.234.567,89"


def test_format_betrag_negative():
    assert format_betrag(Decimal("-42.10")) == "-42,10"


def test_format_invoice_number():
    assert format_invoice_number("RE-", 2026, 1) == "RE-2026-00001"
    assert format_invoice_number("INV-", 2026, 42, 3) == "INV-2026-042"
