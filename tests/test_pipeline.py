import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Define real exception classes before stubbing so pipeline.py gets them
class AssetNotFoundError(Exception):
    pass


class MultipleAssetsError(Exception):
    pass


class SnipeITError(Exception):
    pass


# Stub heavy dependencies before pipeline imports them
_snipeit_stub = MagicMock()
_snipeit_stub.AssetNotFoundError = AssetNotFoundError
_snipeit_stub.MultipleAssetsError = MultipleAssetsError
_snipeit_stub.SnipeITError = SnipeITError

for mod in ("src.config", "src.logger", "src.processed_tracker",
            "src.pdf_extractor", "src.amount_extractor", "src.serial_extractor"):
    sys.modules.setdefault(mod, MagicMock())

sys.modules["src.snipeit_client"] = _snipeit_stub

_logger = sys.modules["src.logger"]
_tracker = sys.modules["src.processed_tracker"]
_tracker.load_processed.return_value = []
_tracker.save_processed.return_value = None

from src.pipeline import process_invoice  # noqa: E402

FAKE_PATH = Path("invoices/INV-001.pdf")


def _reset_logger():
    for name in ("log_ok", "log_skipped", "log_unresolved", "log_ambiguous", "log_error"):
        getattr(_logger, name).reset_mock()


@patch("src.pipeline.save_processed")
@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.update_purchase_cost")
@patch("src.pipeline.lookup_by_serial", return_value={"id": 7, "serial": "SN-ABC"})
@patch("src.pipeline.extract_serial", return_value="SN-ABC")
@patch("src.pipeline.extract_amount", return_value=(1299.99, "regex"))
@patch("src.pipeline.extract_text", return_value="Invoice text with amount and serial")
def test_happy_path(mock_text, mock_amount, mock_serial, mock_lookup, mock_update, mock_load, mock_save):
    _reset_logger()
    process_invoice(FAKE_PATH)
    mock_update.assert_called_once_with(7, 1299.99)
    mock_save.assert_called_once()
    _logger.log_ok.assert_called_once()


@patch("src.pipeline.load_processed", return_value=["INV-001.pdf"])
def test_already_processed_skips(mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_skipped.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value=None)
def test_no_text_extracted(mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_unresolved.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value="ERROR: corrupted file")
def test_pdf_extraction_error(mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_error.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value="some text")
@patch("src.pipeline.extract_amount", return_value=(None, "regex"))
def test_amount_not_found(mock_amount, mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_unresolved.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value="some text")
@patch("src.pipeline.extract_amount", return_value=(500.0, "regex"))
@patch("src.pipeline.extract_serial", return_value=None)
def test_serial_not_found(mock_serial, mock_amount, mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_unresolved.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value="some text")
@patch("src.pipeline.extract_amount", return_value=(500.0, "regex"))
@patch("src.pipeline.extract_serial", return_value="SN-XYZ")
@patch("src.pipeline.lookup_by_serial", side_effect=AssetNotFoundError("not found"))
def test_asset_not_found(mock_lookup, mock_serial, mock_amount, mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_unresolved.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value="some text")
@patch("src.pipeline.extract_amount", return_value=(500.0, "regex"))
@patch("src.pipeline.extract_serial", return_value="SN-DUP")
@patch("src.pipeline.lookup_by_serial", side_effect=MultipleAssetsError("ambiguous"))
def test_multiple_assets(mock_lookup, mock_serial, mock_amount, mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_ambiguous.assert_called_once()


@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.extract_text", return_value="some text")
@patch("src.pipeline.extract_amount", return_value=(500.0, "regex"))
@patch("src.pipeline.extract_serial", return_value="SN-ERR")
@patch("src.pipeline.lookup_by_serial", side_effect=SnipeITError("network error"))
def test_snipeit_lookup_error(mock_lookup, mock_serial, mock_amount, mock_text, mock_load):
    _reset_logger()
    process_invoice(FAKE_PATH)
    _logger.log_error.assert_called_once()


@patch("src.pipeline.save_processed")
@patch("src.pipeline.load_processed", return_value=[])
@patch("src.pipeline.update_purchase_cost", side_effect=SnipeITError("update failed"))
@patch("src.pipeline.lookup_by_serial", return_value={"id": 3, "serial": "SN-UPD"})
@patch("src.pipeline.extract_serial", return_value="SN-UPD")
@patch("src.pipeline.extract_amount", return_value=(750.0, "claude-api"))
@patch("src.pipeline.extract_text", return_value="some text")
def test_update_failure(mock_text, mock_amount, mock_serial, mock_lookup, mock_update, mock_load, mock_save):
    _reset_logger()
    process_invoice(FAKE_PATH)
    mock_save.assert_not_called()
    _logger.log_error.assert_called_once()
