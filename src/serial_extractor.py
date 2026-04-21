import re

SERIAL_PATTERN = re.compile(
    r'(?:serial\s*(?:number|no\.?|nr\.?)|s/n|nr\s+seryjny)[:\s]+([A-Za-z0-9][\w\-]{3,})',
    re.IGNORECASE,
)


def extract_serial(text: str) -> str | None:
    match = SERIAL_PATTERN.search(text)
    return match.group(1) if match else None
