package com.zenpay.app

/**
 * Published sandbox test-card numbers (Stripe/Razorpay/PayPal test-mode
 * docs) — Luhn-valid but never issued to a real cardholder. This list is
 * only for the "fill example" chips; the actual allowlist that's *enforced*
 * lives server-side in app/portal.py's TEST_CARDS — keep the two in sync if
 * you ever add/remove one.
 */
val TEST_CARDS: List<Pair<String, String>> = listOf(
    "4242424242424242" to "Visa (test)",
    "4111111111111111" to "Visa (test)",
    "5555555555554444" to "Mastercard (test)",
    "5105105105105100" to "Mastercard (test)",
    "378282246310005" to "American Express (test)",
    "371449635398431" to "American Express (test)",
    "6011111111111117" to "Discover (test)",
)

/** Mirrors app/portal.py's PAYEES keys (mcc mapping is server-side only) —
 * a spread of everyday purchase categories, not just one or two. */
val PAYEES: List<String> = listOf(
    "ZenPay Demo Kirana Store",
    "ZenPay Demo Electronics Bazaar",
    "ZenPay Demo Travel Co.",
    "ZenPay Demo Subscription",
    "ZenPay Demo Chai Tapri Café",
    "ZenPay Demo Petrol Pump",
    "ZenPay Demo Fashion Hub",
    "ZenPay Demo Pharmacy",
    "ZenPay Demo Home & Decor",
    "ZenPay Demo Cinema",
    "ZenPay Demo RideNow Cabs",
    "ZenPay Demo Jewellers",
    "ZenPay Demo Online Mart",
    "ZenPay Demo Hotel Stay",
)

fun formatCardNumber(pan: String): String =
    pan.chunked(4).joinToString(" ")
