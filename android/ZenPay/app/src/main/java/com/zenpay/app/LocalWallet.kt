package com.zenpay.app

import android.content.Context
import java.security.MessageDigest

/** Result of sending fake money to another ZenPay user — mirrors the
 * backend's `TransferResponse` (app/portal.py) shape closely enough that
 * SendMoneyActivity can treat a local-only send and a synced one the same
 * way once the local part has happened. */
data class TransferResult(
    val ok: Boolean,
    val error: String = "",
    val txnId: String = "",
    val toId: String = "",
    val amount: Double = 0.0,
    val score: Double = 0.0,
    val severity: String = "",
    val outcome: String = "",
    val newBalance: Double = 0.0,
)

/**
 * Sends fake money from this device to another ZenPay ID, entirely
 * on-device: debits the local wallet (WalletStore), scores the transfer
 * through the same FraudScorer engine every other ZenPay flow uses (a
 * persistent profile keyed by this device's own ZenPay ID, so repeated
 * sends build velocity/amount history), and returns immediately — no
 * network required. PortalApi's optional sync (MainActivity) may also
 * mirror this to the shared backend afterwards, purely so the *other*
 * device sees the money land; that never blocks or is required for this
 * function to "work."
 */
object LocalWallet {
    private const val HOME_CITY = "Mumbai"

    private fun sha(algorithm: String, input: String): String =
        MessageDigest.getInstance(algorithm).digest(input.toByteArray())
            .joinToString("") { "%02x".format(it) }

    fun send(context: Context, myId: String, toId: String, amount: Double): TransferResult {
        if (toId.length != 15 || !toId.all { it.isDigit() }) {
            return TransferResult(ok = false, error = "Not a valid ZenPay ID.")
        }
        if (toId == myId) {
            return TransferResult(ok = false, error = "Can't send money to yourself.")
        }
        if (amount <= 0.0) {
            return TransferResult(ok = false, error = "Amount must be greater than 0.")
        }

        val wallet = WalletStore(context)
        if (!wallet.debit(amount)) {
            return TransferResult(ok = false, error = "Insufficient balance.")
        }

        val token = "wallet_$myId"
        val store = ProfileStore(context)
        val profile = store.load(token)
        val ts = System.currentTimeMillis() / 1000.0
        val device = "dev_" + myId.take(8)

        val result = FraudScorer.score(amount, device, HOME_CITY, ts, profile)
        profile.observe(amount, device, HOME_CITY, ts)
        store.save(token, profile)

        val outcome = when {
            result.riskScore >= 0.90 -> "Blocked — auto-frozen by fraud policy"
            result.riskScore >= 0.40 -> "Flagged for analyst review"
            else -> "Processed — no risk signals"
        }
        val txnId = "txn_" + sha("SHA-1", "$token$toId$ts$amount").take(10)

        return TransferResult(
            ok = true, txnId = txnId, toId = toId, amount = amount,
            score = result.riskScore, severity = result.severity, outcome = outcome,
            newBalance = wallet.balance(),
        )
    }
}
