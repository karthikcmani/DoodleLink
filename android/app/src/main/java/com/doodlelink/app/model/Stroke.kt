package com.doodlelink.app.model

import kotlinx.serialization.Serializable
import java.util.UUID

data class BoundingBox(
    val minX: Float,
    val minY: Float,
    val maxX: Float,
    val maxY: Float
)

/**
 * A continuous drawing stroke composed of ordered normalized points.
 */
@Serializable
data class Stroke(
    val id: String = UUID.randomUUID().toString(),
    val tool: ToolType = ToolType.PEN,
    val color: String = "#000000",
    val width: Float = 0.004f,
    val points: MutableList<Point> = mutableListOf()
) {
    fun addPoint(
        x: Float,
        y: Float,
        timestamp: Double = System.currentTimeMillis().toDouble(),
        pressure: Float = 1.0f
    ): Point {
        val pt = Point(
            x = x.coerceIn(0.0f, 1.0f),
            y = y.coerceIn(0.0f, 1.0f),
            timestamp = timestamp,
            pressure = pressure.coerceIn(0.0f, 1.0f)
        )
        points.add(pt)
        return pt
    }

    fun isEmpty(): Boolean = points.isEmpty()

    fun boundingBox(): BoundingBox? {
        if (points.isEmpty()) return null
        var minX = Float.MAX_VALUE
        var minY = Float.MAX_VALUE
        var maxX = Float.MIN_VALUE
        var maxY = Float.MIN_VALUE

        for (p in points) {
            if (p.x < minX) minX = p.x
            if (p.y < minY) minY = p.y
            if (p.x > maxX) maxX = p.x
            if (p.y > maxY) maxY = p.y
        }

        val halfW = width / 2.0f
        return BoundingBox(
            minX = (minX - halfW).coerceAtLeast(0.0f),
            minY = (minY - halfW).coerceAtLeast(0.0f),
            maxX = (maxX + halfW).coerceAtMost(1.0f),
            maxY = (maxY + halfW).coerceAtMost(1.0f)
        )
    }
}
