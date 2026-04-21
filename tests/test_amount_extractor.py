import pytest
from src.amount_extractor import (
    INVOICE_FORMAT_A,
    INVOICE_FORMAT_B,
    normalize_amount,
    select_largest,
    extract_amount,
)


class TestInvoiceFormatA:
    def test_do_zaplaty(self):
        assert INVOICE_FORMAT_A.findall("Do zapłaty: 1 234,56 PLN") == ["1 234,56"]

    def test_razem(self):
        assert INVOICE_FORMAT_A.findall("Razem: 999,00") == ["999,00"]

    def test_suma(self):
        assert INVOICE_FORMAT_A.findall("Suma: 12 000,99") == ["12 000,99"]

    def test_case_insensitive(self):
        assert INVOICE_FORMAT_A.findall("DO ZAPŁATY: 50,00") == ["50,00"]

    def test_no_match(self):
        assert INVOICE_FORMAT_A.findall("Total: 100.00") == []


class TestInvoiceFormatB:
    def test_total(self):
        assert INVOICE_FORMAT_B.findall("Total: 1,234.56") == ["1,234.56"]

    def test_amount_due(self):
        assert INVOICE_FORMAT_B.findall("Amount Due: $500.00") == ["500.00"]

    def test_subtotal(self):
        assert INVOICE_FORMAT_B.findall("Subtotal: 99.99") == ["99.99"]

    def test_case_insensitive(self):
        assert INVOICE_FORMAT_B.findall("TOTAL: 200.00") == ["200.00"]

    def test_no_match(self):
        assert INVOICE_FORMAT_B.findall("Razem: 100,00") == []


class TestNormalizeAmount:
    def test_comma_decimal(self):
        assert normalize_amount("1 234,56") == pytest.approx(1234.56)

    def test_comma_decimal_no_space(self):
        assert normalize_amount("999,00") == pytest.approx(999.00)

    def test_period_decimal_with_comma_thousands(self):
        assert normalize_amount("1,234.56") == pytest.approx(1234.56)

    def test_period_decimal_plain(self):
        assert normalize_amount("500.00") == pytest.approx(500.00)

    def test_integer_style(self):
        assert normalize_amount("100.00") == pytest.approx(100.00)


class TestSelectLargest:
    def test_single(self):
        assert select_largest([42.0]) == 42.0

    def test_multiple(self):
        assert select_largest([10.0, 200.0, 50.0]) == 200.0

    def test_equal(self):
        assert select_largest([5.0, 5.0]) == 5.0


class TestExtractAmount:
    def test_format_a_match(self):
        amount, method = extract_amount("Do zapłaty: 1 234,56 PLN")
        assert amount == pytest.approx(1234.56)
        assert method == "regex"

    def test_format_b_match(self):
        amount, method = extract_amount("Total: 1,234.56")
        assert amount == pytest.approx(1234.56)
        assert method == "regex"

    def test_selects_largest_when_multiple(self):
        text = "Subtotal: 100.00\nTotal: 200.00"
        amount, method = extract_amount(text)
        assert amount == pytest.approx(200.00)
        assert method == "regex"

    def test_no_regex_match_calls_claude(self, monkeypatch):
        import src.claude_fallback as cf
        monkeypatch.setattr(cf, "extract_with_claude", lambda text: 77.77)
        amount, method = extract_amount("no pattern here")
        assert amount == pytest.approx(77.77)
        assert method == "claude-api"

    def test_no_regex_match_claude_returns_none(self, monkeypatch):
        import src.claude_fallback as cf
        monkeypatch.setattr(cf, "extract_with_claude", lambda text: None)
        amount, method = extract_amount("no pattern here")
        assert amount is None
        assert method == "claude-api"
