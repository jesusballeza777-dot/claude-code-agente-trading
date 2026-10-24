package com.agentetrading.control.model

import org.json.JSONArray
import org.json.JSONObject

/** Lectores de las demás páginas. Mismas reglas que `Parsers`: falta un campo y falla, no se inventa. */
object PageParsers {
    fun limites(json: JSONObject): Limites =
        Limites(
            origen = origen(json),
            editable = json.getBoolean("editable"),
            aviso = json.getString("aviso"),
            vigentes =
                json.getJSONArray("vigentes").objects().map {
                    Limite(it.getString("nombre"), it.getString("valor"), it.getString("techo_plan"), it.getString("unidad"), it.getString("adr"))
                },
            gruposCorrelacionados = json.getJSONArray("grupos_correlacionados").let { groups -> (0 until groups.length()).map { groups.getJSONArray(it).strings() } },
        )

    fun vetos(json: JSONObject): Vetos =
        Vetos(
            origen = origen(json),
            nota = json.getString("nota"),
            vetos = json.getJSONArray("vetos").objects().map { VetoVisto(it.getString("codigo"), it.getString("titulo"), it.getString("explicacion"), it.getInt("veces")) },
        )

    fun calculo(json: JSONObject): Calculo =
        Calculo(
            origen = origen(json),
            motor = json.getString("motor"),
            aprobada = json.getBoolean("aprobada"),
            cantidad = json.getString("cantidad"),
            nocional = json.getString("nocional"),
            riesgoUsd = json.stringOrNull("riesgo_usd"),
            presupuestoUsd = json.getString("presupuesto_usd"),
            apalancamientoEfectivo = json.stringOrNull("apalancamiento_efectivo"),
            precioLiquidacion = json.stringOrNull("precio_liquidacion"),
            comision = json.getJSONObject("costes").getString("comision"),
            slippage = json.getJSONObject("costes").getString("slippage"),
            vetos = json.getJSONArray("vetos").objects().map { VetoMotivo(it.getString("code"), it.getString("title"), it.getString("message")) },
        )

    fun decisiones(json: JSONObject): Decisiones =
        Decisiones(
            origen = origen(json),
            vacio = json.getString("vacio"),
            decisiones =
                json.getJSONArray("decisiones").objects().map {
                    DecisionVista(
                        t = it.getString("t"),
                        accion = it.getString("accion"),
                        nivel = it.getString("nivel"),
                        motivo = it.getString("motivo"),
                        evidencia = it.getJSONArray("evidencia").strings(),
                        veto = it.stringOrNull("veto"),
                        json = it.getJSONObject("json").toString(2),
                    )
                },
            libros =
                json.getJSONArray("libros").objects().map {
                    Libro(it.getString("libro"), it.getInt("operaciones"), if (it.isNull("esperanza_r")) null else it.getDouble("esperanza_r"))
                },
        )

    fun diario(json: JSONObject): Diario =
        Diario(
            origen = origen(json),
            aviso = json.getString("aviso"),
            vacio = json.getString("vacio"),
            operaciones =
                json.getJSONArray("operaciones").objects().map {
                    Operacion(
                        id = it.getString("id"),
                        hipotesis = it.getString("hipotesis"),
                        simbolo = it.getString("simbolo"),
                        lado = it.getString("lado"),
                        entrada = it.getString("entrada"),
                        precioEntrada = it.getString("precio_entrada"),
                        precioSalida = it.getString("precio_salida"),
                        motivoSalida = it.getString("motivo_salida"),
                        pnl = it.getString("pnl"),
                        r = it.getDouble("r"),
                        regimen = it.getString("regimen"),
                    )
                },
            notas = json.getJSONArray("notas").objects().map { nota(it) },
        )

    fun nota(json: JSONObject): Nota = Nota(json.getString("id"), json.getString("fecha_utc"), json.getString("referencia"), json.getString("texto"))

    fun proyecto(json: JSONObject): Proyecto {
        val costes = json.getJSONObject("costes")
        val cambio = costes.getJSONObject("tipo_de_cambio")
        val usoApi = costes.getJSONObject("uso_api_claude")
        return Proyecto(
            origen = origen(json),
            fases = json.getJSONArray("fases").objects().map { Fase(it.getString("id"), it.getString("nombre"), it.getString("estado")) },
            adr = json.getJSONArray("adr").objects().map { Adr(it.getString("id"), it.getString("titulo"), it.getString("estado")) },
            riesgos = json.getJSONArray("riesgos").objects().map { Riesgo(it.getString("id"), it.getString("riesgo"), it.getString("probabilidad"), it.getString("impacto")) },
            pendientes = json.getJSONArray("pendientes_propietario").objects().map { Pendiente(it.getString("tarea"), it.getString("documento")) },
            costes = costes.getJSONArray("conceptos").objects().map { Costo(it.getString("concepto"), it.getString("usd_mes"), it.getString("estado")) },
            mxnPorUsd = cambio.getString("mxn_por_usd"),
            estadoTipoCambio = cambio.getString("estado"),
            usoApiOrigen = origen(usoApi),
            usoApiNota = usoApi.getString("nota"),
        )
    }

    fun reportes(json: JSONObject): Reportes =
        Reportes(
            origen = origen(json),
            tipos = json.getJSONArray("reportes").objects().map { TipoReporte(it.getString("tipo"), it.getString("formato"), it.getString("nombre")) },
            historial =
                json.getJSONArray("historial").objects().map {
                    ReporteGenerado(it.getString("fecha_utc"), it.getString("tipo"), it.getString("formato"), it.getString("archivo"), it.getBoolean("demo"))
                },
        )

    private fun origen(json: JSONObject): Origen =
        when (json.getString("origen")) {
            "real" -> Origen.REAL
            "backtest" -> Origen.BACKTEST
            else -> Origen.DEMO // lo desconocido se trata como demostración, nunca como real
        }

    /** `JSONObject.optString` devolvería la palabra "null" para un null del JSON: aquí es un null de verdad. */
    private fun JSONObject.stringOrNull(key: String): String? = if (isNull(key)) null else getString(key)

    private fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }

    private fun JSONArray.strings(): List<String> = (0 until length()).map { getString(it) }
}
