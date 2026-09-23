from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.god_view import GodViewData, god_view_html


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.payload[:limit]


def test_god_view_public_evidence_is_bounded_and_labelled():
    seen = []

    def opener(request, timeout):
        seen.append((request.full_url, timeout))
        if "nominatim" in request.full_url:
            return Response([{"display_name": "Lapland, Finland", "lat": "67.92", "lon": "26.50"}])
        if "open-meteo" in request.full_url:
            return Response({"timezone": "Europe/Helsinki", "current": {"temperature_2m": -4}, "daily": {"time": []}})
        if "epic.gsfc.nasa.gov/api/natural" in request.full_url:
            return Response([{"image": "epic_1b_20260829003633", "date": "2026-08-29 00:32:44", "caption": "Earth"}])
        if "wheretheiss.at" in request.full_url:
            return Response({"latitude": 12.5, "longitude": -43.2, "altitude": 418.4, "velocity": 27580, "timestamp": 1788039000, "visibility": "daylight"})
        return Response({"ac": [{"hex": "abc123", "flight": "FIN123", "lat": 67.9, "lon": 26.6, "alt_baro": 32000, "gs": 440}]})

    data = GodViewData(opener)
    place = data.geocode("Lapland")
    weather = data.weather(67.92, 26.5)
    flights = data.flights(67.92, 26.5)
    earth = data.nasa_earth()
    iss = data.iss_position()
    assert place["status"] == "LIVE"
    assert place["matches"][0]["name"] == "Lapland, Finland"
    assert weather["status"] == "FORECAST"
    assert flights["status"] == "LIVE"
    assert flights["aircraft"][0]["flight"] == "FIN123"
    assert earth["status"] == "RECENT SATELLITE IMAGE"
    assert earth["source"] == "NASA DSCOVR EPIC"
    assert earth["image_url"].endswith("epic_1b_20260829003633.png")
    assert iss["status"] == "LIVE POSITION"
    assert iss["latitude"] == 12.5
    assert all(timeout == 8 for _, timeout in seen)


def test_god_view_rejects_bad_coordinates_and_escapes_token():
    data = GodViewData(lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="Invalid coordinates"):
        data.weather(91, 0)
    page = god_view_html('bad"token').decode("utf-8")
    assert 'bad"token' not in page
    assert "bad&amp;quot;token" not in page
    assert "Pilot Mode" in page
    assert "NASA Earth Now" in page
    assert "Live View from Space" in page
    assert "Track ISS" in page
    assert "fO9e9jnhYK8" in page
    assert "SEN STV-1" in page
    assert "showMapTiles" in page
    assert "/tile/" in page
    assert "function moveControl" in page
    assert "launchMode==='fly'" in page
    assert "LIVE ISS" in page
