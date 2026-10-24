package com.agentetrading.control.net

import java.net.URLEncoder

object Query {
    /** `/ruta?a=1&b=dos%20tres`: los valores del usuario siempre se codifican. */
    fun build(path: String, params: List<Pair<String, String>>): String =
        if (params.isEmpty()) path else path + "?" + params.joinToString("&") { (k, v) -> "$k=${encode(v)}" }

    private fun encode(value: String): String = URLEncoder.encode(value, "UTF-8")
}
