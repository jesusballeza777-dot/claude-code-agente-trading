package com.agentetrading.control.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RegimeTimelineTest {
    @Test
    fun segmentsAreProportionalToTheirDaysAndAddUpToOne() {
        val tramos =
            listOf(
                Tramo("sin etiqueta", "2019-01-01", "2019-12-31"), // anterior al periodo: se omite
                Tramo("alcista", "2020-01-01", "2020-01-10"), // 10 días
                Tramo("bajista", "2020-01-11", "2020-01-30"), // 20 días
            )
        val segments = RegimeTimeline.segments(tramos)
        assertEquals(listOf("alcista", "bajista"), segments.map { it.regimen })
        assertEquals(1.0 / 3, segments[0].share, 1e-9)
        assertEquals(1.0, segments.sumOf { it.share }, 1e-9)
    }

    @Test
    fun nothingToShowIsAnEmptyListNotADivisionByZero() {
        assertTrue(RegimeTimeline.segments(emptyList()).isEmpty())
        assertTrue(RegimeTimeline.segments(listOf(Tramo("alcista", "2018-01-01", "2018-02-01"))).isEmpty())
    }
}
