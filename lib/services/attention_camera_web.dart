// ╔══════════════════════════════════════════════════════════════════╗
// ║     ATTENTION CAMERA — WEB implementation (Chrome/Edge)           ║
// ║  getUserMedia → hidden <video> → <canvas> → base64 JPEG frames    ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// This is compiled ONLY on Flutter Web (selected via the conditional export
// in attention_camera.dart). It grabs the webcam with the standard browser
// MediaDevices API, draws the current video frame onto an offscreen canvas,
// and returns a base64 data-URL JPEG that we POST to the backend.
//
// Nothing is written to disk; frames live only in memory and are handed to
// the backend which discards them after computing metrics (privacy §6).

import 'dart:async';
import 'dart:html' as html;

class AttentionCamera {
  html.VideoElement? _video;
  html.MediaStream? _stream;
  html.CanvasElement? _canvas;

  /// Web always supports the getUserMedia path (subject to user permission).
  bool get isSupported => true;

  /// Whether the camera is currently streaming.
  bool get isRunning => _stream != null;

  /// Request the webcam and begin streaming into a hidden <video> element.
  /// Returns true on success, false if permission denied / no camera.
  Future<bool> start() async {
    if (_stream != null) return true;
    try {
      final mediaDevices = html.window.navigator.mediaDevices;
      if (mediaDevices == null) return false;

      final stream = await mediaDevices.getUserMedia(<String, dynamic>{
        'video': <String, dynamic>{
          'width': <String, dynamic>{'ideal': 640},
          'height': <String, dynamic>{'ideal': 480},
          'facingMode': 'user',
        },
        'audio': false,
      });

      final video = html.VideoElement()
        ..autoplay = true
        ..muted = true
        ..width = 640
        ..height = 480;
      // Required for autoplay on some browsers.
      video.setAttribute('playsinline', 'true');
      video.srcObject = stream;

      // Wait until the first frame is available so captures aren't blank.
      await video.onLoadedMetadata.first;
      await video.play();

      _stream = stream;
      _video = video;
      _canvas = html.CanvasElement(width: 640, height: 480);
      return true;
    } catch (_) {
      // Permission denied, no device, or insecure context.
      _cleanup();
      return false;
    }
  }

  /// Capture the current frame as a base64 JPEG data URL (or null if not ready).
  /// [quality] is 1-100 (JPEG quality); default 60 keeps payloads small.
  String? captureBase64({int quality = 60}) {
    final video = _video;
    final canvas = _canvas;
    if (video == null || canvas == null || _stream == null) return null;

    final vw = video.videoWidth;
    final vh = video.videoHeight;
    if (vw == 0 || vh == 0) return null;

    if (canvas.width != vw || canvas.height != vh) {
      canvas.width = vw;
      canvas.height = vh;
    }

    final ctx = canvas.context2D;
    ctx.drawImageScaled(video, 0, 0, vw, vh);
    // Returns e.g. "data:image/jpeg;base64,...."; backend strips the prefix.
    return canvas.toDataUrl('image/jpeg', quality / 100.0);
  }

  /// Stop the webcam and release all tracks/elements.
  void stop() => _cleanup();

  void _cleanup() {
    try {
      _stream?.getTracks().forEach((t) => t.stop());
    } catch (_) {}
    try {
      _video?.srcObject = null;
    } catch (_) {}
    _stream = null;
    _video = null;
    _canvas = null;
  }
}
