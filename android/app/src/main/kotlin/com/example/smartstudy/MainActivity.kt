package com.example.smartstudy

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

// ╔══════════════════════════════════════════════════════════════════╗
// ║  MainActivity — Quiz Security Features (Android)                 ║
// ║  • FLAG_SECURE: blocks screenshots & screen recording            ║
// ║  • Screen Pinning: locks app to foreground (user confirms)       ║
// ║  • Recent apps preview hidden when FLAG_SECURE is active         ║
// ╚══════════════════════════════════════════════════════════════════╝

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.smartstudy.security"
    private var isSecureMode = false

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            try {
                when (call.method) {
                    "enableSecure" -> {
                        enableSecureMode()
                        result.success(true)
                    }
                    "disableSecure" -> {
                        disableSecureMode()
                        result.success(true)
                    }
                    "requestScreenPin" -> {
                        requestScreenPinning()
                        result.success(true)
                    }
                    else -> result.notImplemented()
                }
            } catch (e: Exception) {
                result.error("SECURITY_ERROR", e.localizedMessage, null)
            }
        }
    }

    /**
     * Enable secure mode:
     * - FLAG_SECURE: Makes screenshots/screen recording show black content
     *   Also hides app content from recent apps (task switcher) preview
     * - This works on ALL Android devices without any special permissions
     */
    private fun enableSecureMode() {
        isSecureMode = true
        runOnUiThread {
            window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
    }

    /**
     * Disable secure mode and remove FLAG_SECURE
     */
    private fun disableSecureMode() {
        isSecureMode = false
        runOnUiThread {
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
    }

    /**
     * Request Android's built-in Screen Pinning feature.
     * This shows a system dialog asking the user to confirm pinning the app.
     * When pinned, the user cannot leave the app without unpinning first
     * (which triggers app lifecycle events we can detect in Flutter).
     *
     * NOTE: This does NOT require Device Owner/Admin (MDM).
     * It uses the user-facing "Screen Pinning" feature available since Android 5.0.
     * The user must have Screen Pinning enabled in Settings > Security.
     */
    private fun requestScreenPinning() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            val activityManager = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            // Check if already in lock task mode
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                if (activityManager.lockTaskModeState == ActivityManager.LOCK_TASK_MODE_NONE) {
                    try {
                        // startLockTask() in non-admin mode triggers the Screen Pinning UI
                        startLockTask()
                    } catch (_: Exception) {
                        // Screen pinning may not be available — silently continue
                        // FLAG_SECURE is still active for screenshot protection
                    }
                }
            } else {
                try {
                    startLockTask()
                } catch (_: Exception) {}
            }
        }
    }

    /**
     * When the user tries to leave the app while in secure mode,
     * stop the lock task if it was active
     */
    override fun onPause() {
        super.onPause()
        if (isSecureMode) {
            // The Flutter side (WidgetsBindingObserver) will handle
            // the quiz cancellation when app goes to background
        }
    }

    override fun onDestroy() {
        // Ensure we clean up lock task when activity is destroyed
        if (isSecureMode) {
            try {
                stopLockTask()
            } catch (_: Exception) {}
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
            isSecureMode = false
        }
        super.onDestroy()
    }
}
