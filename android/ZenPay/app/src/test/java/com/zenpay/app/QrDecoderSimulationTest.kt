package com.zenpay.app

import com.google.zxing.BarcodeFormat
import com.google.zxing.BinaryBitmap
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.common.HybridBinarizer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class QrDecoderSimulationTest {

    @Test
    fun testSimulatedRotatedCameraFrame() {
        val qrText = "zenpay://user/123456789012345"
        val modules = QrCodes.modules(qrText, border = 4)
        val qrSize = modules.size
        val scale = 8
        val uprightW = qrSize * scale
        val uprightH = qrSize * scale

        // Upright target image:
        val upright = ByteArray(uprightW * uprightH)
        for (r in 0 until uprightH) {
            val modRow = r / scale
            for (c in 0 until uprightW) {
                val modCol = c / scale
                val isDark = modules[modRow][modCol]
                upright[r * uprightW + c] = if (isDark) 0.toByte() else 255.toByte()
            }
        }

        // Camera frame: width = uprightH, height = uprightW, rotated 90 deg relative to upright
        val sensorW = uprightH
        val sensorH = uprightW
        val stride = sensorW + 48 // simulate unaligned row stride
        val sensorBuffer = ByteArray(sensorH * stride)

        // Populate sensorBuffer so that applying 90 deg clockwise rotation reproduces upright:
        // Rotation formula: rotated[x * sensorH + (sensorH - 1 - y)] = sensorBuffer[y * stride + x]
        // Since rotated is upright (width = sensorH, height = sensorW):
        // upright[x * sensorH + (sensorH - 1 - y)] = sensorBuffer[y * stride + x]
        for (y in 0 until sensorH) {
            val destCol = sensorH - 1 - y
            for (x in 0 until sensorW) {
                val pixel = upright[x * sensorH + destCol]
                sensorBuffer[y * stride + x] = pixel
            }
        }

        // Execute ScanActivity's exact unpadding & rotation logic:
        val rotated = ByteArray(sensorW * sensorH)
        for (y in 0 until sensorH) {
            val srcRowOffset = y * stride
            val destCol = sensorH - 1 - y
            for (x in 0 until sensorW) {
                rotated[x * sensorH + destCol] = sensorBuffer[srcRowOffset + x]
            }
        }

        // Luminance source dimensions: width = sensorH, height = sensorW
        val source = PlanarYUVLuminanceSource(rotated, sensorH, sensorW, 0, 0, sensorH, sensorW, false)
        val reader = MultiFormatReader().apply {
            setHints(mapOf(
                DecodeHintType.POSSIBLE_FORMATS to listOf(BarcodeFormat.QR_CODE),
                DecodeHintType.TRY_HARDER to true,
                DecodeHintType.CHARACTER_SET to "UTF-8"
            ))
        }

        val bitmap = BinaryBitmap(HybridBinarizer(source))
        val result = reader.decodeWithState(bitmap)

        assertNotNull("ZXing should decode the rotated simulated frame", result)
        assertEquals(qrText, result.text)

        val classification = QrValidator.classify(result.text)
        assertTrue(classification is ScanResult.ZenPayUser)
        assertEquals("123456789012345", (classification as ScanResult.ZenPayUser).id)
    }
}
