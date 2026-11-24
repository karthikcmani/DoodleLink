package com.doodlelink.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke as DrawStroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import com.doodlelink.app.model.Stroke
import com.doodlelink.app.model.ToolType
import com.doodlelink.app.viewmodel.DrawingViewModel

private val OuterBackgroundColor = Color(0xFF1E, 0x1E, 0x2E)
private val CanvasBackgroundColor = Color(0xFF, 0xFF, 0xFF)
private val BorderColor = Color(0xFF3B, 0x42, 0x52)

@Composable
fun CanvasSurface(
    viewModel: DrawingViewModel,
    modifier: Modifier = Modifier
) {
    val canvasState = viewModel.canvasState
    val coordMapper = viewModel.coordMapper
    // Observing stateVersion triggers redraws on stroke additions/mutations
    val _version = viewModel.stateVersion

    Canvas(
        modifier = modifier
            .fillMaxSize()
            .onSizeChanged { size ->
                coordMapper.updateScreenSize(size.width.toFloat(), size.height.toFloat())
            }
            .pointerInput(viewModel.currentTool, viewModel.currentColor, viewModel.activeThicknessPx) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    val (startX, startY) = coordMapper.screenToNormalized(down.position.x, down.position.y)

                    viewModel.onLocalStrokeStart(startX, startY, down.pressure)
                    down.consume()

                    val pointerId = down.id
                    while (true) {
                        val event = awaitPointerEvent()
                        val change = event.changes.firstOrNull { it.id == pointerId } ?: break

                        if (change.pressed) {
                            val (nx, ny) = coordMapper.screenToNormalized(change.position.x, change.position.y)
                            viewModel.onLocalPointAppend(nx, ny, change.pressure)
                            change.consume()
                        } else {
                            viewModel.onLocalStrokeFinish()
                            change.consume()
                            break
                        }
                    }
                }
            }
    ) {
        // 1. Draw outer margins (letterbox / pillarbox)
        drawRect(color = OuterBackgroundColor, size = size)

        val vp = coordMapper.viewport
        val canvasRect = Rect(vp.x, vp.y, vp.right, vp.bottom)

        // 2. Draw whiteboard surface
        drawRect(
            color = CanvasBackgroundColor,
            topLeft = Offset(vp.x, vp.y),
            size = Size(vp.width, vp.height)
        )

        // 3. Draw border
        drawRect(
            color = BorderColor,
            topLeft = Offset(vp.x, vp.y),
            size = Size(vp.width, vp.height),
            style = DrawStroke(width = 2.0f)
        )

        // 4. Clip drawing to the canvas rectangle
        clipRect(left = vp.x, top = vp.y, right = vp.right, bottom = vp.bottom) {
            // Render committed strokes
            for (stroke in canvasState.strokes) {
                renderStroke(this, coordMapper, stroke)
            }

            // Render active stroke
            val active = canvasState.activeStroke
            if (active != null) {
                renderStroke(this, coordMapper, active)
            }
        }
    }
}

private fun renderStroke(
    drawScope: androidx.compose.ui.graphics.drawscope.DrawScope,
    coordMapper: com.doodlelink.app.model.CoordinateMapper,
    stroke: Stroke
) {
    if (stroke.isEmpty()) return

    val strokeColor = if (stroke.tool == ToolType.ERASER) {
        CanvasBackgroundColor
    } else {
        try {
            Color(android.graphics.Color.parseColor(stroke.color))
        } catch (_: Exception) {
            Color.Black
        }
    }

    val pxWidth = coordMapper.normalizedToPixelWidth(stroke.width)
    val pts = stroke.points

    if (pts.size == 1) {
        val (sx, sy) = coordMapper.normalizedToScreen(pts[0].x, pts[0].y)
        drawScope.drawCircle(
            color = strokeColor,
            radius = (pxWidth / 2.0f).coerceAtLeast(1.0f),
            center = Offset(sx, sy)
        )
        return
    }

    val path = Path()
    val (firstX, firstY) = coordMapper.normalizedToScreen(pts[0].x, pts[0].y)
    path.moveTo(firstX, firstY)

    for (i in 1 until pts.size) {
        val (sx, sy) = coordMapper.normalizedToScreen(pts[i].x, pts[i].y)
        path.lineTo(sx, sy)
    }

    drawScope.drawPath(
        path = path,
        color = strokeColor,
        style = DrawStroke(
            width = pxWidth,
            cap = StrokeCap.Round,
            join = StrokeJoin.Round
        )
    )
}
