package com.doodlelink.app.network

import com.doodlelink.app.model.Point
import kotlinx.serialization.Serializable

@Serializable
data class SerializedStroke(
    val stroke_id: String,
    val tool: String = "pen",
    val color: String = "#000000",
    val width: Float = 0.004f,
    val points: List<Point> = emptyList()
)

@Serializable
data class GenericMessage(
    val version: Int = 1,
    val type: String,
    val session_id: String? = null,
    val code: String? = null,
    val client_name: String? = null,
    val message: String? = null,
    val stroke_id: String? = null,
    val sequence: Int = 0,
    val tool: String? = null,
    val color: String? = null,
    val width: Float? = null,
    val timestamp: Double? = null,
    val points: List<Point>? = null,
    val board_id: String? = null,
    val page_id: String? = null,
    val page_number: Int? = null,
    val total_pages: Int? = null,
    val direction: String? = null,
    val strokes: List<SerializedStroke>? = null
)

@Serializable
data class PairRequest(
    val version: Int = 1,
    val type: String = "pair",
    val code: String? = null,
    val session_id: String? = null,
    val client_name: String = "Nothing Phone (3a)"
)

@Serializable
data class StrokeStartEvent(
    val version: Int = 1,
    val type: String = "stroke_start",
    val session_id: String? = null,
    val stroke_id: String,
    val sequence: Int = 0,
    val tool: String = "pen",
    val color: String = "#000000",
    val width: Float = 0.004f,
    val points: List<Point> = emptyList()
)

@Serializable
data class StrokePointsEvent(
    val version: Int = 1,
    val type: String = "stroke_points",
    val session_id: String? = null,
    val stroke_id: String,
    val sequence: Int = 0,
    val points: List<Point>
)

@Serializable
data class StrokeLifecycleEvent(
    val version: Int = 1,
    val type: String, // "stroke_end" or "stroke_cancel"
    val session_id: String? = null,
    val stroke_id: String,
    val sequence: Int = 0
)

@Serializable
data class ActionEvent(
    val version: Int = 1,
    val type: String, // "undo", "redo", or "clear_canvas"
    val session_id: String? = null,
    val sequence: Int = 0
)

@Serializable
data class HeartbeatEvent(
    val version: Int = 1,
    val type: String, // "ping" or "pong"
    val timestamp: Double = System.currentTimeMillis().toDouble()
)

@Serializable
data class PageInfoEvent(
    val version: Int = 1,
    val type: String = "page_info",
    val session_id: String? = null,
    val sequence: Int = 0,
    val board_id: String? = null,
    val page_id: String = "",
    val page_number: Int = 1,
    val total_pages: Int = 1,
    val strokes: List<SerializedStroke> = emptyList()
)

@Serializable
data class PageSwitchEvent(
    val version: Int = 1,
    val type: String = "page_switch",
    val session_id: String? = null,
    val sequence: Int = 0,
    val direction: String,
    val page_id: String = ""
)
