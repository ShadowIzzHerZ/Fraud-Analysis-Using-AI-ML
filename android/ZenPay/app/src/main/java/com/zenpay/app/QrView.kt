package com.zenpay.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View

/**
 * Draws a QR code straight from the module grid the backend returns
 * (app/portal.py's `_qr_matrix`) — no bitmap/image decoding needed, just
 * boolean cells rendered as squares. Keeps this app dependency-free for QR
 * generation entirely; the server is the only place that runs the `qrcode`
 * library, and even there only to compute the grid, never an image.
 */
class QrView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private var modules: List<List<Boolean>> = emptyList()
    private val darkPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.BLACK }
    private val lightPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }

    fun setModules(grid: List<List<Boolean>>) {
        modules = grid
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val size = modules.size
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), lightPaint)
        if (size == 0) return

        val cell = minOf(width, height).toFloat() / size
        val xOffset = (width - cell * size) / 2f
        val yOffset = (height - cell * size) / 2f

        for (row in 0 until size) {
            val cols = modules[row]
            for (col in cols.indices) {
                if (!cols[col]) continue
                val left = xOffset + col * cell
                val top = yOffset + row * cell
                canvas.drawRect(left, top, left + cell + 0.5f, top + cell + 0.5f, darkPaint)
            }
        }
    }
}
