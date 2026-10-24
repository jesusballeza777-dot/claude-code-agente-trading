package com.agentetrading.control.model

/** Modelos de las páginas Riesgo, Decisiones, Diario, Proyecto, Reportes y Ajustes. */

data class Limite(val nombre: String, val valor: String, val techoPlan: String, val unidad: String, val adr: String) {
    /** El motor entrega fracciones (0.005) o múltiplos (2): se muestran como "0.5%" o "2x". */
    val esFraccion: Boolean get() = unidad == "fracción"
}

data class Limites(val origen: Origen, val editable: Boolean, val aviso: String, val vigentes: List<Limite>, val gruposCorrelacionados: List<List<String>>)

data class VetoMotivo(val codigo: String, val titulo: String, val explicacion: String)

data class VetoVisto(val codigo: String, val titulo: String, val explicacion: String, val veces: Int)

data class Vetos(val origen: Origen, val nota: String, val vetos: List<VetoVisto>)

data class Calculo(
    val origen: Origen,
    val motor: String,
    val aprobada: Boolean,
    /** Cifras como texto decimal tal cual las entrega el motor (nunca se recalculan aquí). */
    val cantidad: String,
    val nocional: String,
    val riesgoUsd: String?,
    val presupuestoUsd: String,
    val apalancamientoEfectivo: String?,
    val precioLiquidacion: String?,
    val comision: String,
    val slippage: String,
    val vetos: List<VetoMotivo>,
)

data class DecisionVista(
    val t: String,
    val accion: String,
    val nivel: String,
    val motivo: String,
    val evidencia: List<String>,
    val veto: String?,
    /** La decisión JSON completa, con sangría, para mostrarla tal cual. */
    val json: String,
)

data class Libro(val libro: String, val operaciones: Int, val esperanzaR: Double?)

data class Decisiones(val origen: Origen, val vacio: String, val decisiones: List<DecisionVista>, val libros: List<Libro>)

data class Operacion(
    val id: String,
    val hipotesis: String,
    val simbolo: String,
    val lado: String,
    val entrada: String,
    val precioEntrada: String,
    val precioSalida: String,
    val motivoSalida: String,
    val pnl: String,
    val r: Double,
    val regimen: String,
)

data class Nota(val id: String, val fechaUtc: String, val referencia: String, val texto: String)

data class Diario(val origen: Origen, val aviso: String, val vacio: String, val operaciones: List<Operacion>, val notas: List<Nota>)

data class Adr(val id: String, val titulo: String, val estado: String)

data class Riesgo(val id: String, val riesgo: String, val probabilidad: String, val impacto: String)

data class Costo(val concepto: String, val usdMes: String, val estado: String)

data class Proyecto(
    val origen: Origen,
    val fases: List<Fase>,
    val adr: List<Adr>,
    val riesgos: List<Riesgo>,
    val pendientes: List<Pendiente>,
    val costes: List<Costo>,
    val mxnPorUsd: String,
    val estadoTipoCambio: String,
    val usoApiOrigen: Origen,
    val usoApiNota: String,
)

data class TipoReporte(val tipo: String, val formato: String, val nombre: String)

data class ReporteGenerado(val fechaUtc: String, val tipo: String, val formato: String, val archivo: String, val demo: Boolean)

data class Reportes(val origen: Origen, val tipos: List<TipoReporte>, val historial: List<ReporteGenerado>)
