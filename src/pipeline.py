from pathlib import Path

from src.pdf_extractor import extract_text
from src.amount_extractor import extract_amount
from src.serial_extractor import extract_serial
from src.snipeit_client import lookup_by_serial, update_purchase_cost, AssetNotFoundError, MultipleAssetsError, SnipeITError
from src.processed_tracker import load_processed, save_processed
from src.logger import log_ok, log_skipped, log_unresolved, log_ambiguous, log_error


def process_invoice(filepath: Path) -> None:
    filename = filepath.name

    processed = load_processed()
    if filename in processed:
        log_skipped(filename, "already processed")
        return

    text = extract_text(filepath)
    if text is None:
        log_unresolved(filename, "no text extracted from PDF")
        return
    if isinstance(text, str) and text.startswith("ERROR:"):
        log_error(filename, f"PDF extraction failed: {text[7:]}")
        return

    amount, method = extract_amount(text)
    if amount is None:
        log_unresolved(filename, "could not extract amount")
        return

    serial = extract_serial(text)
    if serial is None:
        log_unresolved(filename, "could not extract serial number")
        return

    try:
        asset = lookup_by_serial(serial)
    except AssetNotFoundError as exc:
        log_unresolved(filename, str(exc))
        return
    except MultipleAssetsError as exc:
        log_ambiguous(filename, str(exc))
        return
    except SnipeITError as exc:
        log_error(filename, str(exc))
        return

    asset_id = asset.get("id")
    if asset_id is None:
        log_error(filename, "asset record missing id field")
        return

    try:
        update_purchase_cost(asset_id, amount)
    except SnipeITError as exc:
        log_error(filename, str(exc))
        return

    processed.append(filename)
    save_processed(processed)
    log_ok(filename, f"purchase_cost set to {amount} via {method} (asset {asset_id})")
