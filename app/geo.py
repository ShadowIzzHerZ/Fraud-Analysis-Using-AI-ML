"""Tiny geo helper: approximate city centroids + haversine distance.

Just enough fidelity to make "impossible travel" (same card, two cities, no
time to have physically flown between them) a believable detector for a
simulated stream — not meant as a real geocoding source. Cities span India
so the detector still has real geographic spread to work with (Mumbai to
Guwahati is ~2,400 km, for instance).
"""
from __future__ import annotations

import math

# (lat, lon) centroids, deliberately coarse.
COUNTRIES: dict[str, tuple[float, float]] = {
    "Mumbai": (19.076, 72.877),
    "Delhi": (28.613, 77.209),
    "Bengaluru": (12.972, 77.594),
    "Hyderabad": (17.385, 78.487),
    "Chennai": (13.083, 80.270),
    "Kolkata": (22.573, 88.364),
    "Pune": (18.520, 73.856),
    "Ahmedabad": (23.023, 72.571),
    "Jaipur": (26.912, 75.787),
    "Lucknow": (26.847, 80.946),
    "Chandigarh": (30.733, 76.779),
    "Kochi": (9.931, 76.267),
    "Bhopal": (23.259, 77.412),
    "Surat": (21.170, 72.831),
    "Guwahati": (26.144, 91.736),
    "Goa": (15.490, 73.828),
}

COUNTRY_CODES = list(COUNTRIES.keys())

# A plausible commercial-flight ceiling. Anything implying a faster average
# speed between two cities than this is physically impossible.
MAX_PLAUSIBLE_KMH = 900.0


def haversine_km(a: str, b: str) -> float:
    if a == b or a not in COUNTRIES or b not in COUNTRIES:
        return 0.0
    lat1, lon1 = COUNTRIES[a]
    lat2, lon2 = COUNTRIES[b]
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def implied_speed_kmh(country_a: str, country_b: str, seconds: float) -> float:
    if seconds <= 0:
        seconds = 1.0
    dist = haversine_km(country_a, country_b)
    return dist / (seconds / 3600.0)
