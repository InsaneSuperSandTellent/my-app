import requests
from src.config import SNIPEIT_URL, SNIPEIT_API_KEY


class AssetNotFoundError(Exception):
    pass


class MultipleAssetsError(Exception):
    pass


class SnipeITError(Exception):
    pass


def lookup_by_serial(serial: str) -> dict:
    url = f"{SNIPEIT_URL.rstrip('/')}/api/v1/hardware"
    headers = {
        "Authorization": f"Bearer {SNIPEIT_API_KEY}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, params={"serial": serial}, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise SnipeITError(f"HTTP/network error looking up serial {serial!r}: {exc}") from exc

    data = response.json()
    assets = data.get("rows", [])
    total = data.get("total", len(assets))

    if total == 0 or len(assets) == 0:
        raise AssetNotFoundError(f"No asset found for serial {serial!r}")
    if total > 1 or len(assets) > 1:
        raise MultipleAssetsError(f"Multiple assets ({total}) found for serial {serial!r}")

    return assets[0]


def update_purchase_cost(asset_id: int, amount: float) -> None:
    url = f"{SNIPEIT_URL.rstrip('/')}/api/v1/hardware/{asset_id}"
    headers = {
        "Authorization": f"Bearer {SNIPEIT_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        response = requests.patch(url, json={"purchase_cost": amount}, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise SnipeITError(f"HTTP/network error updating asset {asset_id}: {exc}") from exc

    data = response.json()
    if data.get("status") == "error":
        messages = data.get("messages", data.get("error", "unknown error"))
        raise SnipeITError(f"Snipe-IT rejected update for asset {asset_id}: {messages}")
