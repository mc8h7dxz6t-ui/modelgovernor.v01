from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.000000000001")


def quantize_money(value: Decimal | str | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
