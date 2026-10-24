package com.agentetrading.control

import org.junit.Assert.assertEquals
import org.junit.Test

class FormatTest {
    @Test
    fun usdGroupsThousandsAndRoundsToCents() {
        assertEquals("USD 1,500.34", Format.usd("1500.34"))
        assertEquals("USD 1,524.08", Format.usd("1524.075"))
        assertEquals("USD 0.00", Format.usd("0"))
        assertEquals("—", Format.usd("no es número"))
    }

    @Test
    fun percentages() {
        assertEquals("1.75%", Format.pct(0.017469313771204618))
        assertEquals("15%", Format.pct(0.15, 0))
        assertEquals("99.88%", Format.pctOf(0.998767))
        assertEquals("—", Format.pctOf(null))
    }

    @Test
    fun dateTime() {
        assertEquals("2026-10-06 20:00 UTC", Format.fechaHora("2026-10-06T20:00:00+00:00"))
        assertEquals("2026-10-06 20:00 UTC", Format.fechaHora("2026-10-06T20:00:00Z"))
        assertEquals("ayer", Format.fechaHora("ayer"))
    }

    @Test
    fun elapsed() {
        assertEquals("ahora mismo", Format.ago(1_000, 3_000))
        assertEquals("hace 12 s", Format.ago(0, 12_000))
        assertEquals("hace 3 min", Format.ago(0, 200_000))
        assertEquals("ahora mismo", Format.ago(10_000, 5_000)) // reloj atrasado: nunca negativo
    }
}
