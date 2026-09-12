package com.zenpay.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.MotionEvent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraControl
import androidx.camera.core.CameraSelector
import androidx.camera.core.FocusMeteringAction
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.google.zxing.BarcodeFormat
import com.google.zxing.BinaryBitmap
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.NotFoundException
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.Result
import com.google.zxing.common.GlobalHistogramBinarizer
import com.google.zxing.common.HybridBinarizer
import com.zenpay.app.databinding.ActivityScanBinding
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

const val EXTRA_SCANNED_ZENPAY_ID = "zenpay_id"

/**
 * Camera QR scanner for "Scan & Send" — the ONLY thing it ever returns
 * RESULT_OK for is another device's ZenPay ID (QrValidator.kt). A real UPI
 * QR code or anything unrecognized is shown as a rejection banner and
 * scanning continues; there is no path from this screen to paying a real
 * UPI handle.
 */
class ScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivityScanBinding
    private lateinit var cameraExecutor: ExecutorService
    private var cameraControl: CameraControl? = null
    private var cachedRawBuffer: ByteArray? = null
    private var cachedRotatedBuffer: ByteArray? = null

    private val reader = MultiFormatReader().apply {
        setHints(
            mapOf(
                DecodeHintType.POSSIBLE_FORMATS to listOf(BarcodeFormat.QR_CODE),
                DecodeHintType.TRY_HARDER to true,
                DecodeHintType.CHARACTER_SET to "UTF-8",
            )
        )
    }
    private val mainHandler = Handler(Looper.getMainLooper())
    @Volatile private var paused = false

    private val requestCameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startCamera() else {
            android.widget.Toast.makeText(this, "Camera permission is required to scan a QR code.", android.widget.Toast.LENGTH_LONG).show()
            finish()
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)
        cameraExecutor = Executors.newSingleThreadExecutor()

        binding.closeButton.setOnClickListener { finish() }

        binding.manualInputButton.setOnClickListener {
            showManualInputDialog()
        }

        binding.previewView.setOnTouchListener { view, event ->
            if (event.action == MotionEvent.ACTION_UP) {
                val factory = binding.previewView.meteringPointFactory
                val point = factory.createPoint(event.x, event.y)
                val action = FocusMeteringAction.Builder(point).build()
                cameraControl?.startFocusAndMetering(action)
                view.performClick()
            }
            true
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestCameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    private fun showManualInputDialog() {
        val input = android.widget.EditText(this).apply {
            hint = "15-digit ZenPay ID"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            filters = arrayOf(android.text.InputFilter.LengthFilter(19))
            typeface = android.graphics.Typeface.MONOSPACE
        }
        val container = android.widget.FrameLayout(this).apply {
            val pad = (20 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad / 2, pad, pad / 2)
            addView(input)
        }
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Enter ZenPay ID")
            .setMessage("Enter or paste the 15-digit ID of the recipient:")
            .setView(container)
            .setPositiveButton("Continue") { _, _ ->
                val cleanId = input.text.toString().filter { it.isDigit() }
                val myId = UserIdentity.getOrCreate(this)
                if (cleanId.length != 15) {
                    android.widget.Toast.makeText(this, "Please enter a valid 15-digit ID (got ${cleanId.length} digits).", android.widget.Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                if (cleanId == myId) {
                    android.widget.Toast.makeText(this, "You cannot send money to your own ZenPay ID.", android.widget.Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                paused = true
                val intent = Intent().putExtra(EXTRA_SCANNED_ZENPAY_ID, cleanId)
                setResult(RESULT_OK, intent)
                finish()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun startCamera() {
        val providerFuture = ProcessCameraProvider.getInstance(this)
        providerFuture.addListener({
            val provider = providerFuture.get()
            val preview = Preview.Builder().build().also {
                it.surfaceProvider = binding.previewView.surfaceProvider
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(cameraExecutor, ::analyzeFrame) }

            try {
                provider.unbindAll()
                val camera = provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
                cameraControl = camera.cameraControl
            } catch (e: Exception) {
                android.widget.Toast.makeText(this, "Couldn't start the camera: ${e.message}", android.widget.Toast.LENGTH_LONG).show()
                finish()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun extractUprightLuminance(imageProxy: ImageProxy): PlanarYUVLuminanceSource {
        val plane = imageProxy.planes[0]
        val buffer = plane.buffer
        val rowStride = plane.rowStride
        val pixelStride = plane.pixelStride
        val width = imageProxy.width
        val height = imageProxy.height
        val rotation = imageProxy.imageInfo.rotationDegrees

        val rawLen = buffer.remaining()
        var raw = cachedRawBuffer
        if (raw == null || raw.size != rawLen) {
            raw = ByteArray(rawLen)
            cachedRawBuffer = raw
        }
        buffer.get(raw, 0, rawLen)

        val targetLen = width * height
        var rotated = cachedRotatedBuffer
        if (rotated == null || rotated.size != targetLen) {
            rotated = ByteArray(targetLen)
            cachedRotatedBuffer = rotated
        }

        return when (rotation) {
            90 -> {
                // Rotated 90 deg clockwise:
                // (x, y) -> (newX, newY) = (height - 1 - y, x)
                // newWidth = height, newHeight = width
                for (y in 0 until height) {
                    val srcRowOffset = y * rowStride
                    val destCol = height - 1 - y
                    for (x in 0 until width) {
                        rotated[x * height + destCol] = raw[srcRowOffset + x * pixelStride]
                    }
                }
                PlanarYUVLuminanceSource(rotated, height, width, 0, 0, height, width, false)
            }
            180 -> {
                for (y in 0 until height) {
                    val srcRowOffset = y * rowStride
                    val destRowOffset = (height - 1 - y) * width
                    for (x in 0 until width) {
                        rotated[destRowOffset + (width - 1 - x)] = raw[srcRowOffset + x * pixelStride]
                    }
                }
                PlanarYUVLuminanceSource(rotated, width, height, 0, 0, width, height, false)
            }
            270 -> {
                // Rotated 270 deg clockwise:
                // (x, y) -> (newX, newY) = (y, width - 1 - x)
                // newWidth = height, newHeight = width
                for (y in 0 until height) {
                    val srcRowOffset = y * rowStride
                    for (x in 0 until width) {
                        val destY = width - 1 - x
                        rotated[destY * height + y] = raw[srcRowOffset + x * pixelStride]
                    }
                }
                PlanarYUVLuminanceSource(rotated, height, width, 0, 0, height, width, false)
            }
            else -> {
                if (rowStride == width && pixelStride == 1) {
                    PlanarYUVLuminanceSource(raw, width, height, 0, 0, width, height, false)
                } else {
                    for (y in 0 until height) {
                        val srcRowOffset = y * rowStride
                        val destRowOffset = y * width
                        for (x in 0 until width) {
                            rotated[destRowOffset + x] = raw[srcRowOffset + x * pixelStride]
                        }
                    }
                    PlanarYUVLuminanceSource(rotated, width, height, 0, 0, width, height, false)
                }
            }
        }
    }

    private fun decodeSource(source: PlanarYUVLuminanceSource): Result? {
        // 1. HybridBinarizer
        try {
            val bitmap = BinaryBitmap(HybridBinarizer(source))
            return reader.decodeWithState(bitmap)
        } catch (_: NotFoundException) {
        } finally {
            reader.reset()
        }

        // 2. GlobalHistogramBinarizer
        try {
            val bitmap = BinaryBitmap(GlobalHistogramBinarizer(source))
            return reader.decodeWithState(bitmap)
        } catch (_: NotFoundException) {
        } finally {
            reader.reset()
        }

        // 3. Inverted HybridBinarizer (for dark backgrounds or screen reflections)
        try {
            val bitmap = BinaryBitmap(HybridBinarizer(source.invert()))
            return reader.decodeWithState(bitmap)
        } catch (_: NotFoundException) {
        } finally {
            reader.reset()
        }

        return null
    }

    private fun analyzeFrame(imageProxy: ImageProxy) {
        if (paused) {
            imageProxy.close()
            return
        }
        try {
            val source = extractUprightLuminance(imageProxy)
            val result = decodeSource(source)
            if (result != null) {
                Log.i("ZenPayScan", "Decoded QR: ${result.text}")
                onDecoded(result.text)
            }
        } catch (e: Exception) {
            Log.e("ZenPayScan", "Frame exception: ${e::class.java.simpleName}: ${e.message}", e)
        } finally {
            imageProxy.close()
        }
    }

    private fun onDecoded(raw: String) {
        if (paused) return
        Log.i("ZenPayScan", "Classifying scanned text: $raw")
        when (val classified = QrValidator.classify(raw)) {
            is ScanResult.ZenPayUser -> {
                paused = true
                Log.i("ZenPayScan", "Accepted ZenPay user ID: ${classified.id}")
                mainHandler.post {
                    val intent = Intent().putExtra(EXTRA_SCANNED_ZENPAY_ID, classified.id)
                    setResult(RESULT_OK, intent)
                    finish()
                }
            }
            is ScanResult.RealUpi -> showBanner("❌ ${classified.reason}")
            is ScanResult.Unknown -> showBanner("Not a ZenPay QR code — try another.")
        }
    }

    private fun showBanner(message: String) {
        paused = true
        mainHandler.post {
            binding.bannerText.text = message
            binding.bannerText.visibility = android.view.View.VISIBLE
        }
        mainHandler.postDelayed({
            binding.bannerText.visibility = android.view.View.GONE
            paused = false
        }, 2200)
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}

