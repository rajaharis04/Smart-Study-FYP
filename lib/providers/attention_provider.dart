// ╔══════════════════════════════════════════════════════════════════╗
// ║        ATTENTION PROVIDER — webcam presence/engagement            ║
// ║  Enrollment + session lifecycle + ~1 fps frame streaming          ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// Talks to the backend `/attention/*` endpoints (see api_service.dart) using
// frames captured by AttentionCamera (getUserMedia on web). Only derived
// metrics are ever stored server-side; frames are discarded after scoring.
//
// Lifecycle used by the lecture player:
//   1. checkAvailability()  → is CV engine up + camera supported?
//   2. enroll()             → one-time face registration (3-5 photos)
//   3. startMonitoring(lectureId) → camera on + POST /session/start
//   4. (internal 1 fps timer) → POST /frame, updates live ratio
//   5. stopMonitoring()     → POST /session/end → Present/Absent verdict

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_service.dart';
import '../services/attention_camera.dart';

// ── Sampling cadence (backend samples ~1 fps per spec) ───────────────
const Duration _kFrameInterval = Duration(seconds: 1);
const int _kEnrollmentPhotos = 5;
const Duration _kEnrollGap = Duration(milliseconds: 500);

// ════════════════════════════════════════════════════════════════════
//  State
// ════════════════════════════════════════════════════════════════════

enum AttentionPhase { idle, checking, enrolling, monitoring, ended }

class AttentionState {
  final AttentionPhase phase;

  // Capability flags
  final bool cvAvailable;      // backend CV engine reachable
  final bool cameraSupported;  // platform supports webcam capture
  final bool enrolled;         // this student has a registered face

  // Live session values
  final int? sessionId;
  final bool cameraOn;
  final int framesSent;
  final bool? lastFaceDetected;
  final bool? lastAttentive;
  final double liveRatio;      // running attentive ratio (0..1)

  // Final verdict (after stopMonitoring)
  final String? status;        // "Present" | "Absent"
  final double? finalRatio;
  final List<String> flags;

  final String? error;
  final String? notice;        // non-fatal, user-visible hint

  const AttentionState({
    this.phase = AttentionPhase.idle,
    this.cvAvailable = false,
    this.cameraSupported = false,
    this.enrolled = false,
    this.sessionId,
    this.cameraOn = false,
    this.framesSent = 0,
    this.lastFaceDetected,
    this.lastAttentive,
    this.liveRatio = 0.0,
    this.status,
    this.finalRatio,
    this.flags = const [],
    this.error,
    this.notice,
  });

  bool get isMonitoring => phase == AttentionPhase.monitoring;

  AttentionState copyWith({
    AttentionPhase? phase,
    bool? cvAvailable,
    bool? cameraSupported,
    bool? enrolled,
    int? sessionId,
    bool? cameraOn,
    int? framesSent,
    bool? lastFaceDetected,
    bool? lastAttentive,
    double? liveRatio,
    String? status,
    double? finalRatio,
    List<String>? flags,
    String? error,
    bool clearError = false,
    String? notice,
    bool clearNotice = false,
  }) {
    return AttentionState(
      phase: phase ?? this.phase,
      cvAvailable: cvAvailable ?? this.cvAvailable,
      cameraSupported: cameraSupported ?? this.cameraSupported,
      enrolled: enrolled ?? this.enrolled,
      sessionId: sessionId ?? this.sessionId,
      cameraOn: cameraOn ?? this.cameraOn,
      framesSent: framesSent ?? this.framesSent,
      lastFaceDetected: lastFaceDetected ?? this.lastFaceDetected,
      lastAttentive: lastAttentive ?? this.lastAttentive,
      liveRatio: liveRatio ?? this.liveRatio,
      status: status ?? this.status,
      finalRatio: finalRatio ?? this.finalRatio,
      flags: flags ?? this.flags,
      error: clearError ? null : (error ?? this.error),
      notice: clearNotice ? null : (notice ?? this.notice),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  Notifier
// ════════════════════════════════════════════════════════════════════

class AttentionNotifier extends StateNotifier<AttentionState> {
  final ApiService _api;
  final AttentionCamera _camera = AttentionCamera();
  Timer? _frameTimer;
  bool _sending = false; // guard against overlapping frame posts

  AttentionNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const AttentionState());

  /// Probe backend CV availability + platform camera support.
  Future<void> checkAvailability() async {
    state = state.copyWith(phase: AttentionPhase.checking, clearError: true);
    bool cv = false;
    try {
      final status = await _api.getAttentionStatus();
      cv = status['cv_available'] == true;
    } catch (_) {
      cv = false;
    }
    state = state.copyWith(
      phase: AttentionPhase.idle,
      cvAvailable: cv,
      cameraSupported: _camera.isSupported,
    );
  }

  /// One-time enrollment: capture [_kEnrollmentPhotos] frames and register.
  /// Returns true on success.
  Future<bool> enroll() async {
    if (!_camera.isSupported) {
      state = state.copyWith(error: 'Camera not supported on this platform.');
      return false;
    }
    state = state.copyWith(phase: AttentionPhase.enrolling, clearError: true, clearNotice: true);

    final started = await _camera.start();
    if (!started) {
      state = state.copyWith(
        phase: AttentionPhase.idle,
        error: 'Could not access the webcam. Please allow camera permission.',
      );
      return false;
    }

    // Give the sensor a moment to auto-expose before the first shot.
    await Future<void>.delayed(const Duration(milliseconds: 600));

    final photos = <String>[];
    for (var i = 0; i < _kEnrollmentPhotos; i++) {
      final shot = _camera.captureBase64(quality: 80);
      if (shot != null) photos.add(shot);
      await Future<void>.delayed(_kEnrollGap);
    }

    _camera.stop();

    if (photos.length < 3) {
      state = state.copyWith(
        phase: AttentionPhase.idle,
        error: 'Could not capture enough clear photos. Try again in good light.',
      );
      return false;
    }

    try {
      await _api.enrollFace(photos);
      state = state.copyWith(
        phase: AttentionPhase.idle,
        enrolled: true,
        notice: 'Face enrolled successfully.',
      );
      return true;
    } catch (e) {
      state = state.copyWith(phase: AttentionPhase.idle, error: _msg(e));
      return false;
    }
  }

  /// Start a monitored viewing session for [lectureId] and begin 1 fps frames.
  Future<void> startMonitoring(int? lectureId) async {
    if (!_camera.isSupported) return;
    if (state.isMonitoring) return;

    final started = await _camera.start();
    if (!started) {
      state = state.copyWith(
        notice: 'Attention monitoring off (camera permission denied).',
      );
      return;
    }

    await Future<void>.delayed(const Duration(milliseconds: 500));
    final firstFrame = _camera.captureBase64(quality: 70);

    try {
      final res = await _api.startAttentionSession(
        lectureId: lectureId,
        imageBase64: firstFrame,
      );
      final sid = res['session_id'] as int?;
      final unrecognized = res['unrecognized_viewer'] == true;

      state = state.copyWith(
        phase: AttentionPhase.monitoring,
        sessionId: sid,
        cameraOn: true,
        framesSent: 0,
        liveRatio: 0.0,
        clearError: true,
        notice: unrecognized
            ? 'Viewer not recognized — please ensure your face is visible.'
            : null,
      );

      _frameTimer?.cancel();
      _frameTimer = Timer.periodic(_kFrameInterval, (_) => _tick());
    } catch (e) {
      _camera.stop();
      state = state.copyWith(cameraOn: false, notice: _msg(e));
    }
  }

  /// Internal: capture + POST one frame, fold in the returned metrics.
  Future<void> _tick() async {
    final sid = state.sessionId;
    if (sid == null || _sending) return;
    final frame = _camera.captureBase64(quality: 60);
    if (frame == null) return;

    _sending = true;
    try {
      final res = await _api.sendAttentionFrame(sessionId: sid, imageBase64: frame);
      if (res != null) {
        state = state.copyWith(
          framesSent: state.framesSent + 1,
          lastFaceDetected: res['face_detected'] == true,
          lastAttentive: res['attentive'] == true,
          liveRatio: (res['attention_ratio_so_far'] as num?)?.toDouble() ??
              state.liveRatio,
        );
      }
    } finally {
      _sending = false;
    }
  }

  /// Stop the session: kill the timer, release the camera, finalize verdict.
  Future<void> stopMonitoring() async {
    _frameTimer?.cancel();
    _frameTimer = null;
    final sid = state.sessionId;
    _camera.stop();

    if (sid == null) {
      state = state.copyWith(phase: AttentionPhase.ended, cameraOn: false);
      return;
    }

    try {
      final res = await _api.endAttentionSession(sid);
      if (res != null) {
        state = state.copyWith(
          phase: AttentionPhase.ended,
          cameraOn: false,
          status: res['status'] as String?,
          finalRatio: (res['attention_ratio'] as num?)?.toDouble(),
          flags: ((res['flags'] as List<dynamic>?) ?? const [])
              .map((e) => e.toString())
              .toList(),
        );
      } else {
        state = state.copyWith(phase: AttentionPhase.ended, cameraOn: false);
      }
    } catch (_) {
      state = state.copyWith(phase: AttentionPhase.ended, cameraOn: false);
    }
  }

  String _msg(Object e) {
    final s = e.toString();
    return s.startsWith('Exception: ') ? s.replaceFirst('Exception: ', '') : s;
  }

  @override
  void dispose() {
    _frameTimer?.cancel();
    _camera.stop();
    super.dispose();
  }
}

// ════════════════════════════════════════════════════════════════════
//  Provider (autoDispose so camera/timer stop when player closes)
// ════════════════════════════════════════════════════════════════════

final attentionProvider =
    StateNotifierProvider.autoDispose<AttentionNotifier, AttentionState>(
  (ref) => AttentionNotifier(),
);
