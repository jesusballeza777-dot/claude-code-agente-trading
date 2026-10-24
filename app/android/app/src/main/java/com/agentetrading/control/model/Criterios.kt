package com.agentetrading.control.model

import com.agentetrading.control.Format

/** Nombre claro de cada criterio del gate de la F4 y cómo se muestra el valor con el que se evaluó. */
object Criterios {
    class Texto(val nombre: String, val explica: String)

    private val textos =
        mapOf(
            "1_operaciones_>=200" to Texto("≥200 operaciones", "Muestra mínima para que el resultado no sea suerte."),
            "2_ic90_inferior_>0" to Texto("IC90% de la esperanza > 0", "Incluso en el escenario pesimista del rango, gana."),
            "3_pf_>=1.25" to Texto("Profit factor ≥ 1.25", "Gana al menos 1.25 veces lo que pierde."),
            "4a_dsr_>=0.90" to Texto("DSR ≥ 0.90", "El Sharpe sigue siendo bueno después de corregir por todas las pruebas."),
            "4b_pbo_<=0.30" to Texto("PBO ≤ 0.30", "Poca probabilidad de que el resultado dependa de un punto concreto de parámetros."),
            "5_maxdd_p95_mc_<=25%" to Texto("MaxDD p95 ≤ 25%", "En el 95% de las simulaciones la peor caída no pasa del 25%."),
            "6a_parametros_±20%_esperanza_>0" to Texto("Robusta a ±20% en parámetros", "Mover cada parámetro un 20% no la vuelve perdedora."),
            "6b_costes_x1.5_ic90_inferior_>0" to Texto("Aguanta costes ×1.5", "Con comisiones, slippage y funding 50% peores, sigue ganando."),
            "7_positiva_en_>=2_de_3_regimenes" to Texto("Positiva en ≥2 de 3 regímenes", "No depende solo de un tipo de mercado."),
            "8_ningun_mes_>30%" to Texto("Ningún mes > 30% del beneficio", "El resultado no viene de un solo mes afortunado."),
            "h4_k_>=20" to Texto("El filtro quita ≥ 20 entradas", "Con menos, no hay potencia para evaluar el filtro."),
            "h4_mejor_que_base" to Texto("Mejor que la base", "El filtro mejora la estrategia sin filtrar."),
            "h4_mejor_que_p90_aleatorio" to Texto("Mejor que el p90 de filtros al azar", "Mejora más que quitar operaciones al azar."),
        )

    /** Un criterio desconocido se muestra con su código: nunca se oculta. */
    fun texto(clave: String): Texto = textos[clave] ?: Texto(clave, "")

    fun valor(clave: String, v: ValoresGate?): String {
        if (v == null) return ""
        return when (clave) {
            "1_operaciones_>=200" -> v.operaciones?.toString().orEmpty()
            "2_ic90_inferior_>0" -> v.ic90?.let { "[${Format.r(it.first)}, ${Format.r(it.second)}]" }.orEmpty()
            "3_pf_>=1.25" -> v.pf?.let { Format.decimal(it, 2) }.orEmpty()
            "4a_dsr_>=0.90" -> v.dsr?.let { Format.decimal(it, 3) }.orEmpty()
            "4b_pbo_<=0.30" -> v.pbo?.let { Format.decimal(it, 3) }.orEmpty()
            "5_maxdd_p95_mc_<=25%" -> v.maxDdP95?.let { Format.pct(it, 1) }.orEmpty()
            "6b_costes_x1.5_ic90_inferior_>0" -> v.costesIc90?.let { "[${Format.r(it.first)}, ${Format.r(it.second)}]" }.orEmpty()
            "7_positiva_en_>=2_de_3_regimenes" -> v.regimenesPositivos.joinToString(", ").ifEmpty { "ninguno" }
            "8_ningun_mes_>30%" -> v.maxPesoMes?.let { Format.pct(it, 1) } ?: "total ≤ 0"
            else -> ""
        }
    }
}
