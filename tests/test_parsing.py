"""Tests for AISFriends parsing helpers."""
from datetime import timezone

from custom_components.aisfriends import AISFriendsCoordinator
from custom_components.aisfriends.config_flow import _parse_mmsi_input


def test_parse_mmsi_input_filters_and_deduplicates() -> None:
    """Only valid unique nine-digit MMSIs are retained."""
    assert _parse_mmsi_input("235091818, bad;232002643\n235091818") == [
        "235091818",
        "232002643",
    ]


def test_parse_eta_iso_utc() -> None:
    """ISO UTC ETAs are returned timezone-aware."""
    eta = AISFriendsCoordinator._parse_eta("2026-08-26T10:30:00Z")
    assert eta is not None
    assert eta.tzinfo == timezone.utc
    assert eta.hour == 10
    assert eta.minute == 30


def test_parse_eta_invalid_sentinel() -> None:
    """AIS unknown ETA sentinels are ignored."""
    assert AISFriendsCoordinator._parse_eta("00-00 24:60") is None
