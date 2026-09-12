// ZenPay — customer-facing test-payment app (part of the RiskPulse/Zen
// fraud-detection demo).
//
// Talks to app/portal.py's JSON API in the Python backend (running via
// `python main.py` in the repo root) only for the optional analyst-console
// sync — the core payment flow (LocalPortal.kt) runs entirely on-device.
// Ships nothing resembling a real payment: card numbers are checked against
// a short allowlist of published sandbox test PANs, and every generated QR
// encodes a payee handle that cannot resolve on the real UPI network — see
// app/portal.py's module docstring for the full rationale.
plugins {
    id("com.android.application")
}

android {
    namespace = "com.zenpay.app"
    compileSdk = 36 // CameraX 1.6.x's camera-core/camera2/view need API 36+

    defaultConfig {
        applicationId = "com.zenpay.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Card entry, fraud scoring, and QR generation all run on-device (see
    // LocalPortal.kt) — the app never needs the Python backend to function.
    // ZXing's core module (no Android/AWT dependencies) generates the QR
    // module grid; okhttp is only used for the optional, best-effort
    // "sync to analyst console" toggle in Settings.
    implementation("com.google.zxing:core:3.5.3")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")

    // Camera preview + frame analysis for the QR scanner (ScanActivity) —
    // paired with zxing-core (already a dependency above) to decode frames,
    // instead of pulling in the unmaintained zxing-android-embedded wrapper.
    val cameraxVersion = "1.6.2"
    implementation("androidx.camera:camera-core:$cameraxVersion")
    implementation("androidx.camera:camera-camera2:$cameraxVersion")
    implementation("androidx.camera:camera-lifecycle:$cameraxVersion")
    implementation("androidx.camera:camera-view:$cameraxVersion")

    // Custom Tabs for the Google sign-in flow (AuthClient.kt) — opens the
    // same Supabase-fronted Google OAuth consent screen the web app uses,
    // in the device's real browser (so saved Google sessions/passkeys work),
    // rather than a WebView.
    implementation("androidx.browser:browser:1.8.0")

    testImplementation("junit:junit:4.13.2")
}
