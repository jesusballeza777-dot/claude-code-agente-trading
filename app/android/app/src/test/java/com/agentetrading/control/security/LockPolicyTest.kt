package com.agentetrading.control.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LockPolicyTest {
    @Test
    fun disabledNeverAsks() {
        assertFalse(LockPolicy.needsUnlock(false, null, null, 1_000))
    }

    @Test
    fun firstOpenAsks() {
        assertTrue(LockPolicy.needsUnlock(true, null, null, 1_000))
    }

    @Test
    fun stillInForegroundDoesNotAsk() {
        assertFalse(LockPolicy.needsUnlock(true, 1_000, null, 500_000))
    }

    @Test
    fun shortAbsenceDoesNotAskButLongOneDoes() {
        assertFalse(LockPolicy.needsUnlock(true, 1_000, 10_000, 10_000 + LockPolicy.GRACE_MS))
        assertTrue(LockPolicy.needsUnlock(true, 1_000, 10_000, 10_001 + LockPolicy.GRACE_MS))
    }
}
