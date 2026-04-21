import re

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
