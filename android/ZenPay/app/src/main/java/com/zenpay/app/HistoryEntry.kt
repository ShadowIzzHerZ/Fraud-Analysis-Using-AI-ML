package com.zenpay.app

import org.json.JSONObject

/** One past simulated payment, as shown on the History screen. `incoming`
 * defaults to false (a card payment or an outgoing send, the only two kinds
 * that used to exist) — money credited by ANOTHER device's transfer is the
 * one case where it's true (see MainActivity's incoming-transfer poll). */
data class HistoryEntry(
    val txnId: String,
    val ts: Long, // epoch millis
    val payee: String,
    val amount: Double,
    val vpa: String,
    val score: Double,
    val severity: String,
    val outcome: String,
    val suspicious: Boolean,
    val incoming: Boolean = false,
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("txnId", txnId)
        put("ts", ts)
        put("payee", payee)
        put("amount", amount)
        put("vpa", vpa)
        put("score", score)
        put("severity", severity)
        put("outcome", outcome)
        put("suspicious", suspicious)
        put("incoming", incoming)
    }

    companion object {
        fun fromJson(o: JSONObject): HistoryEntry = HistoryEntry(
            txnId = o.optString("txnId"),
            ts = o.optLong("ts"),
            payee = o.optString("payee"),
            amount = o.optDouble("amount"),
            vpa = o.optString("vpa"),
            score = o.optDouble("score"),
            severity = o.optString("severity"),
            outcome = o.optString("outcome"),
            suspicious = o.optBoolean("suspicious"),
            incoming = o.optBoolean("incoming", false),
        )
    }
}
