package com.agentetrading.control.format

import com.agentetrading.control.model.LimitUnit
import org.junit.Assert.assertEquals
import org.junit.Test

class FormatTest {
    @Test
    fun usdShowsSignAndThousands() {
        assertEquals("$1,500.00", Format.usd(1500.0))
        assertEquals("-$6.80", Format.usd(-6.8))
        assertEquals("—", Format.usd(null))
    }

    @Test
    fun rShowsExplicitSign() {
        assertEquals("+0.93 R", Format.r(0.9333))
        assertEquals("-1.50 R", Format.r(-1.5))
        assertEquals("—", Format.r(null))
    }

    @Test
    fun limitsUseTheirUnit() {
        assertEquals("15.0%", Format.limit(0.15, LimitUnit.PERCENT))
        assertEquals("2.00x", Format.limit(2.0, LimitUnit.MULTIPLE))
    }

    @Test
    fun usageIsClampedToTheBar() {
        assertEquals(0.5f, Format.usage(0.01, 0.02), 1e-6f)
        assertEquals(1f, Format.usage(0.05, 0.02), 0f)
        assertEquals(0f, Format.usage(-1.0, 0.02), 0f)
        assertEquals(1f, Format.usage(0.0, 0.0), 0f)
    }
}
