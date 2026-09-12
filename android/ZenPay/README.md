# ZenPay

The customer-facing test-payment app for the RiskPulse fraud-detection demo.
Standalone from the Zen/RiskPulse analyst web console (`../../app/`) — this
is the only place the "make a test UPI payment" / QR flow lives; the
analyst console has no QR or payment UI at all.

## It works fully offline

Everything happens on-device, with no network call required:

- **Card check** — `LocalPortal.kt` validates against a short allowlist of
  published sandbox test-card numbers (`TestCards.kt`), Luhn-checked. No
  real card number is ever accepted, and nothing here could charge one even
  if it were.
- **Fraud scoring** — `FraudScorer.kt` + `CardProfile.kt` are a Kotlin port
  of the Python backend's detection engine (`../../app/scoring.py`): the
  same AMOUNT/VELOCITY/GEO_JUMP/NEW_DEVICE detectors, same weights, same
  thresholds, running against a per-test-card profile persisted locally
  (`ProfileStore.kt`) so repeated use of the same test card builds up
  history exactly like the server version does.
- **QR generation** — `LocalPortal.kt` builds a standard `upi://pay?...`
  deep link and renders it via ZXing's QR encoder (`QrView.kt` draws the
  raw module grid directly, no image library needed).
- **History** — every simulated payment is saved locally
  (`HistoryStore.kt`) and shown on the History screen and the home
  screen's "Recent activity" preview. This is the app's only record of past
  transactions; nothing is fetched from a server.

The payee handle on every generated QR is `sim.<hash>@fakebank` —
`@fakebank` is not an NPCI-registered PSP suffix, so no real UPI app can
resolve it or move money through it, regardless of what card or amount you
enter.

## Bonus: sync to the analyst console when reachable

Settings has a "Sync test payments to analyst console" toggle — **on by
default**, but purely opportunistic. After every payment, the app tries a
best-effort, fire-and-forget `POST /api/portal/pay` to the Python backend
(`../../app/portal.py`) so the analyst dashboard can show it live too; if
the backend isn't reachable, the attempt just silently fails with no error
shown. This never blocks, delays, or is required for a payment to work in
this app — turn it off in Settings if you'd rather it never even try.

To use it: run the backend (`python main.py` in the repo root) and either
put your phone on the same Wi-Fi network as that machine (set the Settings
URL to that machine's LAN IP, e.g. `http://10.0.0.5:8080`), or tunnel over
USB with `adb reverse tcp:8080 tcp:8080` and use `http://127.0.0.1:8080`.
Use **Test Connection** in Settings to check reachability before relying on
it.

## Building and installing

```bash
cd android/ZenPay
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Requires a connected device or emulator with USB debugging enabled for
`adb install`; once installed, the app itself needs no cable and no Wi-Fi.

## Stack

Kotlin, plain Android views (no Compose), AGP 9 / Gradle 9.7 with AGP's
built-in Kotlin support (no separate `org.jetbrains.kotlin.android` plugin).
ZXing (`com.google.zxing:core`) for QR encoding, OkHttp for the optional
sync call only. No Room, no DI framework — SharedPreferences-backed JSON is
enough for a card profile and a payment history that only ever need to
answer "what did this device do."
