// ╔══════════════════════════════════════════════════════════════════╗
// ║   ATTENTION CAMERA — non-web STUB (mobile / desktop)              ║
// ║  Attention monitoring currently targets Flutter Web (getUserMedia)║
// ╚══════════════════════════════════════════════════════════════════╝
//
// Compiled on every non-web platform via the conditional export in
// attention_camera.dart. It reports `isSupported == false` so the UI can
// gracefully hide/disable the Attention Monitor on mobile/desktop until a
// native camera integration (e.g. the `camera` package) is added.

import 'dart:async';

class AttentionCamera {
  /// Not supported off-web (no browser getUserMedia).
  bool get isSupported => false;

  bool get isRunning => false;

  Future<bool> start() async => false;

  String? captureBase64({int quality = 60}) => null;

  void stop() {}
}
