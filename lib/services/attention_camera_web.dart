// ╔══════════════════════════════════════════════════════════════════╗
// ║     ATTENTION CAMERA — WEB implementation (Chrome/Edge)           ║
// ║  getUserMedia → hidden <video> → <canvas> → base64 JPEG frames    ║
// ║  + a live on-screen PREVIEW via an HtmlElementView platform view  ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// This is compiled ONLY on Flutter Web (selected via the conditional export
// in attention_camera.dart). It grabs the webcam with the standard browser
// MediaDevices API, draws the current video frame onto an offscreen canvas,
// and returns a base64 data-URL JPEG that we POST to the backend.
//
// NEW (v2): the same live <video> element is also embedded into the Flutter
// widget tree as a platform view (HtmlElementView) so the student can SEE
// themselves — used by the guided enrollment wizard and the live monitor
// thumbnail. Nothing is written to disk; frames live only in memory.

import 'dart:async';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

class AttentionCamera {
  html.VideoElement? _video;
  html.MediaStream? _stream;
  html.CanvasElement? _canvas;
  late final html.DivElement _container;

  // A unique platform-view type per instance so multiple cameras (e.g. after
  // an autoDispose re-create) never clash on a duplicate factory registration.
  static int _instanceSeq = 0;
  late final String _viewType;
  bool _factoryRegistered = false;

  AttentionCamera() {
    _viewType = 'attention-camera-preview-${_instanceSeq++}';
    _container = html.DivElement()
      ..style.width = '100%'
      ..style.height = '100%'
      ..style.backgroundColor = '#000'
      ..style.overflow = 'hidden'
      ..style.borderRadius = '12px';
    _registerFactory();
  }

  /// The platform-view type to feed into a Flutter `HtmlElementView`.
  String get previewViewType => _viewType;

  /// Web always supports the getUserMedia path (subject to user permission).
  bool get isSupported => true;

  /// Whether the camera is currently streaming.
  bool get isRunning => _stream != null;

  void _registerFactory() {
    if (_factoryRegistered) return;
    try {
      ui_web.platformViewRegistry.registerViewFactory(
        _viewType,
        (int viewId) => _container,
      );
      _factoryRegistered = true;
    } catch (_) {
      // Already registered (hot reload) — safe to ignore.
      _factoryRegistered = true;
    }
  }

  /// Request the webcam and begin streaming into a <video> element that is
  /// both captured from AND shown in the preview container.
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
        // Fill the preview container while keeping aspect (mirror like a selfie).
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.objectFit = 'cover'
        ..style.transform = 'scaleX(-1)';
      // Required for autoplay on some browsers.
      video.setAttribute('playsinline', 'true');
      video.srcObject = stream;

      // Wait until the first frame is available so captures aren't blank.
      await video.onLoadedMetadata.first;
      await video.play();

      _stream = stream;
      _video = video;
      _canvas = html.CanvasElement(width: 640, height: 480);

      // Mount the live video into the preview container.
      _container.children.clear();
      _container.append(video);
      return true;
    } catch (_) {
      // Permission denied, no device, or insecure context.
      _cleanup();
      return false;
    }
  }

  /// Capture the current frame as a base64 JPEG data URL (or null if not ready).
  /// [quality] is 1-100 (JPEG quality); default 60 keeps payloads small.
  ///
  /// NOTE: we draw the UNMIRRORED frame to the canvas (the CSS mirror is only a
  /// UI nicety); the backend sees a normal, correctly-oriented image.
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
    try {
      _container.children.clear();
    } catch (_) {}
    _stream = null;
    _video = null;
    _canvas = null;
  }
}
