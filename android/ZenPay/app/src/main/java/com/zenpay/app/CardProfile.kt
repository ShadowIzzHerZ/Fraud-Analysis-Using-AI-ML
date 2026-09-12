package com.zenpay.app

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Rolling behavioural baseline for one (locally-simulated) test card —
 * on-device port of the Python backend's `CardProfile`
 * (app/state.py) so FraudScorer.kt can run the same detectors with no
 * network call at all. Persisted as JSON via ProfileStore so a card's
 * history survives between app launches.
 */
class CardProfile(
    var n: Int = 0,
    var meanAmount: Double = 0.0,
    var m2: Double = 0.0,
    var meanLog: Double = 0.0,
    var m2Log: Double = 0.0,
    val seenDevices: MutableSet<String> = mutableSetOf(),
    var lastCountry: String? = null,
    var lastTs: Double? = null,
    // (ts, amount) pairs within the last couple of minutes — enough for the
    // velocity detector's 60s window; trimmed on every observe().
    val recentTxnTimes: MutableList<Double> = mutableListOf(),
) {
    val stdLog: Double
        get() = if (n < 2) 0.0 else sqrt(max(0.0, m2Log / (n - 1)))

    fun amountZscore(amount: Double): Double {
        if (n < 5 || stdLog < 1e-6) return 0.0
        return (ln(max(amount, 0.01)) - meanLog) / stdLog
    }

    /** Must be called AFTER scoring reads this profile — baseline reflects
     * strictly prior history only, same ordering the Python backend uses. */
    fun observe(amount: Double, device: String, country: String, ts: Double) {
        n += 1
        val delta = amount - meanAmount
        meanAmount += delta / n
        val delta2 = amount - meanAmount
        m2 += delta * delta2

        val logAmt = ln(max(amount, 0.01))
        val deltaL = logAmt - meanLog
        meanLog += deltaL / n
        val delta2L = logAmt - meanLog
        m2Log += deltaL * delta2L

        seenDevices.add(device)
        lastCountry = country
        lastTs = ts
        recentTxnTimes.add(ts)
        val cutoff = ts - 120.0
        recentTxnTimes.removeAll { it < cutoff }
    }

    fun toJson(): JSONObject = JSONObject().apply {
        put("n", n)
        put("meanAmount", meanAmount)
        put("m2", m2)
        put("meanLog", meanLog)
        put("m2Log", m2Log)
        put("seenDevices", JSONArray(seenDevices.toList()))
        put("lastCountry", lastCountry)
        put("lastTs", lastTs)
        put("recentTxnTimes", JSONArray(recentTxnTimes))
    }

    companion object {
        fun fromJson(o: JSONObject): CardProfile {
            val devices = mutableSetOf<String>()
            o.optJSONArray("seenDevices")?.let { arr -> for (i in 0 until arr.length()) devices.add(arr.getString(i)) }
            val times = mutableListOf<Double>()
            o.optJSONArray("recentTxnTimes")?.let { arr -> for (i in 0 until arr.length()) times.add(arr.getDouble(i)) }
            return CardProfile(
                n = o.optInt("n", 0),
                meanAmount = o.optDouble("meanAmount", 0.0),
                m2 = o.optDouble("m2", 0.0),
                meanLog = o.optDouble("meanLog", 0.0),
                m2Log = o.optDouble("m2Log", 0.0),
                seenDevices = devices,
                lastCountry = if (o.isNull("lastCountry")) null else o.optString("lastCountry"),
                lastTs = if (o.isNull("lastTs")) null else o.optDouble("lastTs"),
                recentTxnTimes = times,
            )
        }
    }
}
