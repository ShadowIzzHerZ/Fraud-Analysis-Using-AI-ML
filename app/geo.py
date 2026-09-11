"""Tiny geo helper: approximate country centroids + haversine distance.

Just enough fidelity to make "impossible travel" (same card, two countries,
no time to have physically flown between them) a believable detector for a
simulated stream — not meant as a real geocoding source.
"""
from __future__ import annotations

import math

# (lat, lon) centroids, deliberately coarse.
COUNTRIES: dict[str, tuple[float, float]] = {
    "US": (39.8, -98.6),
    "GB": (54.0, -2.0),
    "DE": (51.2, 10.4),
    "FR": (46.6, 2.2),
    "IN": (22.0, 79.0),
    "BR": (-10.0, -55.0),
    "AU": (-25.0, 134.0),
    "JP": (36.2, 138.3),
    "NG": (9.1, 8.7),
    "CN": (35.9, 104.2),
    "RU": (61.5, 105.3),
    "ZA": (-29.0, 24.0),
    "CA": (56.1, -106.3),
    "MX": (23.6, -102.5),
    "AE": (23.4, 53.8),
    "SG": (1.35, 103.8),
}

COUNTRY_CODES = list(COUNTRIES.keys())

# A plausible commercial-flight ceiling. Anything implying a faster average
# speed between two countries than this is physically impossible.
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
