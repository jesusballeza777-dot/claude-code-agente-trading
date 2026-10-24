package com.agentetrading.control.model

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LabVerdictTest {
    private val lab =
        LabParsers.laboratorio(
            JSONObject(javaClass.classLoader!!.getResourceAsStream("laboratorio.json")!!.bufferedReader().use { it.readText() }),
        )

    @Test
    fun withTheRealF4ResultsNobodyPassesAndH2IsTheClosest() {
        val text = LabVerdict.text(lab.hipotesis)
        assertTrue(text.startsWith("Ninguna de las 4 hipótesis evaluadas pasa el examen."))
        assertTrue(text.contains("H2-v1 es la que más se acerca: cumple 9 de 10 criterios."))
        assertTrue(text.contains("No es un fracaso"))
    }

    @Test
    fun ifSomeonePassedItSaysTheHoldoutIsStillNeeded() {
        val h2 = lab.hipotesis.first { it.id == "H2-v1" }
        val passing = h2.copy(gate = h2.gate!!.copy(pasa = true))
        val text = LabVerdict.text(listOf(passing))
        assertEquals("1 hipótesis pasan los criterios 1-8. Falta el holdout, que se abre una sola vez y con tu autorización.", text)
    }

    @Test
    fun nothingEvaluatedYet() {
        assertEquals("Aún no hay hipótesis evaluadas.", LabVerdict.text(lab.hipotesis.filter { !it.evaluada }))
    }
}
