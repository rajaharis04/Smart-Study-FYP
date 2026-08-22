// ╔══════════════════════════════════════════════════════════════════╗
// ║        ATTENTION OVERLAY — UI for the Presence/Attention Monitor  ║
// ║  Live state panel + guided enrollment wizard + verdict dialog     ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// These widgets/helpers drive the student-facing UX for the Attention &
// Presence Monitor (v2). They read/drive `attentionProvider`. The heavy
// lifting (webcam capture + backend scoring) lives in the provider/service
// layer. This file focuses on clear, live, color-coded feedback:
//   • AttentionLiveBadge   — compact pill in the player top bar.
//   • AttentionLivePanel   — richer live card (state + %-ring + camera preview).
//   • showAttentionStartDialog / guided enrollment wizard.
//   • showAttentionVerdictDialog — end-of-session Present/Absent summary.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/attention_provider.dart';

// ════════════════════════════════════════════════════════════════════
//  STATE → COLOR / ICON / LABEL  (single source of truth for the UI)
// ════════════════════════════════════════════════════════════════════

class _StateStyle {
  final Color color;
  final IconData icon;
  final String label;
  const _StateStyle(this.color, this.icon, this.label);
}

_StateStyle _styleForState(String state, {bool? faceDetected, bool? attentive}) {
  switch (state) {
    case 'attentive':
      return const _StateStyle(Color(0xFF00C853), Icons.check_circle_rounded, 'Attentive');
    case 'looking_away':
      return const _StateStyle(Color(0xFFFFB300), Icons.visibility_off_rounded, 'Looking away');
    case 'eyes_closed':
      return const _StateStyle(Color(0xFFFFB300), Icons.remove_red_eye_outlined, 'Eyes closed');
    case 'drowsy':
      return const _StateStyle(Color(0xFFFF6D00), Icons.bedtime_rounded, 'Drowsy / sleepy');
    case 'no_face':
      return const _StateStyle(Color(0xFFE53935), Icons.person_off_rounded, 'No face');
    case 'multiple_faces':
      return const _StateStyle(Color(0xFFE53935), Icons.groups_rounded, 'Multiple faces');
    case 'not_you':
      return const _StateStyle(Color(0xFFE53935), Icons.no_accounts_rounded, 'Not you');
    case 'spoof':
      return const _StateStyle(Color(0xFFD500F9), Icons.photo_camera_back_rounded, 'Spoof?');
    case 'starting':
      return const _StateStyle(Color(0xFF42A5F5), Icons.hourglass_top_rounded, 'Starting…');
    default:
      // Fall back to the legacy face/attentive booleans if state is unknown.
      if (faceDetected == false) {
        return const _StateStyle(Color(0xFFE53935), Icons.person_off_rounded, 'No face');
      }
      if (attentive == true) {
        return const _StateStyle(Color(0xFF00C853), Icons.check_circle_rounded, 'Attentive');
      }
      return const _StateStyle(Color(0xFFFFB300), Icons.visibility_off_rounded, 'Distracted');
  }
}

// ════════════════════════════════════════════════════════════════════
//  LIVE BADGE — compact pill shown in the player top bar while monitoring
// ════════════════════════════════════════════════════════════════════

class AttentionLiveBadge extends ConsumerWidget {
  const AttentionLiveBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final st = ref.watch(attentionProvider);
    if (!st.isMonitoring) return const SizedBox.shrink();

    final style = _styleForState(
      st.liveState,
      faceDetected: st.lastFaceDetected,
      attentive: st.lastAttentive,
    );
    final int pct = (st.liveRatio * 100).round();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: style.color.withValues(alpha: 0.85), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(style.icon, color: style.color, size: 14),
          const SizedBox(width: 6),
          Text(
            '${style.label} · $pct%',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  LIVE PANEL — richer floating card: camera preview + state + ring
// ════════════════════════════════════════════════════════════════════

class AttentionLivePanel extends ConsumerWidget {
  const AttentionLivePanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final st = ref.watch(attentionProvider);
    if (!st.isMonitoring) return const SizedBox.shrink();

    final notifier = ref.read(attentionProvider.notifier);
    final style = _styleForState(
      st.liveState,
      faceDetected: st.lastFaceDetected,
      attentive: st.lastAttentive,
    );
    final int pct = (st.liveRatio * 100).round();

    return Container(
      width: 168,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.62),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: style.color.withValues(alpha: 0.7), width: 1.2),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Live camera preview thumbnail.
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: SizedBox(
              height: 96,
              child: notifier.cameraRunning
                  ? HtmlElementViewOrBlank(viewType: notifier.previewViewType)
                  : Container(color: Colors.black),
            ),
          ),
          const SizedBox(height: 8),
          // State row.
          Row(
            children: [
              Icon(style.icon, color: style.color, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  st.liveMessage.isNotEmpty ? st.liveMessage : style.label,
                  style: TextStyle(
                    color: style.color,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          // Attention ratio bar.
          Row(
            children: [
              const Text('Attention',
                  style: TextStyle(color: Colors.white70, fontSize: 10)),
              const Spacer(),
              Text('$pct%',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: st.liveRatio.clamp(0.0, 1.0),
              minHeight: 5,
              backgroundColor: Colors.white24,
              valueColor: AlwaysStoppedAnimation<Color>(style.color),
            ),
          ),
          // Contextual warnings.
          if (st.drowsy || st.spoofSuspected) ...[
            const SizedBox(height: 6),
            Text(
              st.spoofSuspected
                  ? '⚠ Spoof suspected — show your live face'
                  : '⚠ You look drowsy — sit up & focus',
              style: const TextStyle(color: Color(0xFFFFCC80), fontSize: 10),
            ),
          ],
        ],
      ),
    );
  }
}

/// Small helper that renders an HtmlElementView on web and a black box off-web,
/// so this file compiles on all platforms without importing dart:ui_web.
class HtmlElementViewOrBlank extends StatelessWidget {
  final String viewType;
  const HtmlElementViewOrBlank({super.key, required this.viewType});

  @override
  Widget build(BuildContext context) {
    // HtmlElementView is only meaningful on web; on other platforms the
    // camera is unsupported (stub) and this branch isn't reached in practice.
    try {
      return HtmlElementView(viewType: viewType);
    } catch (_) {
      return Container(color: Colors.black);
    }
  }
}

// ════════════════════════════════════════════════════════════════════
//  START FLOW — availability check → enroll (if needed) → monitor
// ════════════════════════════════════════════════════════════════════

/// Shows the attention start flow. Returns true if monitoring was started.
Future<bool> showAttentionStartDialog(
  BuildContext context,
  WidgetRef ref,
  int? lectureId,
) async {
  final notifier = ref.read(attentionProvider.notifier);
  await notifier.checkAvailability();
  final avail = ref.read(attentionProvider);

  if (!context.mounted) return false;

  // Gracefully explain when the feature can't run here.
  if (!avail.cameraSupported) {
    _toast(context, 'Attention monitoring needs a webcam (open on Chrome/Edge).');
    return false;
  }
  if (!avail.cvAvailable) {
    _toast(context,
        'Attention engine offline. Start the backend from the CV venv (.venv-attention).');
    return false;
  }

  final started = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => _AttentionStartDialog(lectureId: lectureId),
  );
  return started ?? false;
}

class _AttentionStartDialog extends ConsumerStatefulWidget {
  final int? lectureId;
  const _AttentionStartDialog({required this.lectureId});

  @override
  ConsumerState<_AttentionStartDialog> createState() =>
      _AttentionStartDialogState();
}

class _AttentionStartDialogState extends ConsumerState<_AttentionStartDialog> {
  bool _busy = false;
  String _step = '';

  Future<void> _startOnly() async {
    final notifier = ref.read(attentionProvider.notifier);
    setState(() {
      _busy = true;
      _step = 'Starting attention monitoring…';
    });
    await notifier.startMonitoring(widget.lectureId);
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  Future<void> _enrollFirst() async {
    // Launch the guided wizard; on success, start monitoring immediately.
    final ok = await showEnrollmentWizard(context, ref);
    if (!mounted) return;
    if (ok) {
      await _startOnly();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final st = ref.watch(attentionProvider);
    final alreadyEnrolled = st.enrolled;

    return AlertDialog(
      title: Row(
        children: [
          Icon(Icons.videocam_rounded, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          const Expanded(child: Text('Attention Monitoring')),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'This lecture verifies your presence and attentiveness using your '
            'webcam. Your video is never stored — only attendance metrics.',
            style: TextStyle(fontSize: 13, height: 1.4),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Icon(
                st.gazeActive ? Icons.visibility_rounded : Icons.remove_red_eye_outlined,
                size: 15,
                color: st.gazeActive ? const Color(0xFF00C853) : Colors.grey,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  st.gazeActive
                      ? 'Precise gaze tracking active.'
                      : 'Gaze tracking (basic). Full model optional.',
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            alreadyEnrolled
                ? 'You are enrolled ✓ — just start.'
                : 'First time: enroll your face (takes ~20s) so we can recognize you.',
            style: const TextStyle(fontSize: 12, color: Colors.grey),
          ),
          if (_busy) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(_step, style: const TextStyle(fontSize: 12))),
              ],
            ),
          ],
        ],
      ),
      actions: _busy
          ? const []
          : [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Skip'),
              ),
              if (alreadyEnrolled)
                FilledButton.icon(
                  onPressed: _startOnly,
                  icon: const Icon(Icons.play_arrow_rounded, size: 18),
                  label: const Text('Start'),
                )
              else
                FilledButton.icon(
                  onPressed: _enrollFirst,
                  icon: const Icon(Icons.face_retouching_natural_rounded, size: 18),
                  label: const Text('Enroll & Start'),
                ),
            ],
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  GUIDED ENROLLMENT WIZARD — live preview + posed steps
// ════════════════════════════════════════════════════════════════════

/// Shows the full-screen guided enrollment wizard. Returns true if enrollment
/// succeeded (embedding stored on the backend).
Future<bool> showEnrollmentWizard(BuildContext context, WidgetRef ref) async {
  final ok = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => const _EnrollmentWizard(),
  );
  return ok ?? false;
}

class _EnrollmentWizard extends ConsumerStatefulWidget {
  const _EnrollmentWizard();

  @override
  ConsumerState<_EnrollmentWizard> createState() => _EnrollmentWizardState();
}

class _EnrollmentWizardState extends ConsumerState<_EnrollmentWizard> {
  int _poseIndex = 0;
  bool _cameraReady = false;
  bool _busy = false;
  String _status = 'Starting camera…';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _initCamera());
  }

  Future<void> _initCamera() async {
    final notifier = ref.read(attentionProvider.notifier);
    final ok = await notifier.beginEnrollment();
    if (!mounted) return;
    setState(() {
      _cameraReady = ok;
      _status = ok
          ? 'Position your face in the circle.'
          : (ref.read(attentionProvider).error ?? 'Camera unavailable.');
    });
  }

  Future<void> _captureCurrentPose() async {
    if (_busy || !_cameraReady) return;
    final notifier = ref.read(attentionProvider.notifier);
    setState(() {
      _busy = true;
      _status = 'Capturing…';
    });
    final ok = await notifier.captureEnrollShot();
    if (!mounted) return;

    if (!ok) {
      setState(() {
        _busy = false;
        _status = 'Could not capture — try again.';
      });
      return;
    }

    final isLast = _poseIndex >= kEnrollmentPoses.length - 1;
    if (isLast) {
      setState(() => _status = 'Saving your face…');
      final done = await notifier.submitEnrollment();
      if (!mounted) return;
      if (done) {
        Navigator.of(context).pop(true);
      } else {
        setState(() {
          _busy = false;
          _poseIndex = 0; // let them retry from the start
          _status = ref.read(attentionProvider).error ?? 'Enrollment failed. Retry.';
        });
      }
    } else {
      setState(() {
        _poseIndex += 1;
        _busy = false;
        _status = 'Great! Next pose.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final notifier = ref.read(attentionProvider.notifier);
    final st = ref.watch(attentionProvider);
    final pose = kEnrollmentPoses[_poseIndex];
    final total = kEnrollmentPoses.length;

    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(Icons.face_retouching_natural_rounded,
                      color: theme.colorScheme.primary),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text('Enroll your face',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                  ),
                  Text('${st.enrollShotsTaken}/$total',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                'One-time setup. We capture $total quick poses to recognize you '
                'reliably. Your photos are never saved — only a math signature.',
                style: const TextStyle(fontSize: 12, color: Colors.grey, height: 1.4),
              ),
              const SizedBox(height: 14),

              // ── Live camera preview with a framing circle ──────────
              AspectRatio(
                aspectRatio: 4 / 3,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: _cameraReady && notifier.cameraRunning
                          ? HtmlElementViewOrBlank(viewType: notifier.previewViewType)
                          : Container(
                              color: Colors.black,
                              child: const Center(
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                            ),
                    ),
                    IgnorePointer(
                      child: Center(
                        child: Container(
                          width: 150,
                          height: 190,
                          decoration: BoxDecoration(
                            border: Border.all(
                                color: Colors.white.withValues(alpha: 0.85), width: 2),
                            borderRadius: BorderRadius.circular(100),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // ── Current pose instruction ───────────────────────────
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Text(pose.icon, style: const TextStyle(fontSize: 26)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Step ${_poseIndex + 1}: ${pose.title}',
                              style: const TextStyle(
                                  fontSize: 14, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 2),
                          Text(pose.hint,
                              style: const TextStyle(
                                  fontSize: 12, color: Colors.grey)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),

              // ── Progress dots ──────────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(total, (i) {
                  final done = i < st.enrollShotsTaken;
                  final current = i == _poseIndex;
                  return Container(
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    width: current ? 22 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: done
                          ? const Color(0xFF00C853)
                          : (current
                              ? theme.colorScheme.primary
                              : Colors.grey.withValues(alpha: 0.35)),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  );
                }),
              ),
              const SizedBox(height: 10),

              Text(_status,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 12),

              Row(
                children: [
                  TextButton(
                    onPressed: _busy
                        ? null
                        : () {
                            notifier.cancelEnrollment();
                            Navigator.of(context).pop(false);
                          },
                    child: const Text('Cancel'),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: (_busy || !_cameraReady) ? null : _captureCurrentPose,
                    icon: _busy
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.camera_alt_rounded, size: 18),
                    label: Text(
                      _poseIndex >= total - 1 ? 'Capture & Finish' : 'Capture',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  VERDICT DIALOG — shown after the session ends
// ════════════════════════════════════════════════════════════════════

Future<void> showAttentionVerdictDialog(
  BuildContext context,
  AttentionState st,
) async {
  if (st.status == null) return; // nothing to report (never started)
  final bool present = st.status == 'Present';
  final int pct = ((st.finalRatio ?? 0) * 100).round();

  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Row(
        children: [
          Icon(
            present ? Icons.check_circle_rounded : Icons.cancel_rounded,
            color: present ? const Color(0xFF00C853) : const Color(0xFFE53935),
          ),
          const SizedBox(width: 8),
          Text(present ? 'Present' : 'Absent'),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Attention ratio: $pct%', style: const TextStyle(fontSize: 14)),
          if (st.drowsyEvents > 0) ...[
            const SizedBox(height: 6),
            Text('Drowsy episodes: ${st.drowsyEvents}',
                style: const TextStyle(fontSize: 12, color: Color(0xFFFF6D00))),
          ],
          if (st.spoofFrames > 0) ...[
            const SizedBox(height: 6),
            Text('Spoof-suspected frames: ${st.spoofFrames}',
                style: const TextStyle(fontSize: 12, color: Color(0xFFD500F9))),
          ],
          if (st.flags.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Flags: ${st.flags.join(', ')}',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('OK'),
        ),
      ],
    ),
  );
}

// ── tiny snackbar helper ─────────────────────────────────────────────
void _toast(BuildContext context, String msg) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(msg), duration: const Duration(seconds: 4)),
  );
}
