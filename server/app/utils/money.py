from decimal import Decimal, ROUND_HALF_UP


def parse_dollars_to_cents(value: str | int | float | Decimal | None) -> int | None:
    """
    Parse a dollar-denominated value into integer cents.

    Accepted examples:
    - "1123.30"
    - "$1,123.30"
    - "(1,123.30)"  # negative accounting style
    - 1123
    - 1123.30
    - Decimal("1123.30")

    Returns:
    - integer cents
    - None for None or empty strings

    Raises:
    - ValueError for invalid values/formats
    """

    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid money value")

    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, (int, float)):
        amount = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        negative = False
        if text.startswith("(") and text.endswith(")"):
            negative = True
            text = text[1:-1].strip()

        # Accept common currency formatting from CSV exports.
        text = text.replace("$", "").replace(",", "").strip()
        if not text:
            return None

        if text.count("-") > 1:
            raise ValueError(f"Invalid money value: {value!r}")
        if "-" in text and not text.startswith("-"):
            raise ValueError(f"Invalid money value: {value!r}")

        try:
            amount = Decimal(text)
        except Exception as exc:
            raise ValueError(f"Invalid money value: {value!r}") from exc

        if negative:
            amount = -amount
    else:
        raise ValueError(f"Unsupported money value type: {type(value).__name__}")

    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def cents_to_decimal_str(cents: int | None) -> str | None:
    """
    Convert integer cents to a fixed 2-decimal dollar string.

    Example:
    - 112330 -> "1123.30"
    """

    if cents is None:
        return None
    if isinstance(cents, bool):
        raise ValueError("Boolean is not a valid cents value")
    if not isinstance(cents, int):
        raise ValueError("cents must be an integer or None")

    dollars = Decimal(cents) / Decimal("100")
    return format(dollars.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def cents_to_float(cents: int | None) -> float | None:
    """
    Convert integer cents to dollar float.

    Use only when float precision tradeoffs are acceptable.
    """

    if cents is None:
        return None
    if isinstance(cents, bool):
        raise ValueError("Boolean is not a valid cents value")
    if not isinstance(cents, int):
        raise ValueError("cents must be an integer or None")

    return float(Decimal(cents) / Decimal("100"))
