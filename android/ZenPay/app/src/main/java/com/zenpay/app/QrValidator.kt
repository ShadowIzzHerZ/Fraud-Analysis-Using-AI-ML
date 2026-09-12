package com.zenpay.app

/** What a scanned QR code turned out to be. */
sealed class ScanResult {
    data class ZenPayUser(val id: String) : ScanResult()
    data class RealUpi(val reason: String) : ScanResult()
    data class Unknown(val raw: String) : ScanResult()
}

/**
 * Classifies whatever the camera decoded — the entire point of the scanner
 * (see ScanActivity.kt): it must accept ONLY another device's ZenPay ID
 * (UserIdentity.kt's 15-digit format, optionally wrapped in the
 * `zenpay://user/<id>` scheme MyQrActivity.kt encodes) and must actively
 * reject anything that looks like a real UPI QR code — a real `upi://`
 * deep link, or a bare `name@bank` VPA — rather than silently "succeeding"
 * against it. There is no path from a real UPI QR to a send flow here.
 */
object QrValidator {
    private val ZENPAY_SCHEME = Regex("""zenpay://user/(\d{15})""")
    private val BARE_ID = Regex("""\b(\d{15})\b""")
    private val VPA_LIKE = Regex("""^[\w.\-]{2,}@[\w.\-]{2,}$""")

    fun classify(raw: String): ScanResult {
        val text = raw.trim()

        ZENPAY_SCHEME.find(text)?.let { return ScanResult.ZenPayUser(it.groupValues[1]) }
        BARE_ID.find(text)?.let { return ScanResult.ZenPayUser(it.groupValues[1]) }

        if (text.contains("@fakebank", ignoreCase = true)) {
            val digits = text.filter { it.isDigit() }
            if (digits.length >= 15) {
                return ScanResult.ZenPayUser(digits.take(15))
            }
        }

        if (text.startsWith("upi://", ignoreCase = true)) {
            return ScanResult.RealUpi("This is a real UPI payment QR code. ZenPay only sends simulated money to another ZenPay user's ID — it can't pay a real UPI handle.")
        }
        if (VPA_LIKE.matches(text) && !text.endsWith("@fakebank", ignoreCase = true)) {
            return ScanResult.RealUpi("This looks like a real UPI ID ($text). ZenPay only sends simulated money to another ZenPay user's ID.")
        }

        return ScanResult.Unknown(text)
    }
}
