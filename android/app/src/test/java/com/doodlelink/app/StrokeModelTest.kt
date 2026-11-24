package com.doodlelink.app

import com.doodlelink.app.model.DoodleJson
import com.doodlelink.app.model.Point
import com.doodlelink.app.model.Stroke
import com.doodlelink.app.model.ToolType
import kotlinx.serialization.encodeToString
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StrokeModelTest {

    private val json = DoodleJson.json

    @Test
    fun testPointCreationAndClamping() {
        val p = Point(x = 0.5f, y = 0.5f, timestamp = 1000.0, pressure = 0.8f)
        assertEquals(0.5f, p.x, 0.0001f)
        assertEquals(0.5f, p.y, 0.0001f)
        assertEquals(1000.0, p.timestamp, 0.001)
        assertEquals(0.8f, p.pressure, 0.0001f)

        // Point clamped
        val p2 = Point(x = 0.0f, y = 1.0f, pressure = 1.0f).clamped()
        assertEquals(0.0f, p2.x, 0.0001f)
        assertEquals(1.0f, p2.y, 0.0001f)
    }

    @Test
    fun testStrokeAddPointAndBoundingBox() {
        val stroke = Stroke(tool = ToolType.PEN, color = "#2563EB", width = 0.01f)
        assertTrue(stroke.isEmpty())

        stroke.addPoint(0.2f, 0.3f, 100.0, 0.5f)
        stroke.addPoint(0.8f, 0.7f, 200.0, 0.9f)
        assertEquals(2, stroke.points.size)

        val bbox = stroke.boundingBox()
        assertNotNull(bbox)
        assertTrue(bbox!!.minX <= 0.2f)
        assertTrue(bbox.minY <= 0.3f)
        assertTrue(bbox.maxX >= 0.8f)
        assertTrue(bbox.maxY >= 0.7f)
    }

    @Test
    fun testJsonSerializationMatchesProtocolV1() {
        val stroke = Stroke(
            id = "test-uuid-1234",
            tool = ToolType.PEN,
            color = "#DC2626",
            width = 0.005f
        )
        stroke.addPoint(0.15f, 0.25f, 12345.0, 0.9f)
        stroke.addPoint(0.45f, 0.65f, 12350.0, 0.85f)

        val encoded = json.encodeToString(stroke)
        println("ENCODED JSON: $encoded")
        assertTrue("Expected id in JSON", encoded.contains("\"id\":\"test-uuid-1234\""))
        assertTrue("Expected tool in JSON: $encoded", encoded.contains("\"tool\":\"pen\""))
        assertTrue(encoded.contains("\"color\":\"#DC2626\""))
        assertTrue(encoded.contains("\"width\":"))
        assertTrue(encoded.contains("\"points\":["))

        // Deserialize back
        val decoded = json.decodeFromString<Stroke>(encoded)
        assertEquals(stroke.id, decoded.id)
        assertEquals(stroke.tool, decoded.tool)
        assertEquals(stroke.color, decoded.color)
        assertEquals(0.005f, decoded.width, 0.0001f)
        assertEquals(2, decoded.points.size)
        assertEquals(0.15f, decoded.points[0].x, 0.0001f)
        assertEquals(0.25f, decoded.points[0].y, 0.0001f)
    }

    @Test
    fun testDesktopGeneratedJsonCompatibility() {
        // Sample JSON string produced by python desktop Stroke.to_dict()
        val desktopJson = """
            {
                "id": "desktop-stroke-999",
                "tool": "eraser",
                "color": "#FFFFFF",
                "width": 0.02,
                "points": [
                    {"x": 0.3, "y": 0.4, "timestamp": 5000.0, "pressure": 1.0},
                    {"x": 0.5, "y": 0.6, "timestamp": 5010.0, "pressure": 0.95}
                ]
            }
        """.trimIndent()

        val decoded = json.decodeFromString<Stroke>(desktopJson)
        assertEquals("desktop-stroke-999", decoded.id)
        assertEquals(ToolType.ERASER, decoded.tool)
        assertEquals("#FFFFFF", decoded.color)
        assertEquals(0.02f, decoded.width, 0.0001f)
        assertEquals(2, decoded.points.size)
        assertEquals(0.3f, decoded.points[0].x, 0.0001f)
        assertEquals(0.5f, decoded.points[1].x, 0.0001f)
    }
}
