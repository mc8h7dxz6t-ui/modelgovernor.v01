from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.000000000001")


def quantize_money(value: Decimal | str | float) -> Decimal:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
