import sys
from pathlib import Path

from src.config import INVOICES_FOLDER
from src.processed_tracker import load_processed
from src.pipeline import process_invoice
from src.logger import log_error

try:
    folder = Path(INVOICES_FOLDER)
    pdf_files = sorted(folder.glob("*.pdf"))
    processed = load_processed()

    for pdf in pdf_files:
        if pdf.name in processed:
            continue
        process_invoice(pdf)
except Exception as exc:
    log_error("main", str(exc))
    sys.exit(1)
