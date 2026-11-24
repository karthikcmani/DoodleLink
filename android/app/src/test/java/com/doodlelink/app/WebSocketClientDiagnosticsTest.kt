package com.doodlelink.app

import com.doodlelink.app.network.WebSocketClient
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.ConnectException
import java.net.NoRouteToHostException
import java.net.SocketTimeoutException

class WebSocketClientDiagnosticsTest {

    @Test
    fun testWifiConnectExceptionDiagnostics() {
        val client = WebSocketClient()
        // Simulate Wi-Fi connection target
        client.connect("192.168.1.50", 8765, "123456")
        val errorMsg = client.formatErrorMessage(ConnectException("Connection refused"))
        assertTrue("Message should mention server running: $errorMsg", errorMsg.contains("Ensure server is running"))
        assertTrue("Message should include host: $errorMsg", errorMsg.contains("192.168.1.50:8765"))
        client.disconnect()
    }

    @Test
    fun testUsbAdbConnectExceptionDiagnostics() {
        val client = WebSocketClient()
        // Simulate USB ADB reverse target
        client.connect("127.0.0.1", 8765, "123456")
        val errorMsg = client.formatErrorMessage(ConnectException("Connection refused"))
        assertTrue("Message should mention adb reverse: $errorMsg", errorMsg.contains("adb reverse"))
        client.disconnect()
    }

    @Test
    fun testSocketTimeoutDiagnostics() {
        val client = WebSocketClient()
        client.connect("192.168.43.10", 8765, "123456")
        val errorMsg = client.formatErrorMessage(SocketTimeoutException("timeout"))
        assertTrue("Message should mention timeout and IP: $errorMsg", errorMsg.contains("timed out"))
        client.disconnect()
    }

    @Test
    fun testNoRouteToHostDiagnostics() {
        val client = WebSocketClient()
        client.connect("192.168.1.200", 8765, "123456")
        val errorMsg = client.formatErrorMessage(NoRouteToHostException("No route"))
        assertTrue("Message should mention network: $errorMsg", errorMsg.contains("No route to host"))
        client.disconnect()
    }
}
