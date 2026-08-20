// ╔══════════════════════════════════════════════════════════════════╗
// ║        ATTENTION CAMERA — cross-platform webcam capture           ║
// ║  Web (Chrome): dart:html getUserMedia + canvas → base64 JPEG      ║
// ║  Mobile/desktop: stub (monitoring disabled until native camera)   ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// Uses a conditional export so the correct implementation is compiled per
// platform. The Attention & Presence Monitor streams ~1 fps frames to the
// backend `/attention/*` endpoints; only derived metrics are stored (privacy).
//
// The public surface (AttentionCamera) is identical in both implementations:
//   • bool  get isSupported
//   • Future<bool> start()
//   • String? captureBase64({int quality})   // JPEG data URL or null
//   • void  stop()

export 'attention_camera_stub.dart'
    if (dart.library.html) 'attention_camera_web.dart';
