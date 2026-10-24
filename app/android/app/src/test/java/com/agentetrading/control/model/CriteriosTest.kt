package com.agentetrading.control.model

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CriteriosTest {
    private val valores =
        LabParsers.detalle(JSONObject(javaClass.classLoader!!.getResourceAsStream("laboratorio-h2.json")!!.bufferedReader().use { it.readText() }))
            .gate!!.valores

    @Test
    fun readableNames() {
        assertEquals("PBO ≤ 0.30", Criterios.texto("4b_pbo_<=0.30").nombre)
        assertTrue(Criterios.texto("4b_pbo_<=0.30").explica.isNotEmpty())
    }

    @Test
    fun unknownCriteriaAreShownByTheirCodeNeverHidden() {
        assertEquals("zz_nuevo", Criterios.texto("zz_nuevo").nombre)
    }

    @Test
    fun valuesAreFormattedLikeTheWeb() {
        assertEquals("272", Criterios.valor("1_operaciones_>=200", valores))
        assertEquals("0.456", Criterios.valor("4b_pbo_<=0.30", valores))
        assertEquals("0.992", Criterios.valor("4a_dsr_>=0.90", valores))
        assertEquals("1.86", Criterios.valor("3_pf_>=1.25", valores))
        assertEquals("19.2%", Criterios.valor("5_maxdd_p95_mc_<=25%", valores))
        assertTrue(Criterios.valor("2_ic90_inferior_>0", valores).startsWith("[+0.21 R"))
        assertEquals("23.8%", Criterios.valor("8_ningun_mes_>30%", valores))
        assertEquals("", Criterios.valor("6a_parametros_±20%_esperanza_>0", valores))
        assertEquals("", Criterios.valor("1_operaciones_>=200", null))
    }
}
