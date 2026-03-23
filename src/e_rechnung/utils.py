from decimal import ROUND_HALF_UP, Decimal

FACTUR_X_GUIDELINE = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"
PROFILE = "EXTENDED"

VAT_CODES = {
    "VAT": "S",
    "VAT7": "S",
    "EU": "K",
    "EX": "G",
    "AE": "AE",
    "E": "E",
    "Z": "Z",
}

UNIT_CODES = [
    ("HUR", "Stunde", "Hour"),
    ("DAY", "Tag", "Day"),
    ("MON", "Monat", "Month"),
    ("C62", "Stueck", "Piece"),
    ("KGM", "Kilogramm", "Kilogram"),
    ("MTR", "Meter", "Metre"),
    ("LTR", "Liter", "Litre"),
    ("KWH", "Kilowattstunde", "Kilowatt hour"),
    ("TNE", "Tonne", "Tonne"),
    ("MTK", "Quadratmeter", "Square metre"),
    ("LS", "Pauschale", "Lump sum"),
    ("SET", "Set", "Set"),
    ("MIN", "Minute", "Minute"),
]

VAT_CATEGORIES = [
    ("S", "Normaler Steuersatz", Decimal("19.00"), None, None),
    ("S7", "Ermaessigter Steuersatz", Decimal("7.00"), None, None),
    ("K", "Innergemeinschaftliche Lieferung", Decimal("0.00"), "Intra-Community supply", "VATEX-EU-IC"),
    ("G", "Ausfuhrlieferung", Decimal("0.00"), "Export supply", "VATEX-EU-EXP"),
    ("AE", "Reverse Charge", Decimal("0.00"), "Reverse charge", "VATEX-EU-AE"),
    ("E", "Steuerbefreit", Decimal("0.00"), "Exempt from tax", "VATEX-EU-132"),
    ("Z", "Nullsatz", Decimal("0.00"), None, None),
]


def round_decimal(value: Decimal | int | float | str, decimals: int = 2) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    quantize_str = "0." + "0" * decimals if decimals > 0 else "1"
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def format_betrag(value: Decimal | int | float | str) -> str:
    d = round_decimal(value)
    sign, digits, exp = d.as_tuple()
    int_part = int(abs(d))
    frac = f"{abs(d) - int_part:.2f}"[2:]
    int_str = f"{int_part:,}".replace(",", ".")
    result = f"{int_str},{frac}"
    if sign:
        result = "-" + result
    return result


def format_invoice_number(prefix: str, year: int, counter: int, width: int = 5) -> str:
    return f"{prefix}{year}-{counter:0{width}d}"
