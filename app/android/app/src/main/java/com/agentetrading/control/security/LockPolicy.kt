package com.agentetrading.control.security

/** Cuándo la app vuelve a pedir huella, rostro o PIN del teléfono. */
object LockPolicy {
    const val GRACE_MS = 60_000L

    /**
     * @param unlockedAtMs momento del último desbloqueo de este proceso (null: aún no).
     * @param backgroundedAtMs momento en que la app pasó a segundo plano (null: sigue al frente).
     */
    fun needsUnlock(enabled: Boolean, unlockedAtMs: Long?, backgroundedAtMs: Long?, nowMs: Long): Boolean {
        if (!enabled) return false
        if (unlockedAtMs == null) return true
        val away = backgroundedAtMs ?: return false
        return nowMs - away > GRACE_MS
    }
}
