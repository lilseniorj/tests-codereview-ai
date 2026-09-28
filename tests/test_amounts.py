from __future__ import annotations

from decimal import Decimal

import pytest

from payments_svc.amounts import (
    MAX_AMOUNT,
    AmountError,
    CurrencyError,
    calculate_fee,
    normalize_currency,
    parse_amount,
    round_money,
    total_with_fee,
    validate_amount,
)

# --- parse_amount -----------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12.50", Decimal("12.50")),
        ("  12.50  ", Decimal("12.50")),
        (10, Decimal("10")),
        (0.1, Decimal("0.1")),
        (Decimal("99.99"), Decimal("99.99")),
        ("-5", Decimal("-5")),
        ("0", Decimal("0")),
    ],
)
def test_parse_amount_accepts_numeric_input(raw, expected):
    result = parse_amount(raw)

    assert result == expected
    assert isinstance(result, Decimal)


def test_parse_amount_preserves_string_precision():
    assert str(parse_amount("12.50")) == "12.50"


def test_parse_amount_rejects_none():
    with pytest.raises(AmountError, match="amount is required"):
        parse_amount(None)


@pytest.mark.parametrize("raw", ["abc", "", "   ", "12,50", "1.2.3", "$10"])
def test_parse_amount_rejects_non_numeric(raw):
    with pytest.raises(AmountError, match="amount must be numeric"):
        parse_amount(raw)


@pytest.mark.parametrize("raw", ["NaN", "sNaN", "Infinity", "-Infinity", float("inf"), float("nan")])
def test_parse_amount_rejects_non_finite(raw):
    with pytest.raises(AmountError, match="amount must be finite"):
        parse_amount(raw)


def test_amount_error_is_value_error():
    with pytest.raises(ValueError):
        parse_amount("abc")


# --- normalize_currency -----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("USD", "USD"),
        ("usd", "USD"),
        ("  eur ", "EUR"),
        ("CoP", "COP"),
    ],
)
def test_normalize_currency_accepts_supported(raw, expected):
    assert normalize_currency(raw) == expected


def test_normalize_currency_rejects_none():
    with pytest.raises(CurrencyError, match="currency is required"):
        normalize_currency(None)


@pytest.mark.parametrize("raw", ["", "   "])
def test_normalize_currency_rejects_blank(raw):
    with pytest.raises(CurrencyError, match="currency is required"):
        normalize_currency(raw)


@pytest.mark.parametrize(("raw", "shown"), [("gbp", "GBP"), (" mxn ", "MXN")])
def test_normalize_currency_rejects_unsupported_with_normalized_name(raw, shown):
    with pytest.raises(CurrencyError, match=f"unsupported currency: {shown}$"):
        normalize_currency(raw)


def test_currency_error_is_value_error():
    with pytest.raises(ValueError):
        normalize_currency("XXX")


# --- validate_amount --------------------------------------------------------


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("0.01"), Decimal("500"), MAX_AMOUNT])
def test_validate_amount_accepts_valid_range(amount):
    assert validate_amount(amount) is None


@pytest.mark.parametrize("amount", [Decimal("-0.01"), Decimal("-100")])
def test_validate_amount_rejects_negative(amount):
    with pytest.raises(AmountError, match="amount cannot be negative"):
        validate_amount(amount)


@pytest.mark.parametrize("amount", [Decimal("100000.01"), Decimal("1000000")])
def test_validate_amount_rejects_above_maximum(amount):
    with pytest.raises(AmountError, match="amount exceeds maximum allowed"):
        validate_amount(amount)


# --- round_money ------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1"), "1.00"),
        (Decimal("1.234"), "1.23"),
        (Decimal("1.236"), "1.24"),
        # ROUND_HALF_EVEN (banker's rounding): ties go to the even digit.
        (Decimal("1.005"), "1.00"),
        (Decimal("1.015"), "1.02"),
        (Decimal("1.025"), "1.02"),
        (Decimal("-1.005"), "-1.00"),
    ],
)
def test_round_money_quantizes_to_cents_half_even(value, expected):
    assert str(round_money(value)) == expected


# --- calculate_fee ----------------------------------------------------------


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        # Percentage fee above the minimum.
        (Decimal("100"), "USD", "2.90"),
        (Decimal("100"), "EUR", "2.50"),
        (Decimal("100000"), "COP", "1900.00"),
        # Percentage fee below the minimum -> minimum applies.
        (Decimal("1"), "USD", "0.30"),
        (Decimal("10"), "USD", "0.30"),
        (Decimal("1"), "EUR", "0.25"),
        (Decimal("1000"), "COP", "900.00"),
        # Percentage fee exactly equal to the minimum.
        (Decimal("10"), "EUR", "0.25"),
        # Just above the USD threshold (0.30 / 0.029 ≈ 10.345).
        (Decimal("10.35"), "USD", "0.30"),
        (Decimal("11"), "USD", "0.32"),
        # Maximum allowed amount.
        (MAX_AMOUNT, "USD", "2900.00"),
    ],
)
def test_calculate_fee(amount, currency, expected):
    assert str(calculate_fee(amount, currency)) == expected


def test_calculate_fee_normalizes_currency():
    assert calculate_fee(Decimal("100"), " usd ") == Decimal("2.90")


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("1000.20"), "25.00"),  # 25.005 -> tie rounds to even (0)
        (Decimal("1000.60"), "25.02"),  # 25.015 -> tie rounds to even (2)
    ],
)
def test_calculate_fee_uses_half_even_rounding(amount, expected):
    assert str(calculate_fee(amount, "EUR")) == expected


@pytest.mark.parametrize("currency", ["USD", "EUR", "COP"])
def test_calculate_fee_is_zero_for_zero_amount(currency):
    fee = calculate_fee(Decimal("0"), currency)

    assert str(fee) == "0.00"


def test_calculate_fee_rejects_unsupported_currency():
    with pytest.raises(CurrencyError, match="unsupported currency: GBP"):
        calculate_fee(Decimal("100"), "GBP")


def test_calculate_fee_rejects_negative_amount():
    with pytest.raises(AmountError, match="amount cannot be negative"):
        calculate_fee(Decimal("-1"), "USD")


def test_calculate_fee_rejects_amount_above_maximum():
    with pytest.raises(AmountError, match="amount exceeds maximum allowed"):
        calculate_fee(Decimal("100000.01"), "USD")


def test_calculate_fee_validates_currency_before_amount():
    with pytest.raises(CurrencyError):
        calculate_fee(Decimal("-1"), "GBP")


# --- total_with_fee ---------------------------------------------------------


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        (Decimal("100"), "USD", "102.90"),
        (Decimal("100"), "EUR", "102.50"),
        (Decimal("1"), "USD", "1.30"),
        (Decimal("1000"), "COP", "1900.00"),
        (Decimal("0"), "USD", "0.00"),
        (Decimal("19.999"), "USD", "20.58"),  # 19.999 + 0.58 = 20.579 -> 20.58
        (MAX_AMOUNT, "USD", "102900.00"),
    ],
)
def test_total_with_fee(amount, currency, expected):
    assert str(total_with_fee(amount, currency)) == expected


def test_total_with_fee_rejects_negative_amount():
    with pytest.raises(AmountError, match="amount cannot be negative"):
        total_with_fee(Decimal("-0.01"), "USD")


def test_total_with_fee_rejects_amount_above_maximum():
    with pytest.raises(AmountError, match="amount exceeds maximum allowed"):
        total_with_fee(Decimal("100000.01"), "USD")


def test_total_with_fee_validates_amount_before_currency():
    with pytest.raises(AmountError):
        total_with_fee(Decimal("-1"), "GBP")


def test_total_with_fee_rejects_unsupported_currency():
    with pytest.raises(CurrencyError, match="unsupported currency: GBP"):
        total_with_fee(Decimal("100"), "GBP")


# --- parse -> fee pipeline --------------------------------------------------


def test_parsed_string_amount_flows_through_fee_calculation():
    amount = parse_amount(" 250.00 ")

    assert calculate_fee(amount, "usd") == Decimal("7.25")
    assert total_with_fee(amount, "usd") == Decimal("257.25")
