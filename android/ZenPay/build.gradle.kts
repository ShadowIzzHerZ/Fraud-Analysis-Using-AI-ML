// ZenPay — the customer-facing test-payment app. Standalone from the Zen
// analyst web console: this is the only place the "make a test UPI payment"
// / QR flow lives (see app/portal.py in the Python repo root for the JSON
// API it talks to).
// AGP 9+ has built-in Kotlin support, so no separate
// org.jetbrains.kotlin.android plugin is needed (or allowed) alongside it.
plugins {
    id("com.android.application") version "9.4.0" apply false
}
