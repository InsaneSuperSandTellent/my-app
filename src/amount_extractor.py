import re
from typing import Sequence


def normalize_amount(raw: str) -> float:
    stripped = raw.strip()
    if ',' in stripped and '.' not in stripped:
        # comma is decimal separator (Polish style): "1 234,56"
        return float(stripped.replace(' ', '').replace(',', '.'))
    # period is decimal separator (English style): "1,234.56"
    return float(stripped.replace(',', '').replace(' ', ''))


def select_largest(amounts: Sequence[float]) -> float:
    return max(amounts)


# Polish-style invoices — e.g. "Do zapłaty: 1 234,56 PLN"
INVOICE_FORMAT_A = re.compile(
    r'(?:do\s+zap[łl]aty|razem|suma)[:\s]+(\d[\d\s]*,\d{2})',
    re.IGNORECASE,
)

# English-style invoices — e.g. "Total: 1,234.56"
INVOICE_FORMAT_B = re.compile(
    r'(?:total|amount\s+due|subtotal)[:\s]+\$?(\d[\d,]*\.\d{2})',
    re.IGNORECASE,
)


def extract_amount(text: str) -> tuple[float | None, str]:
    matches = INVOICE_FORMAT_A.findall(text) + INVOICE_FORMAT_B.findall(text)
    if matches:
        amounts = [normalize_amount(m) for m in matches]
        return (select_largest(amounts), "regex")
    from src.claude_fallback import extract_with_claude
    return (extract_with_claude(text), "claude-api")
