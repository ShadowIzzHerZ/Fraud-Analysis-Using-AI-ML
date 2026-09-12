package com.zenpay.app

import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel
import com.google.zxing.qrcode.encoder.Encoder

/** Shared QR-generation helper — used by LocalPortal.kt (merchant payment
 * QRs) and MyQrActivity.kt (a device's own ZenPay ID QR). */
object QrCodes {
    /** Raw QR module grid (with a hand-added quiet-zone border), high error
     * correction so a "SIMULATION" stamp drawn over it in the UI doesn't
     * break scanning. Computed entirely on-device via ZXing — no server, no
     * image library, just a boolean grid the caller draws (see QrView.kt). */
    fun modules(data: String, border: Int = 2): List<List<Boolean>> {
        val code = Encoder.encode(data, ErrorCorrectionLevel.H)
        val m = code.matrix
        val size = m.width
        val total = size + border * 2
        return (0 until total).map { row ->
            (0 until total).map { col ->
                val r = row - border
                val c = col - border
                if (r in 0 until size && c in 0 until size) m.get(c, r).toInt() == 1 else false
            }
        }
    }
}
