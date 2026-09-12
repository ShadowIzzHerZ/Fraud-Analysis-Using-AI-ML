package com.zenpay.app

import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Direct Kotlin port of the Python backend's app/geo.py — same city
 * centroids, same haversine math, same plausible-speed ceiling — so the
 * on-device GEO_JUMP detector (FraudScorer.kt) behaves identically to the
 * server's, in case you ever compare the two.
 */
object Geo {
    val CITIES: Map<String, Pair<Double, Double>> = mapOf(
        "Mumbai" to (19.076 to 72.877),
        "Delhi" to (28.613 to 77.209),
        "Bengaluru" to (12.972 to 77.594),
        "Hyderabad" to (17.385 to 78.487),
        "Chennai" to (13.083 to 80.270),
        "Kolkata" to (22.573 to 88.364),
        "Pune" to (18.520 to 73.856),
        "Ahmedabad" to (23.023 to 72.571),
        "Jaipur" to (26.912 to 75.787),
        "Lucknow" to (26.847 to 80.946),
        "Chandigarh" to (30.733 to 76.779),
        "Kochi" to (9.931 to 76.267),
        "Bhopal" to (23.259 to 77.412),
        "Surat" to (21.170 to 72.831),
        "Guwahati" to (26.144 to 91.736),
        "Goa" to (15.490 to 73.828),
    )
    val CITY_NAMES: List<String> = CITIES.keys.toList()
    const val MAX_PLAUSIBLE_KMH = 900.0

    fun haversineKm(a: String, b: String): Double {
        val pa = CITIES[a] ?: return 0.0
        val pb = CITIES[b] ?: return 0.0
        if (a == b) return 0.0
        val r = 6371.0
        val (lat1, lon1) = pa
        val (lat2, lon2) = pb
        val p1 = Math.toRadians(lat1)
        val p2 = Math.toRadians(lat2)
        val dPhi = Math.toRadians(lat2 - lat1)
        val dLambda = Math.toRadians(lon2 - lon1)
        val sinDPhi = sin(dPhi / 2)
        val sinDLambda = sin(dLambda / 2)
        val h = sinDPhi * sinDPhi + cos(p1) * cos(p2) * sinDLambda * sinDLambda
        return 2 * r * asin(min(1.0, sqrt(h)))
    }

    fun impliedSpeedKmh(a: String, b: String, seconds: Double): Double {
        val s = if (seconds <= 0) 1.0 else seconds
        return haversineKm(a, b) / (s / 3600.0)
    }
}
