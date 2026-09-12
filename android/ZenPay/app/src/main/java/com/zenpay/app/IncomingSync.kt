package com.zenpay.app

import android.content.Context

private const val PREFS = "zenpay_incoming_sync"
private const val KEY_LAST_TS = "last_incoming_ts"

/** Bookmarks how far MainActivity's incoming-transfer poll has already
 * caught up to, so the same credit from another device doesn't get added
 * to HistoryStore twice on every resume. One value is enough — a device
 * only ever has one ZenPay ID (UserIdentity.kt), so there's only ever one
 * incoming feed to track. Stored as a String (like WalletStore's balance),
 * not a Float — a Unix timestamp already has 10 digits before the decimal
 * point, more than a 32-bit float can hold without rounding, which would
 * cause the same transfer to be replayed or a later one to be missed. */
object IncomingSync {
    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun lastSeenTs(context: Context): Double =
        prefs(context).getString(KEY_LAST_TS, null)?.toDoubleOrNull() ?: 0.0

    fun markSeen(context: Context, ts: Double) {
        prefs(context).edit().putString(KEY_LAST_TS, ts.toString()).apply()
    }
}
