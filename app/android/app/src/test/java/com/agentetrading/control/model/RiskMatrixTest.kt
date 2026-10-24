package com.agentetrading.control.model

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RiskMatrixTest {
    private val riesgos =
        PageParsers.proyecto(
            JSONObject(javaClass.classLoader!!.getResourceAsStream("proyecto.json")!!.bufferedReader().use { it.readText() }),
        ).riesgos

    @Test
    fun feminineProbabilityAndMasculineImpactMapToTheSameScale() {
        assertEquals(0, RiskMatrix.level("Baja"))
        assertEquals(0, RiskMatrix.level("Bajo"))
        assertEquals(1, RiskMatrix.level("Media"))
        assertEquals(1, RiskMatrix.level("Medio"))
        assertEquals(2, RiskMatrix.level("Alta"))
        assertEquals(2, RiskMatrix.level("Alto"))
        assertEquals(2, RiskMatrix.level("Alta (estimada)"))
        assertEquals(-1, RiskMatrix.level("Ocurrido"))
    }

    @Test
    fun everyRiskIsPlacedOrListedOutsideNeverDropped() {
        val matrix = RiskMatrix.build(riesgos)
        val placed = matrix.cells.sumOf { row -> row.sumOf { it.size } }
        assertEquals(riesgos.size, placed + matrix.outside.size)
        assertTrue(matrix.cells.size == 3 && matrix.cells.all { it.size == 3 })
        // Un riesgo ya ocurrido (R06) no tiene probabilidad: va fuera de la matriz y se avisa.
        assertTrue(matrix.outside.any { it.id == "R06" })
        // R01: probabilidad alta e impacto alto, arriba a la derecha.
        assertTrue(matrix.cells[0][2].any { it.id == "R01" })
    }
}
