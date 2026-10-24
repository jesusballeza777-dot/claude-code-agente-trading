package com.agentetrading.control.model

/** Modelos del Laboratorio (resultados de la F4) y del Mercado. */

data class Ciclo(val etapa: String, val estado: String)

data class Segmento(val n: Int, val esperanzaR: Double)

data class ResumenLab(
    val operaciones: Int,
    val esperanzaR: Double,
    val ic90Inferior: Double,
    val ic90Superior: Double,
    val pf: Double?,
    val tasaAcierto: Double,
    val porDireccion: Map<String, Segmento>,
    val porRegimen: Map<String, Segmento>,
    val porSemestre: Map<String, Segmento>,
)

data class Criterio(val clave: String, val cumple: Boolean)

/** Valores con los que se evaluó cada criterio. Los que no aplican a una hipótesis son null. */
data class ValoresGate(
    val operaciones: Int?,
    val ic90: Pair<Double, Double>?,
    val pf: Double?,
    val dsr: Double?,
    val pbo: Double?,
    val maxDdP95: Double?,
    val costesIc90: Pair<Double, Double>?,
    val regimenesPositivos: List<String>,
    val maxPesoMes: Double?,
)

data class GateLab(val pasa: Boolean, val criterios: List<Criterio>, val holdout: String?, val valores: ValoresGate?) {
    val cumplidos: Int get() = criterios.count { it.cumple }
}

data class HipotesisLab(
    val id: String,
    val titulo: String,
    val evaluada: Boolean,
    val ciclo: List<Ciclo>,
    val resumen: ResumenLab?,
    val gate: GateLab?,
    val pista: String?,
    val corridas: Int,
)

data class Laboratorio(
    val origen: Origen,
    val hipotesis: List<HipotesisLab>,
    val intentosPrincipales: Int,
    val intentosTotal: Int,
    val explicacionIntentos: String,
)

data class PuntoDd(val t: String, val dd: Double)

data class Barra(val desde: Double, val hasta: Double, val n: Int)

data class MesR(val mes: String, val r: Double)

data class PuntoMc(val operacion: Int, val p5: Double, val p25: Double, val p50: Double, val p75: Double, val p95: Double)

data class VarianteSens(val valor: Double, val esperanzaR: Double, val operaciones: Int)

data class Sensibilidad(val parametro: String, val base: Double, val valores: List<VarianteSens>)

data class DetalleLab(
    val origen: Origen,
    val id: String,
    val titulo: String,
    val trialId: String,
    val parametros: List<Pair<String, String>>,
    val codigoCommit: String,
    val datasetId: String,
    val resumen: ResumenLab,
    val gate: GateLab?,
    val curva: List<PuntoCurva>,
    val underwater: List<PuntoDd>,
    val distribucion: List<Barra>,
    val mapaMensual: List<MesR>,
    val abanico: List<PuntoMc>,
    val sensibilidad: List<Sensibilidad>,
    val vetos: List<VetoVisto>,
)

data class Vela(val t: String, val o: Double, val h: Double, val l: Double, val c: Double)

data class Marcador(val t: String, val tipo: String, val lado: String?, val r: Double?)

data class Funding(val t: String, val tasa8h: Double)

data class Velas(
    val origen: Origen,
    val simbolo: String,
    val intervalo: String,
    val velas: List<Vela>,
    /** Canal de entrada y de salida de H2 (solo velas de 4h); null donde aún no hay historia suficiente. */
    val canalAlto: List<Double?>,
    val canalBajo: List<Double?>,
    val marcadores: List<Marcador>,
    val funding: List<Funding>,
)

data class Tramo(val regimen: String, val desde: String, val hasta: String)

data class Regimenes(val origen: Origen, val tramos: List<Tramo>)

data class Correlaciones(val origen: Origen, val ventana: String, val simbolos: List<String>, val matriz: List<List<Double?>>)

data class Simbolos(val origen: Origen, val simbolos: List<String>)
