package com.agentetrading.control

import android.content.Context

/** Preferencias locales. No guardan secretos: la dirección del servidor y dos interruptores. */
class Prefs(context: Context) {
    private val store = context.getSharedPreferences("brujula", Context.MODE_PRIVATE)

    var serverUrl: String?
        get() = store.getString(KEY_URL, null)
        set(value) {
            store.edit().putString(KEY_URL, value).apply()
        }

    /** Pedir huella, rostro o PIN al abrir y al volver tras un minuto fuera. */
    var lockEnabled: Boolean
        get() = store.getBoolean(KEY_LOCK, true)
        set(value) {
            store.edit().putBoolean(KEY_LOCK, value).apply()
        }

    /** Ocultar la app en apps recientes y bloquear capturas de pantalla. */
    var secureScreen: Boolean
        get() = store.getBoolean(KEY_SECURE, true)
        set(value) {
            store.edit().putBoolean(KEY_SECURE, value).apply()
        }

    private companion object {
        const val KEY_URL = "server_url"
        const val KEY_LOCK = "lock_enabled"
        const val KEY_SECURE = "secure_screen"
    }
}
