// ╔══════════════════════════════════════════════════════════════════╗
// ║        ATTENTION PROVIDER — webcam presence/engagement (v2)       ║
// ║  Guided enrollment + session lifecycle + fps frame streaming      ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// Talks to the backend `/attention/*` endpoints (see api_service.dart) using
// frames captured by AttentionCamera (getUserMedia on web). Only derived
// metrics are ever stored server-side; frames are discarded after scoring.
//
// v2 upgrades:
//   • Fixes the live-state key bug (`is_attentive` was read as `attentive`).
//   • Surfaces the rich per-frame STATE (attentive / looking_away / drowsy /
//     eyes_closed / no_face / multiple_faces / not_you / spoof) + message so
//     the UI can tell the student EXACTLY what's happening, live.
//   • One-time GUIDED enrollment: checks enrollment status first; if needed,
//     walks the student through 5 posed shots (with an on-screen preview) and
//     THEN starts monitoring.
//   • Streams frames faster (config-driven ~3 fps) — the backend runs the
//     heavy models throttled so CPU stays comfortable.
//
// Lifecycle used by the lecture player:
//   1. checkAvailability()      → CV engine up? camera supported? enrolled?
//   2. enrollGuidedStep(i)      → capture one posed shot (with preview)
//   3. submitEnrollment()       → POST /enroll (5 photos)
//   4. startMonitoring(id)      → camera on + POST /session/start
//   5. (internal fps timer)     → POST /frame, updates live state
//   6. stopMonitoring()         → POST /session/end → Present/Absent verdict

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_service.dart';
import '../services/attention_camera.dart';

// ── Sampling cadence (backend throttles the heavy models internally) ─
const Duration _kFrameInterval = Duration(milliseconds: 350); // ~3 fps
const Duration _kEnrollGap = Duration(milliseconds: 250);

/// The guided enrollment poses. The student is asked to hold each pose while we
/// capture one (or more) shots — varied angles make a far more robust embedding.
const List<AttentionPose> kEnrollmentPoses = [
  AttentionPose(
    id: 'center',
    title: 'Look straight at the camera',
    hint: 'Keep your whole face in the circle, good lighting.',
    icon: '🙂',
  ),
  AttentionPose(
    id: 'left',
    title: 'Turn your head slightly LEFT',
    hint: 'Just a little — stay looking toward the screen.',
    icon: '👈',
  ),
  AttentionPose(
    id: 'right',
    title: 'Turn your head slightly RIGHT',
    hint: 'A small turn is enough.',
    icon: '👉',
  ),
  AttentionPose(
    id: 'up',
    title: 'Tilt your head slightly UP',
    hint: 'Chin up a touch.',
    icon: '👆',
  ),
  AttentionPose(
    id: 'smile',
    title: 'Look straight and smile',
    hint: 'Natural expression, face centered.',
    icon: '😄',
  ),
];

class AttentionPose {
  final String id;
  final String title;
  final String hint;
  final String icon;
  const AttentionPose({
    required this.id,
    required this.title,
    required this.hint,
    required this.icon,
  });
}

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
  final bool gazeActive;       // L2CS-Net gaze live on the backend

  // Live session values
  final int? sessionId;
  final bool cameraOn;
  final int framesSent;
  final bool? lastFaceDetected;
  final bool? lastAttentive;
  final String liveState;      // raw state id (e.g. "attentive", "drowsy")
  final String liveMessage;    // human text for the current (smoothed) state
  final double liveRatio;      // running attentive ratio (0..1)
  final double perclos;        // fatigue signal (0..1)
  final bool drowsy;
  final bool spoofSuspected;

  // Enrollment progress
  final int enrollShotsTaken;

  // Final verdict (after stopMonitoring)
  final String? status;        // "Present" | "Absent"
  final double? finalRatio;
  final List<String> flags;
  final int drowsyEvents;
  final int spoofFrames;

  final String? error;
  final String? notice;        // non-fatal, user-visible hint

  const AttentionState({
    this.phase = AttentionPhase.idle,
    this.cvAvailable = false,
    this.cameraSupported = false,
    this.enrolled = false,
    this.gazeActive = false,
    this.sessionId,
    this.cameraOn = false,
    this.framesSent = 0,
    this.lastFaceDetected,
    this.lastAttentive,
    this.liveState = 'idle',
    this.liveMessage = '',
    this.liveRatio = 0.0,
    this.perclos = 0.0,
    this.drowsy = false,
    this.spoofSuspected = false,
    this.enrollShotsTaken = 0,
    this.status,
    this.finalRatio,
    this.flags = const [],
    this.drowsyEvents = 0,
    this.spoofFrames = 0,
    this.error,
    this.notice,
  });

  bool get isMonitoring => phase == AttentionPhase.monitoring;

  AttentionState copyWith({
    AttentionPhase? phase,
    bool? cvAvailable,
    bool? cameraSupported,
    bool? enrolled,
    bool? gazeActive,
    int? sessionId,
    bool? cameraOn,
    int? framesSent,
    bool? lastFaceDetected,
    bool? lastAttentive,
    String? liveState,
    String? liveMessage,
    double? liveRatio,
    double? perclos,
    bool? drowsy,
    bool? spoofSuspected,
    int? enrollShotsTaken,
    String? status,
    double? finalRatio,
    List<String>? flags,
    int? drowsyEvents,
    int? spoofFrames,
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
      gazeActive: gazeActive ?? this.gazeActive,
      sessionId: sessionId ?? this.sessionId,
      cameraOn: cameraOn ?? this.cameraOn,
      framesSent: framesSent ?? this.framesSent,
      lastFaceDetected: lastFaceDetected ?? this.lastFaceDetected,
      lastAttentive: lastAttentive ?? this.lastAttentive,
      liveState: liveState ?? this.liveState,
      liveMessage: liveMessage ?? this.liveMessage,
      liveRatio: liveRatio ?? this.liveRatio,
      perclos: perclos ?? this.perclos,
      drowsy: drowsy ?? this.drowsy,
      spoofSuspected: spoofSuspected ?? this.spoofSuspected,
      enrollShotsTaken: enrollShotsTaken ?? this.enrollShotsTaken,
      status: status ?? this.status,
      finalRatio: finalRatio ?? this.finalRatio,
      flags: flags ?? this.flags,
      drowsyEvents: drowsyEvents ?? this.drowsyEvents,
      spoofFrames: spoofFrames ?? this.spoofFrames,
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

  // Photos captured during the guided enrollment (base64 JPEGs, in-memory).
  final List<String> _enrollShots = [];

  AttentionNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const AttentionState());

  /// Expose the platform-view type so the UI can embed a live camera preview.
  String get previewViewType => _camera.previewViewType;

  bool get cameraRunning => _camera.isRunning;

  /// Probe backend CV availability + platform camera support + enrollment.
  Future<void> checkAvailability() async {
    state = state.copyWith(phase: AttentionPhase.checking, clearError: true);
    bool cv = false;
    bool gaze = false;
    try {
      final status = await _api.getAttentionStatus();
      cv = status['cv_available'] == true;
      gaze = status['gaze_available'] == true;
    } catch (_) {
      cv = false;
    }

    bool enrolled = false;
    if (cv) {
      try {
        final enr = await _api.getEnrollmentStatus();
        enrolled = enr['enrolled'] == true;
      } catch (_) {
        enrolled = false;
      }
    }

    state = state.copyWith(
      phase: AttentionPhase.idle,
      cvAvailable: cv,
      gazeActive: gaze,
      cameraSupported: _camera.isSupported,
      enrolled: enrolled,
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  GUIDED ENROLLMENT
  // ──────────────────────────────────────────────────────────────────

  /// Turn the camera on for the enrollment wizard (so the preview shows).
  /// Returns true if the camera started.
  Future<bool> beginEnrollment() async {
    if (!_camera.isSupported) {
      state = state.copyWith(error: 'Camera not supported on this platform.');
      return false;
    }
    _enrollShots.clear();
    state = state.copyWith(
      phase: AttentionPhase.enrolling,
      enrollShotsTaken: 0,
      clearError: true,
      clearNotice: true,
    );
    final started = await _camera.start();
    if (!started) {
      state = state.copyWith(
        phase: AttentionPhase.idle,
        error: 'Could not access the webcam. Please allow camera permission.',
      );
      return false;
    }
    // Give the sensor a moment to auto-expose before the first shot.
    await Future<void>.delayed(const Duration(milliseconds: 500));
    return true;
  }

  /// Capture one shot for the current guided pose. Returns true if a usable
  /// frame was grabbed. (Quality/spoof validation happens server-side on submit.)
  Future<bool> captureEnrollShot() async {
    if (!_camera.isRunning) return false;
    // Two quick grabs, keep the second (lets exposure settle after any motion).
    _camera.captureBase64(quality: 85);
    await Future<void>.delayed(_kEnrollGap);
    final shot = _camera.captureBase64(quality: 85);
    if (shot == null) return false;
    _enrollShots.add(shot);
    state = state.copyWith(enrollShotsTaken: _enrollShots.length);
    return true;
  }

  /// Submit the captured shots to the backend to build the identity embedding.
  /// On success flips `enrolled=true`. Returns true on success.
  Future<bool> submitEnrollment() async {
    if (_enrollShots.length < 3) {
      state = state.copyWith(
        error: 'Need at least 3 clear photos. Please retake in good light.',
      );
      return false;
    }
    try {
      await _api.enrollFace(List<String>.from(_enrollShots));
      _enrollShots.clear();
      state = state.copyWith(
        enrolled: true,
        notice: 'Face enrolled successfully.',
      );
      return true;
    } catch (e) {
      state = state.copyWith(error: _msg(e));
      return false;
    }
  }

  /// Abort the enrollment wizard and release the camera (if not going straight
  /// into monitoring).
  void cancelEnrollment({bool stopCamera = true}) {
    _enrollShots.clear();
    if (stopCamera) _camera.stop();
    state = state.copyWith(phase: AttentionPhase.idle, enrollShotsTaken: 0);
  }

  // ──────────────────────────────────────────────────────────────────
  //  MONITORING
  // ──────────────────────────────────────────────────────────────────

  /// Start a monitored viewing session for [lectureId] and begin frames.
  /// If the camera isn't already running (e.g. straight after enrollment),
  /// it is started here.
  Future<void> startMonitoring(int? lectureId) async {
    if (!_camera.isSupported) return;
    if (state.isMonitoring) return;

    if (!_camera.isRunning) {
      final started = await _camera.start();
      if (!started) {
        state = state.copyWith(
          notice: 'Attention monitoring off (camera permission denied).',
        );
        return;
      }
      await Future<void>.delayed(const Duration(milliseconds: 400));
    }

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
        liveState: 'starting',
        liveMessage: 'Starting…',
        clearError: true,
        notice: unrecognized
            ? 'Face not recognized yet — please center your face.'
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
    final frame = _camera.captureBase64(quality: 55);
    if (frame == null) return;

    _sending = true;
    try {
      final res = await _api.sendAttentionFrame(sessionId: sid, imageBase64: frame);
      if (res != null) {
        // Backend sends BOTH `is_attentive` and legacy `attentive`; accept either.
        final attentive = (res['is_attentive'] ?? res['attentive']) == true;
        state = state.copyWith(
          framesSent: state.framesSent + 1,
          lastFaceDetected: res['face_detected'] == true,
          lastAttentive: attentive,
          liveState: (res['state'] as String?) ?? state.liveState,
          liveMessage: (res['message'] as String?) ?? state.liveMessage,
          liveRatio: (res['attention_ratio_so_far'] as num?)?.toDouble() ??
              state.liveRatio,
          perclos: (res['perclos'] as num?)?.toDouble() ?? state.perclos,
          drowsy: res['drowsy'] == true,
          spoofSuspected: res['spoof_suspected'] == true,
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
          drowsyEvents: (res['drowsy_events'] as num?)?.toInt() ?? 0,
          spoofFrames: (res['spoof_frames'] as num?)?.toInt() ?? 0,
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
