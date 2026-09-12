package com.zenpay.app

import android.content.Context
import java.security.MessageDigest
import kotlin.random.Random

/**
 * Everything ZenPay needs to simulate one test payment, entirely
 * on-device: card validation, fake-VPA/QR generation, and fraud scoring
 * (FraudScorer.kt, backed by a persisted CardProfile per test card). No
 * network call — this app never depends on the Python backend to function;
 * see PortalApi.kt for the separate, optional "sync to analyst console"
 * path, which mirrors a completed local result there best-effort.
 *
 * SIMULATION ONLY, same guarantees as the (now-retired) HTML portal and its
 * app/portal.py backend counterpart:
 *   - Card numbers are checked against `TEST_CARDS`, published sandbox PANs
 *     (Stripe/Razorpay/PayPal test-mode docs), Luhn-valid but never issued
 *     to a real cardholder. Anything else is rejected outright.
 *   - The QR encodes a standard `upi://pay?...` deep link, but the payee
 *     handle is `sim.<hash>@fakebank` — `@fakebank` is not an NPCI-
 *     registered PSP suffix, so no real UPI app can resolve it or move
 *     money through it.
 *   - There is no HTTP call, no SDK, nothing here that talks to a bank,
 *     card network, or NPCI/UPI switch.
 */
object LocalPortal {

    private val TEST_CARD_MAP: Map<String, String> = TEST_CARDS.toMap()
    private const val HOME_CITY = "Mumbai"

    private fun luhnOk(digits: String): Boolean {
        if (digits.length < 12 || !digits.all { it.isDigit() }) return false
        var total = 0
        digits.reversed().forEachIndexed { i, ch ->
            var d = ch - '0'
            if (i % 2 == 1) {
                d *= 2
                if (d > 9) d -= 9
            }
            total += d
        }
        return total % 10 == 0
    }

    private fun sha(algorithm: String, input: String): String =
        MessageDigest.getInstance(algorithm).digest(input.toByteArray())
            .joinToString("") { "%02x".format(it) }

    private fun fakeVpa(pan: String): String = "sim.${sha("SHA-256", pan).take(10)}@fakebank"

    private fun cardToken(pan: String): String = "test_" + sha("SHA-1", pan).take(12)

    fun pay(context: Context, card: String, amount: Double, payee: String, suspicious: Boolean): PayResult {
        val rawPan = card.filter { it.isDigit() }
        if (!TEST_CARD_MAP.containsKey(rawPan) || !luhnOk(rawPan)) {
            return PayResult(ok = false, error = "Not a recognized test-card number.")
        }
        if (amount <= 0.0) {
            return PayResult(ok = false, error = "Amount must be greater than 0.")
        }
        val payeeName = if (PAYEES.contains(payee)) payee else PAYEES.first()

        val token = cardToken(rawPan)
        val store = ProfileStore(context)
        val profile = store.load(token)
        val ts = System.currentTimeMillis() / 1000.0
        var finalAmount = amount
        val device: String
        val country: String

        if (suspicious) {
            device = "dev_%08x".format(Random.nextLong(0, 1L shl 32))
            val farCities = Geo.CITY_NAMES.filter { it != profile.lastCountry }.ifEmpty { Geo.CITY_NAMES }
            country = farCities.random()
            val baseline = maxOf(profile.meanAmount, amount)
            finalAmount = Math.round((baseline * (8.0 + Random.nextDouble() * 7.0) + (2000.0 + Random.nextDouble() * 4000.0)) * 100) / 100.0
        } else {
            device = "dev_" + token.substring(5, 13)
            country = HOME_CITY
        }

        val result = FraudScorer.score(finalAmount, device, country, ts, profile)
        profile.observe(finalAmount, device, country, ts) // AFTER scoring, same ordering as the Python backend
        store.save(token, profile)

        val outcome = when {
            result.riskScore >= 0.90 -> "Blocked — auto-frozen by fraud policy"
            result.riskScore >= 0.40 -> "Flagged for analyst review"
            else -> "Processed — no risk signals"
        }

        val vpa = fakeVpa(rawPan)
        val amountStr = "%.2f".format(finalAmount)
        val uri = "upi://pay?pa=$vpa&pn=ZENPAY%20SIMULATION%20-%20NOT%20REAL" +
            "&am=$amountStr&cu=INR&tn=ZenPay%20test%20payment%20-%20simulation%20only"

        val txnId = "txn_" + sha("SHA-1", "$token$ts$finalAmount").take(10)

        return PayResult(
            ok = true, txnId = txnId, vpa = vpa, uri = uri, amount = finalAmount, payee = payeeName,
            score = result.riskScore, severity = result.severity, outcome = outcome,
            qrModules = QrCodes.modules(uri),
        )
    }
}
