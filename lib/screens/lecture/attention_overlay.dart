// ╔══════════════════════════════════════════════════════════════════╗
// ║        ATTENTION OVERLAY — UI for the Presence/Attention Monitor  ║
// ║  Live badge + enroll/start dialog + Present/Absent verdict        ║
// ╚══════════════════════════════════════════════════════════════════╝
//
// These widgets/helpers drive the student-facing UX for the Attention &
// Presence Monitor. They read/drive `attentionProvider`. The heavy lifting
// (webcam capture + backend scoring) lives in the provider/service layer.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/attention_provider.dart';

// ════════════════════════════════════════════════════════════════════
//  LIVE BADGE — small pill shown while monitoring is active
// ════════════════════════════════════════════════════════════════════

class AttentionLiveBadge extends ConsumerWidget {
  const AttentionLiveBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final st = ref.watch(attentionProvider);
    if (!st.isMonitoring) return const SizedBox.shrink();

    final bool face = st.lastFaceDetected ?? false;
    final bool attentive = st.lastAttentive ?? false;
    final Color color = !face
        ? const Color(0xFFE53935) // red — no face
        : (attentive ? const Color(0xFF00C853) : const Color(0xFFFFB300));
    final String label = !face
        ? 'No face'
        : (attentive ? 'Attentive' : 'Distracted');
    final int pct = (st.liveRatio * 100).round();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.8), width: 1),
      ),

      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.remove_red_eye_rounded, color: color, size: 14),
          const SizedBox(width: 6),
          Text(
            '$label · $pct%',
            style: TextStyle(
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
//  START DIALOG — offer enrollment + start monitoring
// ════════════════════════════════════════════════════════════════════

/// Shows the attention start dialog. Returns true if monitoring was started.
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

  Future<void> _enrollThenStart() async {
    final notifier = ref.read(attentionProvider.notifier);
    setState(() {
      _busy = true;
      _step = 'Enrolling your face (look at the camera)…';
    });
    final ok = await notifier.enroll();
    if (!mounted) return;
    if (!ok) {
      final err = ref.read(attentionProvider).error ?? 'Enrollment failed.';
      setState(() {
        _busy = false;
        _step = '';
      });
      _toast(context, err);
      return;
    }
    setState(() => _step = 'Starting attention monitoring…');
    await notifier.startMonitoring(widget.lectureId);
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
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
            'This lecture can verify your presence and attentiveness using your '
            'webcam. Your video is never stored — only attendance metrics are saved.',
            style: TextStyle(fontSize: 13, height: 1.4),
          ),
          const SizedBox(height: 12),
          const Text(
            'First time? Enroll your face so we can recognize you. '
            'Already enrolled? Just start.',
            style: TextStyle(fontSize: 12, color: Colors.grey),
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
              TextButton(
                onPressed: _startOnly,
                child: const Text('Already enrolled'),
              ),
              FilledButton(
                onPressed: _enrollThenStart,
                child: const Text('Enroll & Start'),
              ),
            ],
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
