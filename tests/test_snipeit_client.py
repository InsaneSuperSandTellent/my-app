import sys
from unittest.mock import MagicMock, patch
import pytest
import requests

# Stub out src.config before the module under test loads it
_mock_config = MagicMock()
_mock_config.SNIPEIT_URL = "https://snipe.example.com"
_mock_config.SNIPEIT_API_KEY = "test-api-key"
sys.modules.setdefault("src.config", _mock_config)

import src.snipeit_client as snipeit_client
from src.snipeit_client import (
    AssetNotFoundError,
    MultipleAssetsError,
    SnipeITError,
    lookup_by_serial,
    update_purchase_cost,
)


def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _make_http_error_response(status_code: int = 500) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    http_err = requests.exceptions.HTTPError(response=resp)
    resp.raise_for_status.side_effect = http_err
    return resp


@patch("src.snipeit_client.requests.get")
class TestLookupBySerial:
    def test_single_asset_returns_dict(self, mock_get):
        asset = {"id": 1, "serial": "SN123", "name": "Laptop"}
        mock_get.return_value = _make_response({"total": 1, "rows": [asset]})
        result = lookup_by_serial("SN123")
        assert result == asset

    def test_zero_assets_raises_not_found(self, mock_get):
        mock_get.return_value = _make_response({"total": 0, "rows": []})
        with pytest.raises(AssetNotFoundError):
            lookup_by_serial("SN_MISSING")

    def test_multiple_assets_raises_multiple(self, mock_get):
        assets = [{"id": 1}, {"id": 2}]
        mock_get.return_value = _make_response({"total": 2, "rows": assets})
        with pytest.raises(MultipleAssetsError):
            lookup_by_serial("SN_DUP")

    def test_http_error_raises_snipeit_error(self, mock_get):
        mock_get.return_value = _make_http_error_response(500)
        with pytest.raises(SnipeITError):
            lookup_by_serial("SN_ERR")

    def test_network_error_raises_snipeit_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("timeout")
        with pytest.raises(SnipeITError):
            lookup_by_serial("SN_NET")


@patch("src.snipeit_client.requests.patch")
class TestUpdatePurchaseCost:
    def test_update_success(self, mock_patch):
        mock_patch.return_value = _make_response({"status": "success", "messages": "Asset updated successfully."})
        update_purchase_cost(42, 999.99)  # should not raise

    def test_update_failure_error_status_raises(self, mock_patch):
        mock_patch.return_value = _make_response({"status": "error", "messages": "Purchase cost is invalid."})
        with pytest.raises(SnipeITError):
            update_purchase_cost(42, -1.0)

    def test_update_http_error_raises(self, mock_patch):
        mock_patch.return_value = _make_http_error_response(403)
        with pytest.raises(SnipeITError):
            update_purchase_cost(42, 500.0)

    def test_update_network_error_raises(self, mock_patch):
        mock_patch.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(SnipeITError):
            update_purchase_cost(42, 500.0)
