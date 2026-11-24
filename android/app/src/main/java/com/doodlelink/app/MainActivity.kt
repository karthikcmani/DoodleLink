package com.doodlelink.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.doodlelink.app.ui.CanvasSurface
import com.doodlelink.app.ui.DrawingControls
import com.doodlelink.app.viewmodel.DrawingViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: DrawingViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    background = Color(0xFF1E, 0x1E, 0x2E),
                    surface = Color(0xFF11, 0x18, 0x27)
                )
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF1E, 0x1E, 0x2E)
                ) {
                    Box(modifier = Modifier.fillMaxSize()) {
                        // Drawing Canvas Layer
                        CanvasSurface(
                            viewModel = viewModel,
                            modifier = Modifier.fillMaxSize()
                        )

                        // Floating Toolbar Controls
                        DrawingControls(
                            viewModel = viewModel,
                            modifier = Modifier.fillMaxSize()
                        )
                    }
                }
            }
        }
    }
}
