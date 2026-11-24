package com.doodlelink.app

import com.doodlelink.app.model.DoodleJson
import com.doodlelink.app.model.Point
import com.doodlelink.app.network.ActionEvent
import com.doodlelink.app.network.ConnectionState
import com.doodlelink.app.network.GenericMessage
import com.doodlelink.app.network.HeartbeatEvent
import com.doodlelink.app.network.PairRequest
import com.doodlelink.app.network.StrokeLifecycleEvent
import com.doodlelink.app.network.StrokePointsEvent
import com.doodlelink.app.network.StrokeStartEvent
import kotlinx.serialization.encodeToString
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WebSocketProtocolTest {

    @Test
    fun testPairRequestSerialization() {
        val req = PairRequest(code = "482915", client_name = "Nothing Phone (3a)")
        val jsonStr = DoodleJson.json.encodeToString(req)
        assertTrue(jsonStr.contains("\"type\":\"pair\""))
        assertTrue(jsonStr.contains("\"code\":\"482915\""))
        assertTrue(jsonStr.contains("\"client_name\":\"Nothing Phone (3a)\""))
    }

    @Test
    fun testStrokeStartSerialization() {
        val start = StrokeStartEvent(
            session_id = "sess-123",
            stroke_id = "s-1",
            sequence = 1,
            tool = "pen",
            color = "#2563EB",
            width = 0.005f,
            points = listOf(Point(0.1f, 0.2f))
        )
        val jsonStr = DoodleJson.json.encodeToString(start)
        assertTrue(jsonStr.contains("\"type\":\"stroke_start\""))
        assertTrue(jsonStr.contains("\"session_id\":\"sess-123\""))
        assertTrue(jsonStr.contains("\"stroke_id\":\"s-1\""))
        assertTrue(jsonStr.contains("\"sequence\":1"))
        assertTrue(jsonStr.contains("\"tool\":\"pen\""))
    }

    @Test
    fun testStrokePointsSerialization() {
        val ptsEvent = StrokePointsEvent(
            session_id = "sess-123",
            stroke_id = "s-1",
            sequence = 2,
            points = listOf(Point(0.3f, 0.4f), Point(0.5f, 0.6f))
        )
        val jsonStr = DoodleJson.json.encodeToString(ptsEvent)
        assertTrue(jsonStr.contains("\"type\":\"stroke_points\""))
        assertTrue(jsonStr.contains("\"sequence\":2"))
        assertTrue(jsonStr.contains("\"points\":["))
    }

    @Test
    fun testStrokeLifecycleAndActionSerialization() {
        val endEvent = StrokeLifecycleEvent(type = "stroke_end", stroke_id = "s-1", sequence = 3)
        val endStr = DoodleJson.json.encodeToString(endEvent)
        assertTrue(endStr.contains("\"type\":\"stroke_end\""))

        val undoEvent = ActionEvent(type = "undo", sequence = 4)
        val undoStr = DoodleJson.json.encodeToString(undoEvent)
        assertTrue(undoStr.contains("\"type\":\"undo\""))

        val clearEvent = ActionEvent(type = "clear_canvas", sequence = 5)
        val clearStr = DoodleJson.json.encodeToString(clearEvent)
        assertTrue(clearStr.contains("\"type\":\"clear_canvas\""))
    }

    @Test
    fun testServerResponseDeserialization() {
        val successJson = """
            {
                "version": 1,
                "type": "pair_success",
                "session_id": "test-session-guid",
                "message": "Connected to DoodleLink Host"
            }
        """.trimIndent()

        val parsed = DoodleJson.json.decodeFromString<GenericMessage>(successJson)
        assertEquals("pair_success", parsed.type)
        assertEquals("test-session-guid", parsed.session_id)

        val errorJson = """
            {
                "version": 1,
                "type": "error",
                "code": "INVALID_PAIRING_CODE",
                "message": "Incorrect or expired pairing code"
            }
        """.trimIndent()
        val parsedErr = DoodleJson.json.decodeFromString<GenericMessage>(errorJson)
        assertEquals("error", parsedErr.type)
        assertEquals("INVALID_PAIRING_CODE", parsedErr.code)
    }

    @Test
    fun testConnectionStateBooleans() {
        assertTrue(ConnectionState.CONNECTED.isConnected)
        assertFalse(ConnectionState.DISCONNECTED.isConnected)
        assertTrue(ConnectionState.CONNECTING.isConnectingOrReconnecting)
        assertTrue(ConnectionState.RECONNECTING.isConnectingOrReconnecting)
        assertFalse(ConnectionState.ERROR.isConnectingOrReconnecting)
    }
}
