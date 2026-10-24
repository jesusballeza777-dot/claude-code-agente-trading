package com.agentetrading.control

import android.graphics.Color
import android.os.Bundle
import android.os.SystemClock
import android.view.WindowManager
import android.webkit.CookieManager
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.fragment.app.FragmentActivity
import com.agentetrading.control.security.AppLock
import com.agentetrading.control.security.LockPolicy
import com.agentetrading.control.ui.BrujulaTheme
import com.agentetrading.control.ui.ConnectScreen
import com.agentetrading.control.ui.LockScreen
import com.agentetrading.control.ui.AppShell

/**
 * App personal de control: cliente de solo lectura del Centro de Mando (ADR-018).
 * No tiene claves de exchanges ni de wallets, y no envía órdenes ni cambia límites.
 */
class MainActivity : FragmentActivity() {
    private enum class Screen { LOCKED, SETTINGS, WEB }

    private lateinit var prefs: Prefs
    private var screen by mutableStateOf(Screen.WEB)
    private var lockMessage by mutableStateOf<String?>(null)
    private var unlockedAt: Long? = null
    private var backgroundedAt: Long? = null
    private var prompting = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        applySecureScreen()
        setContent { BrujulaTheme { Root() } }
    }

    override fun onStart() {
        super.onStart()
        decideScreen()
    }

    override fun onStop() {
        super.onStop()
        backgroundedAt = SystemClock.elapsedRealtime()
    }

    private fun decideScreen() {
        if (prefs.serverUrl == null) {
            screen = Screen.SETTINGS
            return
        }
        val lockActive = prefs.lockEnabled && AppLock.available(this)
        if (LockPolicy.needsUnlock(lockActive, unlockedAt, backgroundedAt, SystemClock.elapsedRealtime())) {
            screen = Screen.LOCKED
            askUnlock()
        } else {
            backgroundedAt = null
            if (screen == Screen.LOCKED) screen = Screen.WEB
        }
    }

    private fun askUnlock() {
        if (prompting) return
        prompting = true
        AppLock.prompt(
            activity = this,
            onSuccess = {
                prompting = false
                unlockedAt = SystemClock.elapsedRealtime()
                backgroundedAt = null
                lockMessage = null
                screen = Screen.WEB
            },
            onFailure = {
                prompting = false
                lockMessage = it
            },
        )
    }

    private fun applySecureScreen() {
        if (prefs.secureScreen) {
            window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
    }

    @Composable
    private fun Root() {
        var lockEnabled by remember { mutableStateOf(prefs.lockEnabled) }
        var secureScreen by remember { mutableStateOf(prefs.secureScreen) }
        Box(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).systemBarsPadding()) {
            when (screen) {
                Screen.LOCKED -> LockScreen(message = lockMessage, onUnlock = { askUnlock() })
                Screen.SETTINGS ->
                    ConnectScreen(
                        initialUrl = prefs.serverUrl.orEmpty(),
                        lockEnabled = lockEnabled && AppLock.available(this@MainActivity),
                        secureScreen = secureScreen,
                        lockAvailable = AppLock.available(this@MainActivity),
                        canClose = prefs.serverUrl != null,
                        onSaved = { url ->
                            if (url != prefs.serverUrl) CookieManager.getInstance().removeAllCookies(null)
                            prefs.serverUrl = url
                            unlockedAt = SystemClock.elapsedRealtime()
                            backgroundedAt = null
                            screen = Screen.WEB
                        },
                        onLockChange = {
                            lockEnabled = it
                            prefs.lockEnabled = it
                        },
                        onSecureChange = {
                            secureScreen = it
                            prefs.secureScreen = it
                            applySecureScreen()
                        },
                        onClose = { screen = Screen.WEB },
                    )
                Screen.WEB ->
                    prefs.serverUrl?.let { url ->
                        AppShell(baseUrl = url, lifecycle = lifecycle, onOpenSettings = { screen = Screen.SETTINGS })
                    }
            }
        }
    }
}
