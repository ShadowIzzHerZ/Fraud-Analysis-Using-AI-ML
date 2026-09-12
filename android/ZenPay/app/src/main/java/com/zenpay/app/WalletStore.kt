package com.zenpay.app

import android.content.Context

private const val PREFS = "zenpay_wallet"
private const val KEY_BALANCE = "balance"
const val DEFAULT_WALLET_BALANCE = 100_000.0

/**
 * This device's local fake-money balance — offline-first, same as
 * everything else in ZenPay: it works with zero network. When "sync to
 * analyst console" is on and the backend is reachable, MainActivity treats
 * the server's `/api/portal/wallet/{id}` balance as authoritative and
 * overwrites this local mirror (so a transfer from another synced device
 * actually shows up here); otherwise this local value is all there is,
 * and only reflects money *this* device has sent.
 */
class WalletStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun balance(): Double = prefs.getString(KEY_BALANCE, null)?.toDoubleOrNull() ?: DEFAULT_WALLET_BALANCE

    /** Returns false (no-op) if the balance can't cover it. */
    fun debit(amount: Double): Boolean {
        val current = balance()
        if (amount > current) return false
        set(current - amount)
        return true
    }

    fun set(newBalance: Double) {
        prefs.edit().putString(KEY_BALANCE, newBalance.toString()).apply()
    }

    fun reset() = set(DEFAULT_WALLET_BALANCE)
}
