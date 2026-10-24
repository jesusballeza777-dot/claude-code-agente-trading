package com.agentetrading.control.security

import android.content.Context
import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

/** Huella, rostro o PIN del teléfono. Nada se guarda: solo se pregunta al sistema. */
object AppLock {
    // BIOMETRIC_STRONG con DEVICE_CREDENTIAL no se admite en Android 9 y 10.
    private val authenticators: Int =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL
        } else {
            BiometricManager.Authenticators.BIOMETRIC_WEAK or BiometricManager.Authenticators.DEVICE_CREDENTIAL
        }

    /** Falso si el teléfono no tiene bloqueo de pantalla configurado. */
    fun available(context: Context): Boolean =
        BiometricManager.from(context).canAuthenticate(authenticators) == BiometricManager.BIOMETRIC_SUCCESS

    fun prompt(activity: FragmentActivity, onSuccess: () -> Unit, onFailure: (String) -> Unit) {
        val callback =
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) = onSuccess()

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) = onFailure(errString.toString())
            }
        val info =
            BiometricPrompt.PromptInfo.Builder()
                .setTitle("Centro de Mando")
                .setSubtitle("Confirma que eres tú")
                .setAllowedAuthenticators(authenticators)
                .build()
        BiometricPrompt(activity, ContextCompat.getMainExecutor(activity), callback).authenticate(info)
    }
}
