package com.doodlelink.app

import android.content.Intent
import android.os.Bundle
import android.util.Log
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
        handleIntent(intent)

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

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent == null) return

        // Security: Intent-based connection automation is strictly disabled in release builds
        // to prevent untrusted third-party apps from redirecting connections.
        if (!BuildConfig.DEBUG) {
            return
        }

        val host = intent.getStringExtra("connect_host")?.trim()
        val port = intent.getIntExtra("connect_port", 8765)
        val code = intent.getStringExtra("connect_code")?.trim()

        if (!host.isNullOrBlank() && !code.isNullOrBlank()) {
            // Security: In debug automation, restrict to loopback to avoid arbitrary redirection
            if (host == "127.0.0.1" || host == "localhost") {
                Log.i("DoodleLink", "Debug auto-connecting to localhost:$port (pairing code redacted)")
                viewModel.connectToHost(host, port, code)
            } else {
                Log.w("DoodleLink", "Ignored non-loopback debug auto-connect target: $host")
            }
        } else if (intent.getBooleanExtra("open_dialog", false)) {
            viewModel.openConnectDialog()
        }
    }
}
