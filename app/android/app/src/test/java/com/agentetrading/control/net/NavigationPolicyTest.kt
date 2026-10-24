package com.agentetrading.control.net

import com.agentetrading.control.net.NavigationPolicy.Decision
import org.junit.Assert.assertEquals
import org.junit.Test

class NavigationPolicyTest {
    private val base = "https://mi-vps.tail1234.ts.net"

    @Test
    fun sameOriginStays() {
        assertEquals(Decision.STAY, NavigationPolicy.decide(base, "https://mi-vps.tail1234.ts.net/laboratorio"))
        assertEquals(Decision.STAY, NavigationPolicy.decide(base, "https://MI-VPS.tail1234.ts.net:443/riesgo"))
        assertEquals(
            Decision.STAY,
            NavigationPolicy.decide("http://127.0.0.1:8080", "http://127.0.0.1:8080/en-vivo"),
        )
    }

    @Test
    fun otherHttpsSitesOpenInTheBrowser() {
        assertEquals(Decision.EXTERNAL, NavigationPolicy.decide(base, "https://www.tradingview.com/"))
        assertEquals(Decision.EXTERNAL, NavigationPolicy.decide(base, "https://mi-vps.tail1234.ts.net:8443/"))
    }

    @Test
    fun everythingElseIsBlocked() {
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "http://mi-vps.tail1234.ts.net/"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "http://evil.example/"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "file:///data/data/com.agentetrading.control/x"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "javascript:alert(1)"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "intent://scan/#Intent;scheme=zxing;end"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "data:text/html,hola"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "https://[bad"))
    }

    @Test
    fun settingsLinkIsInternal() {
        assertEquals(Decision.SETTINGS, NavigationPolicy.decide(base, "brujula://ajustes"))
        assertEquals(Decision.BLOCK, NavigationPolicy.decide(base, "brujula://otra-cosa"))
    }
}
