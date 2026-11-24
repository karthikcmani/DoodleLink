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
    fun testPairRequestWithSessionIdSerialization() {
        val req = PairRequest(session_id = "sess-uuid-456", client_name = "Nothing Phone (3a)")
        val jsonStr = DoodleJson.json.encodeToString(req)
        assertTrue(jsonStr.contains("\"type\":\"pair\""))
        assertTrue(jsonStr.contains("\"session_id\":\"sess-uuid-456\""))
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
    fun testPageSwitchEventSerialization() {
        val switchEvent = com.doodlelink.app.network.PageSwitchEvent(
            session_id = "sess-123",
            direction = "next",
            sequence = 10
        )
        val jsonStr = DoodleJson.json.encodeToString(switchEvent)
        assertTrue(jsonStr.contains("\"type\":\"page_switch\""))
        assertTrue(jsonStr.contains("\"direction\":\"next\""))
        assertTrue(jsonStr.contains("\"sequence\":10"))
    }

    @Test
    fun testPageInfoDeserialization() {
        val pageInfoJson = """
            {
                "version": 1,
                "type": "page_info",
                "session_id": "sess-abc",
                "sequence": 5,
                "board_id": "b-1",
                "page_id": "p-2",
                "page_number": 2,
                "total_pages": 4,
                "strokes": [
                    {
                        "stroke_id": "s-100",
                        "tool": "pen",
                        "color": "#FF0000",
                        "width": 0.005,
                        "points": [{"x": 0.1, "y": 0.2}]
                    }
                ]
            }
        """.trimIndent()

        val parsed = DoodleJson.json.decodeFromString<GenericMessage>(pageInfoJson)
        assertEquals("page_info", parsed.type)
        assertEquals("p-2", parsed.page_id)
        assertEquals(2, parsed.page_number)
        assertEquals(4, parsed.total_pages)
        assertEquals(1, parsed.strokes?.size)
        assertEquals("s-100", parsed.strokes?.get(0)?.stroke_id)
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
