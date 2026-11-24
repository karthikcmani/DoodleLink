package com.doodlelink.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Fullscreen
import androidx.compose.material.icons.filled.FullscreenExit
import androidx.compose.material.icons.automirrored.filled.Redo
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.doodlelink.app.model.ToolType
import com.doodlelink.app.viewmodel.DrawingViewModel

private val PaletteColors = listOf(
    "#111827", // Black
    "#4B5563", // Slate
    "#DC2626", // Red
    "#2563EB", // Blue
    "#16A34A", // Green
    "#D97706", // Amber
    "#EA580C", // Orange
    "#9333EA", // Purple
    "#0891B2", // Cyan
    "#DB2777"  // Pink
)

private val ThicknessPresets = listOf(2.0f, 6.0f, 12.0f, 24.0f)

@Composable
fun DrawingControls(
    viewModel: DrawingViewModel,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier) {
        // Floating Restore Button when in Fullscreen Mode
        if (viewModel.isFullScreen) {
            IconButton(
                onClick = { viewModel.toggleFullScreen() },
                modifier = Modifier
                    .padding(16.dp)
                    .align(Alignment.TopEnd)
                    .clip(CircleShape)
                    .background(Color(0xCC1E, 0x1E, 0x2E))
                    .size(48.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.FullscreenExit,
                    contentDescription = "Exit Fullscreen",
                    tint = Color.White
                )
            }
        }

        // Full Toolbar when not in Fullscreen
        AnimatedVisibility(
            visible = !viewModel.isFullScreen,
            enter = slideInVertically(initialOffsetY = { -it }) + fadeIn(),
            exit = slideOutVertically(targetOffsetY = { -it }) + fadeOut(),
            modifier = Modifier.align(Alignment.TopCenter)
        ) {
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp),
                shape = RoundedCornerShape(16.dp),
                color = Color(0xEE11, 0x18, 0x27),
                shadowElevation = 8.dp
            ) {
                Column(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Row 1: Tools, Undo/Redo, Clear, Fullscreen
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Tool Selector
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            ToolChip(
                                label = "Pen",
                                icon = Icons.Default.Edit,
                                selected = viewModel.currentTool == ToolType.PEN,
                                onClick = { viewModel.selectTool(ToolType.PEN) }
                            )
                            ToolChip(
                                label = "Eraser",
                                icon = Icons.Default.AutoFixHigh,
                                selected = viewModel.currentTool == ToolType.ERASER,
                                onClick = { viewModel.selectTool(ToolType.ERASER) }
                            )
                        }

                        // Actions
                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            IconButton(
                                onClick = { viewModel.undo() },
                                enabled = viewModel.canvasState.canUndo,
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(
                                    Icons.AutoMirrored.Filled.Undo,
                                    contentDescription = "Undo",
                                    tint = if (viewModel.canvasState.canUndo) Color.White else Color(0xFF6B7280)
                                )
                            }
                            IconButton(
                                onClick = { viewModel.redo() },
                                enabled = viewModel.canvasState.canRedo,
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(
                                    Icons.AutoMirrored.Filled.Redo,
                                    contentDescription = "Redo",
                                    tint = if (viewModel.canvasState.canRedo) Color.White else Color(0xFF6B7280)
                                )
                            }
                            IconButton(
                                onClick = { viewModel.clear() },
                                enabled = viewModel.canvasState.strokeCount > 0,
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(
                                    Icons.Default.Delete,
                                    contentDescription = "Clear",
                                    tint = if (viewModel.canvasState.strokeCount > 0) Color(0xFFEF4444) else Color(0xFF6B7280)
                                )
                            }
                            IconButton(
                                onClick = { viewModel.toggleFullScreen() },
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(
                                    Icons.Default.Fullscreen,
                                    contentDescription = "Fullscreen",
                                    tint = Color.White
                                )
                            }
                        }
                    }

                    // Row 2: Color Palette (Only shown when Pen is selected)
                    if (viewModel.currentTool == ToolType.PEN) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            for (hex in PaletteColors) {
                                ColorSwatch(
                                    hexColor = hex,
                                    isSelected = viewModel.currentColor.equals(hex, ignoreCase = true),
                                    onClick = { viewModel.selectColor(hex) }
                                )
                            }
                        }
                    }

                    // Row 3: Brush Thickness Presets & Slider
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${viewModel.activeThicknessPx.toInt()}px",
                            color = Color(0xFF9CA3AF),
                            fontSize = 12.sp,
                            modifier = Modifier.padding(end = 4.dp)
                        )

                        // Preset chips
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            for (preset in ThicknessPresets) {
                                val isSelected = viewModel.activeThicknessPx == preset
                                Box(
                                    modifier = Modifier
                                        .size(28.dp)
                                        .clip(CircleShape)
                                        .background(if (isSelected) Color(0xFF2563EB) else Color(0xFF374151))
                                        .clickable {
                                            if (viewModel.currentTool == ToolType.PEN) {
                                                viewModel.setPenThickness(preset)
                                            } else {
                                                viewModel.setEraserThickness(preset * 3)
                                            }
                                        },
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = "${preset.toInt()}",
                                        color = Color.White,
                                        fontSize = 11.sp
                                    )
                                }
                            }
                        }

                        // Fine Slider
                        Slider(
                            value = viewModel.activeThicknessPx,
                            onValueChange = {
                                if (viewModel.currentTool == ToolType.PEN) {
                                    viewModel.setPenThickness(it)
                                } else {
                                    viewModel.setEraserThickness(it)
                                }
                            },
                            valueRange = if (viewModel.currentTool == ToolType.PEN) 1.0f..48.0f else 4.0f..96.0f,
                            colors = SliderDefaults.colors(
                                thumbColor = Color(0xFF38BDF8),
                                activeTrackColor = Color(0xFF2563EB),
                                inactiveTrackColor = Color(0xFF374151)
                            ),
                            modifier = Modifier.weight(1.0f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ToolChip(
    label: String,
    icon: ImageVector,
    selected: Boolean,
    onClick: () -> Unit
) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label, fontSize = 12.sp) },
        leadingIcon = {
            Icon(
                icon,
                contentDescription = null,
                modifier = Modifier.size(16.dp)
            )
        },
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = Color(0xFF2563EB),
            selectedLabelColor = Color.White,
            selectedLeadingIconColor = Color.White,
            containerColor = Color(0xFF1F2937),
            labelColor = Color(0xFFD1D5DB),
            iconColor = Color(0xFFD1D5DB)
        )
    )
}

@Composable
private fun ColorSwatch(
    hexColor: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val color = try {
        Color(android.graphics.Color.parseColor(hexColor))
    } catch (_: Exception) {
        Color.Black
    }

    Box(
        modifier = Modifier
            .size(28.dp)
            .clip(CircleShape)
            .background(color)
            .border(
                width = if (isSelected) 3.dp else 1.dp,
                color = if (isSelected) Color(0xFF38BDF8) else Color(0x66FFFFFF),
                shape = CircleShape
            )
            .clickable(onClick = onClick)
    )
}
