package com.zenpay.app

import kotlin.math.min

data class Reason(val detector: String, val text: String)

data class ScoreResult(
    val riskScore: Double,
    val severity: String, // low | medium | high | critical
    val reasons: List<Reason>,
)

/**
 * On-device fraud-detection engine — a straight port of the interesting
 * parts of the Python backend's app/scoring.py (AMOUNT, VELOCITY, GEO_JUMP,
 * NEW_DEVICE; MULE_BURST and UNUSUAL_MCC are omitted as out of scope for a
 * single-payment demo flow), so ZenPay can score a simulated payment
 * with zero network call. Same weights, same thresholds, same explainable-
 * reasons-not-a-black-box philosophy.
 */
object FraudScorer {

    private const val VELOCITY_WINDOW_S = 60.0

    fun score(amount: Double, deviceFp: String, country: String, ts: Double, profile: CardProfile): ScoreResult {
        val hits = mutableListOf<Pair<Double, Reason>>()

        detectAmountOutlier(amount, profile)?.let { hits.add(it) }
        detectVelocity(ts, profile)?.let { hits.add(it) }
        detectGeoJump(country, ts, profile)?.let { hits.add(it) }
        detectNewDevice(amount, deviceFp, profile)?.let { hits.add(it) }

        hits.sortByDescending { it.first }
        val total = min(1.0, hits.sumOf { it.first })
        return ScoreResult(
            riskScore = total,
            severity = severityFor(total),
            reasons = hits.take(4).map { it.second },
        )
    }

    private fun severityFor(score: Double): String = when {
        score >= 0.85 -> "critical"
        score >= 0.65 -> "high"
        score >= 0.40 -> "medium"
        else -> "low"
    }

    private fun detectAmountOutlier(amount: Double, profile: CardProfile): Pair<Double, Reason>? {
        if (profile.n < 5) {
            if (amount >= 15000) {
                return 0.20 to Reason("AMOUNT", "Large amount (₹${"%,.0f".format(amount)}) with little or no history on this card")
            }
            return null
        }
        val z = profile.amountZscore(amount)
        val w = when {
            z >= 3.6 -> 0.45
            z >= 2.9 -> 0.30
            z >= 2.3 -> 0.18
            else -> return null
        }
        return w to Reason("AMOUNT", "Amount ₹${"%,.0f".format(amount)} is well above this card's usual range (avg ₹${"%,.0f".format(profile.meanAmount)})")
    }

    private fun detectVelocity(ts: Double, profile: CardProfile): Pair<Double, Reason>? {
        val count = profile.recentTxnTimes.count { it >= ts - VELOCITY_WINDOW_S } + 1
        val w = when {
            count >= 9 -> 0.55
            count >= 7 -> 0.40
            count >= 5 -> 0.18
            else -> return null
        }
        return w to Reason("VELOCITY", "$count transactions on this card in the last ${VELOCITY_WINDOW_S.toInt()}s")
    }

    private fun detectGeoJump(country: String, ts: Double, profile: CardProfile): Pair<Double, Reason>? {
        val last = profile.lastCountry ?: return null
        val lastTs = profile.lastTs ?: return null
        if (last == country) return null
        val dt = maxOf(1.0, ts - lastTs)
        val speed = Geo.impliedSpeedKmh(last, country, dt)
        if (speed <= Geo.MAX_PLAUSIBLE_KMH) return null
        val dist = Geo.haversineKm(last, country)
        return 0.50 to Reason("GEO_JUMP", "$last→$country (${"%,.0f".format(dist)} km) in ${"%.0f".format(dt)}s — implies ${"%,.0f".format(speed)} km/h")
    }

    private fun detectNewDevice(amount: Double, deviceFp: String, profile: CardProfile): Pair<Double, Reason>? {
        if (profile.n < 3 || profile.seenDevices.contains(deviceFp)) return null
        val relative = amount / maxOf(profile.meanAmount, 1e-6)
        if (relative < 2.5 && amount < 3000) return null
        return 0.25 to Reason("NEW_DEVICE", "Unrecognized device for this card, amount ₹${"%,.0f".format(amount)} (avg ₹${"%,.0f".format(profile.meanAmount)})")
    }
}
