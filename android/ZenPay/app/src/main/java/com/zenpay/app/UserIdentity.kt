package com.zenpay.app

import android.content.Context
import java.security.SecureRandom

private const val PREFS = "zenpay_identity"
private const val KEY_ID = "zenpay_id"

/**
 * Each install gets its own random 15-digit "ZenPay ID" the first time this
 * is called — generated once, then persisted forever. It's shaped like an
 * account number so it demos convincingly, but it is NOT a UPI VPA or a
 * bank account: QrValidator.kt only ever accepts this exact shape (15
 * digits, nothing else) as a valid transfer target, and rejects anything
 * that looks like a real `upi://` link or `name@bank` handle.
 */
object UserIdentity {
    private val random = SecureRandom()

    fun getOrCreate(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.getString(KEY_ID, null)?.let { return it }
        val id = generate()
        prefs.edit().putString(KEY_ID, id).apply()
        return id
    }

    private fun generate(): String {
        val first = ('1' + random.nextInt(9)) // never leading zero
        val rest = (1 until 15).map { '0' + random.nextInt(10) }
        return (listOf(first) + rest).joinToString("")
    }
}
