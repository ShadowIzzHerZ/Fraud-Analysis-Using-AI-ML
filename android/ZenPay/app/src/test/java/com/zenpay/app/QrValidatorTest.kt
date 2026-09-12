package com.zenpay.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class QrValidatorTest {

    @Test
    fun testValidZenPayScheme() {
        val result = QrValidator.classify("zenpay://user/987654321012345")
        assertTrue(result is ScanResult.ZenPayUser)
        assertEquals("987654321012345", (result as ScanResult.ZenPayUser).id)
    }

    @Test
    fun testBare15DigitId() {
        val result = QrValidator.classify("987654321012345")
        assertTrue(result is ScanResult.ZenPayUser)
        assertEquals("987654321012345", (result as ScanResult.ZenPayUser).id)
    }

    @Test
    fun testFakeBankVpa() {
        val result = QrValidator.classify("upi://pay?pa=987654321012345@fakebank&pn=ZenPayDemo")
        assertTrue(result is ScanResult.ZenPayUser)
        assertEquals("987654321012345", (result as ScanResult.ZenPayUser).id)
    }

    @Test
    fun testRealUpiRejected() {
        val result = QrValidator.classify("upi://pay?pa=merchant@icici&pn=Shop")
        assertTrue(result is ScanResult.RealUpi)
    }

    @Test
    fun testRealVpaRejected() {
        val result = QrValidator.classify("john.doe@okaxis")
        assertTrue(result is ScanResult.RealUpi)
    }

    @Test
    fun testUnknownQr() {
        val result = QrValidator.classify("https://example.com/some/link")
        assertTrue(result is ScanResult.Unknown)
    }
}
