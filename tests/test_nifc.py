"""Test the NIFC downloads against the live service."""

import pytest

from nifc_wildfires import get_active_perimeters, get_incidents


@pytest.mark.integration
def test_active_perimeters():
    """Test that active perimeters come back as GeoJSON."""
    assert get_active_perimeters()["type"] == "FeatureCollection"


@pytest.mark.integration
def test_incidents():
    """Test that incidents come back as GeoJSON."""
    assert get_incidents()["type"] == "FeatureCollection"
