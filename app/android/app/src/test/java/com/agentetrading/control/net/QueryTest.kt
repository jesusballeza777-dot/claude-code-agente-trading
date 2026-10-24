package com.agentetrading.control.net

import org.junit.Assert.assertEquals
import org.junit.Test

class QueryTest {
    @Test
    fun encodesUserValues() {
        assertEquals(
            "/api/riesgo/calculadora?simbolo=BTCUSDT&entrada=60%2C000&nota=a%26b%3Dc+d",
            Query.build("/api/riesgo/calculadora", listOf("simbolo" to "BTCUSDT", "entrada" to "60,000", "nota" to "a&b=c d")),
        )
    }

    @Test
    fun noParametersNoQuestionMark() {
        assertEquals("/api/hoy", Query.build("/api/hoy", emptyList()))
    }
}
