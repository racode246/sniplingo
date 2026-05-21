import pytest

from sniplingo.adapters.mss_capturer import MssCapturer, region_to_monitor
from sniplingo.domain.errors import CaptureError
from sniplingo.domain.models import Region


def test_region_to_monitor_maps_fields_including_negative_origin():
    assert region_to_monitor(Region(-10, 20, 100, 50)) == {
        "left": -10,
        "top": 20,
        "width": 100,
        "height": 50,
    }


def test_capture_empty_region_raises_without_touching_mss():
    # is_empty is checked before mss is imported/used, so this stays a unit test.
    with pytest.raises(CaptureError):
        MssCapturer().capture(Region(5, 5, 0, 0))
