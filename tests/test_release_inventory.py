from tools.release_inventory import build_inventory
from core.version import CORE_VERSION


def test_release_inventory_is_bounded_and_reports_core_version() -> None:
    inventory = build_inventory()
    assert inventory["schema"] == "mediamanager-release-inventory-v1"
    assert inventory["core_version"] == CORE_VERSION
    names = [item["name"].lower() for item in inventory["components"]]
    assert names == sorted(["cryptography", "pyside6", "yt-dlp", "yt-dlp-ejs"])
