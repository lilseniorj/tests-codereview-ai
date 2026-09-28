from __future__ import annotations

import unittest
from decimal import Decimal

from payments_svc.amounts import (
    AmountError,
    CurrencyError,
    calculate_fee,
    normalize_currency,
    total_with_fee,
    validate_amount,
)


class ValidateAmountNonFiniteTest(unittest.TestCase):
    # E-03
    def test_validate_amount_rejects_nan_with_amount_error(self):
        # Arrange
        amount = Decimal("NaN")

        # Act / Assert
        with self.assertRaises(AmountError):
            validate_amount(amount)

    # E-03
    def test_validate_amount_rejects_signaling_nan_with_amount_error(self):
        # Arrange
        amount = Decimal("sNaN")

        # Act / Assert
        with self.assertRaises(AmountError):
            validate_amount(amount)

    # E-03
    def test_validate_amount_rejects_infinities_with_amount_error(self):
        for raw in ("Infinity", "-Infinity"):
            with self.subTest(raw=raw):
                # Arrange
                amount = Decimal(raw)

                # Act / Assert
                with self.assertRaises(AmountError):
                    validate_amount(amount)


class ValidateAmountMissingTest(unittest.TestCase):
    # N-01
    def test_validate_amount_rejects_none_as_required_amount(self):
        # Arrange
        amount = None

        # Act
        with self.assertRaises(AmountError) as ctx:
            validate_amount(amount)

        # Assert
        self.assertEqual(str(ctx.exception), "amount is required")


class CurrencyInvalidTypeTest(unittest.TestCase):
    # E-04
    def test_normalize_currency_rejects_non_string_with_currency_error(self):
        for currency in (123, 12.5, ["USD"], object()):
            with self.subTest(currency=currency):
                # Arrange: currency ya definido por subTest

                # Act / Assert
                with self.assertRaises(CurrencyError):
                    normalize_currency(currency)

    # E-04
    def test_calculate_fee_rejects_non_string_currency_with_currency_error(self):
        # Arrange
        amount = Decimal("100.00")
        currency = 123

        # Act / Assert
        with self.assertRaises(CurrencyError):
            calculate_fee(amount, currency)

    # E-04
    def test_total_with_fee_rejects_non_string_currency_with_currency_error(self):
        # Arrange
        amount = Decimal("100.00")
        currency = 123

        # Act / Assert
        with self.assertRaises(CurrencyError):
            total_with_fee(amount, currency)


class TotalEqualsAmountPlusFeeTest(unittest.TestCase):
    # B-03
    def test_total_with_fee_equals_amount_plus_fee_for_cent_precision_amounts(self):
        cases = [
            (Decimal("100.00"), "USD"),
            (Decimal("1.00"), "USD"),
            (Decimal("1000.20"), "EUR"),
            (Decimal("49.99"), "EUR"),
            (Decimal("1000.00"), "COP"),
            (Decimal("100000.00"), "USD"),
        ]
        for amount, currency in cases:
            with self.subTest(amount=amount, currency=currency):
                # Arrange: amount y currency definidos por subTest

                # Act
                fee = calculate_fee(amount, currency)
                total = total_with_fee(amount, currency)

                # Assert
                self.assertEqual(total, amount + fee)


if __name__ == "__main__":
    unittest.main()
