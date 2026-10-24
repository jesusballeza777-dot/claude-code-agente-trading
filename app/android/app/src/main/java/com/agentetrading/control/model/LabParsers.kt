package com.agentetrading.control.model

import org.json.JSONArray
import org.json.JSONObject

/** Lectores del Laboratorio y el Mercado. Falta un campo obligatorio y falla: no se inventa nada. */
object LabParsers {
    fun laboratorio(json: JSONObject): Laboratorio {
        val intentos = json.getJSONObject("intentos")
        return Laboratorio(
            origen = origen(json),
            hipotesis =
                json.getJSONArray("hipotesis").objects().map {
                    HipotesisLab(
                        id = it.getString("id"),
                        titulo = it.getString("titulo"),
                        evaluada = it.getBoolean("evaluada"),
                        ciclo = it.getJSONArray("ciclo").objects().map { c -> Ciclo(c.getString("etapa"), c.getString("estado")) },
                        resumen = if (it.isNull("resumen")) null else resumen(it.getJSONObject("resumen")),
                        gate = if (it.isNull("gate")) null else gate(it.getJSONObject("gate"), "pasa_sin_holdout"),
                        pista = it.stringOrNull("pista"),
                        corridas = it.getInt("corridas"),
                    )
                },
            intentosPrincipales = intentos.getInt("principales"),
            intentosTotal = intentos.getInt("total"),
            explicacionIntentos = intentos.getString("explicacion"),
        )
    }

    fun detalle(json: JSONObject): DetalleLab =
        DetalleLab(
            origen = origen(json),
            id = json.getString("id"),
            titulo = json.getString("titulo"),
            trialId = json.getString("trial_id"),
            parametros = json.getJSONObject("parametros").let { p -> p.keys().asSequence().sorted().map { it to p.get(it).toString() }.toList() },
            codigoCommit = json.getString("codigo_commit"),
            datasetId = json.getString("dataset_id"),
            resumen = resumen(json.getJSONObject("resumen")),
            gate = if (json.isNull("gate")) null else gate(json.getJSONObject("gate"), "pasa_gate_sin_holdout"),
            curva = json.getJSONArray("curva").objects().map { PuntoCurva(it.getString("t"), it.getDouble("capital")) },
            underwater = json.getJSONArray("underwater").objects().map { PuntoDd(it.getString("t"), it.getDouble("dd")) },
            distribucion = json.getJSONArray("distribucion_r").objects().map { Barra(it.getDouble("desde"), it.getDouble("hasta"), it.getInt("n")) },
            mapaMensual = json.getJSONArray("mapa_mensual").objects().map { MesR(it.getString("mes"), it.getDouble("r")) },
            abanico =
                json.getJSONArray("abanico_monte_carlo").objects().map {
                    PuntoMc(it.getInt("operacion"), it.getDouble("p5"), it.getDouble("p25"), it.getDouble("p50"), it.getDouble("p75"), it.getDouble("p95"))
                },
            sensibilidad =
                json.getJSONArray("sensibilidad").objects().map { s ->
                    Sensibilidad(
                        s.getString("parametro"),
                        s.getDouble("base"),
                        s.getJSONArray("valores").objects().map { v -> VarianteSens(v.getDouble("valor"), v.getDouble("esperanza_r"), v.getInt("operaciones")) },
                    )
                },
            vetos = json.getJSONArray("vetos").objects().map { VetoVisto(it.getString("codigo"), it.getString("titulo"), it.getString("explicacion"), it.getInt("veces")) },
        )

    fun simbolos(json: JSONObject): Simbolos = Simbolos(origen(json), json.getJSONArray("simbolos").strings())

    fun velas(json: JSONObject): Velas {
        val indicadores = json.getJSONObject("indicadores")
        return Velas(
            origen = origen(json),
            simbolo = json.getString("simbolo"),
            intervalo = json.getString("intervalo"),
            velas = json.getJSONArray("velas").objects().map { Vela(it.getString("t"), it.getDouble("o"), it.getDouble("h"), it.getDouble("l"), it.getDouble("c")) },
            canalAlto = indicadores.optJSONArray("canal_alto")?.nullableDoubles().orEmpty(),
            canalBajo = indicadores.optJSONArray("canal_bajo")?.nullableDoubles().orEmpty(),
            marcadores =
                json.getJSONArray("marcadores").objects().map {
                    Marcador(it.getString("t"), it.getString("tipo"), it.stringOrNull("lado"), if (it.isNull("r")) null else it.getDouble("r"))
                },
            funding = json.getJSONArray("funding").objects().map { Funding(it.getString("t"), it.getDouble("tasa_8h")) },
        )
    }

    fun regimenes(json: JSONObject): Regimenes =
        Regimenes(origen(json), json.getJSONArray("tramos").objects().map { Tramo(it.getString("regimen"), it.getString("desde"), it.getString("hasta")) })

    fun correlaciones(json: JSONObject): Correlaciones =
        Correlaciones(
            origen = origen(json),
            ventana = json.optString("ventana", ""),
            simbolos = json.getJSONArray("simbolos").strings(),
            matriz = json.getJSONArray("matriz").let { rows -> (0 until rows.length()).map { rows.getJSONArray(it).nullableDoubles() } },
        )

    private fun resumen(json: JSONObject): ResumenLab {
        val ic = json.getJSONArray("ic90_r")
        return ResumenLab(
            operaciones = json.getInt("operaciones"),
            esperanzaR = json.getDouble("esperanza_r"),
            ic90Inferior = ic.getDouble(0),
            ic90Superior = ic.getDouble(1),
            pf = if (json.isNull("pf")) null else json.getDouble("pf"),
            tasaAcierto = json.getDouble("tasa_acierto"),
            porDireccion = segmentos(json.optJSONObject("por_direccion")),
            porRegimen = segmentos(json.optJSONObject("por_regimen")),
            porSemestre = segmentos(json.optJSONObject("por_semestre")),
        )
    }

    /** En el resumen del listado los segmentos pueden venir sin detalle: se ignoran los que no lo traen. */
    private fun segmentos(json: JSONObject?): Map<String, Segmento> =
        json?.keys()?.asSequence()?.sorted()?.mapNotNull { key ->
            json.optJSONObject(key)?.takeIf { it.has("n") }?.let { key to Segmento(it.getInt("n"), it.getDouble("esperanza_r")) }
        }?.toMap(LinkedHashMap()).orEmpty()

    private fun gate(json: JSONObject, passKey: String): GateLab {
        val criterios = json.getJSONObject("criterios")
        return GateLab(
            pasa = json.getBoolean(passKey),
            // Los códigos empiezan por el número del criterio: ordenarlos reproduce el orden del protocolo.
            criterios = criterios.keys().asSequence().sorted().map { Criterio(it, criterios.getBoolean(it)) }.toList(),
            holdout = json.stringOrNull("holdout"),
            valores = json.optJSONObject("valores")?.let { valores(it) },
        )
    }

    private fun valores(json: JSONObject): ValoresGate =
        ValoresGate(
            operaciones = if (json.has("operaciones")) json.getInt("operaciones") else null,
            ic90 = json.optJSONArray("ic90_r")?.let { it.getDouble(0) to it.getDouble(1) },
            pf = json.doubleOrNull("pf"),
            dsr = json.doubleOrNull("dsr"),
            pbo = json.doubleOrNull("pbo"),
            maxDdP95 = json.doubleOrNull("maxdd_p95_mc"),
            costesIc90 = json.optJSONArray("costes_x1.5_ic90")?.let { it.getDouble(0) to it.getDouble(1) },
            regimenesPositivos = json.optJSONArray("regimenes_positivos")?.strings().orEmpty(),
            maxPesoMes = json.doubleOrNull("max_peso_mes"),
        )

    private fun origen(json: JSONObject): Origen =
        when (json.getString("origen")) {
            "real" -> Origen.REAL
            "backtest" -> Origen.BACKTEST
            else -> Origen.DEMO // lo desconocido se trata como demostración, nunca como real
        }

    private fun JSONObject.stringOrNull(key: String): String? = if (!has(key) || isNull(key)) null else getString(key)

    private fun JSONObject.doubleOrNull(key: String): Double? = if (!has(key) || isNull(key)) null else getDouble(key)

    private fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }

    private fun JSONArray.strings(): List<String> = (0 until length()).map { getString(it) }

    private fun JSONArray.nullableDoubles(): List<Double?> = (0 until length()).map { if (isNull(it)) null else getDouble(it) }
}
