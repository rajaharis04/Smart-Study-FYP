// ╔══════════════════════════════════════════════════════════════════╗
// ║         MID-CHECK OVERLAY — Phase 5                              ║
// ║  Fires at 50% watch, 2 questions, 30-sec timer                   ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:async';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/lecture_provider.dart';
import '../../models/models.dart';

class MidCheckOverlay extends ConsumerStatefulWidget {
  final List<QuizQuestion> questions;
  final VoidCallback onComplete;

  const MidCheckOverlay({
    super.key,
    required this.questions,
    required this.onComplete,
  });

  @override
  ConsumerState<MidCheckOverlay> createState() => _MidCheckOverlayState();
}

class _MidCheckOverlayState extends ConsumerState<MidCheckOverlay>
    with SingleTickerProviderStateMixin {
  static const _totalSeconds = 30;
  int _currentIndex = 0;
  int _secondsLeft = _totalSeconds;
  Timer? _timer;
  late AnimationController _slideCtrl;
  late Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();

    _slideCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideCtrl, curve: Curves.easeOutCubic));

    _slideCtrl.forward();
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    setState(() => _secondsLeft = _totalSeconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) {
        t.cancel();
        return;
      }
      setState(() => _secondsLeft--);
      if (_secondsLeft <= 0) {
        t.cancel();
        _autoSubmit();
      }
    });
  }

  void _autoSubmit() => _submit();

  void _submit() {
    _timer?.cancel();
    ref.read(lectureProvider.notifier).submitMidQuiz();
    widget.onComplete();
  }

  void _nextQuestion() {
    if (_currentIndex < widget.questions.length - 1) {
      setState(() => _currentIndex++);
      _startTimer();
    } else {
      _submit();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _slideCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLastQ = widget.questions.isEmpty ||
        _currentIndex == widget.questions.length - 1;

    return Stack(
      children: [
        // ── Blurred backdrop ─────────────────────────────────────────
        Positioned.fill(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
            child: Container(color: Colors.black.withOpacity(0.6)),
          ),
        ),

        // ── Overlay card ─────────────────────────────────────────────
        Center(
          child: SlideTransition(
            position: _slideAnim,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Container(
                width: double.infinity,
                constraints: const BoxConstraints(maxWidth: 520),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface,
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 40,
                      offset: const Offset(0, 16),
                    ),
                  ],
                ),
                child: widget.questions.isEmpty
                    ? _buildEmpty(theme)
                    : _buildContent(theme, isLastQ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildContent(ThemeData theme, bool isLastQ) {
    final q = widget.questions[_currentIndex];
    final midAnswers = ref.watch(lectureProvider).midAnswers;
    final selected = midAnswers[q.id];
    final timerColor = _secondsLeft <= 10 ? Colors.red : theme.colorScheme.primary;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF6B6B).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.bolt_rounded,
                        size: 16, color: Color(0xFFFF6B6B)),
                    const SizedBox(width: 4),
                    const Text(
                      'Quick Check!',
                      style: TextStyle(
                        color: Color(0xFFFF6B6B),
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              // Timer ring
              _buildTimerRing(timerColor),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Question ${_currentIndex + 1} of ${widget.questions.length}',
            style: TextStyle(
              fontSize: 12,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 16),
          // Question
          Text(
            q.questionText,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: theme.colorScheme.onSurface,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          // Options — 2 columns
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: 2.8,
            children: q.optionsList.map((entry) {
              final label = entry.key;
              final text = entry.value;
              final isSelected = selected == label;

              return GestureDetector(
                onTap: () => ref
                    .read(lectureProvider.notifier)
                    .setMidAnswer(q.id, label),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? theme.colorScheme.primary
                        : theme.colorScheme.primary.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isSelected
                          ? theme.colorScheme.primary
                          : theme.colorScheme.primary.withOpacity(0.2),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isSelected
                              ? Colors.white.withOpacity(0.25)
                              : theme.colorScheme.primary.withOpacity(0.12),
                        ),
                        child: Center(
                          child: Text(
                            label,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: isSelected
                                  ? Colors.white
                                  : theme.colorScheme.primary,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          text,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: isSelected
                                ? Colors.white
                                : theme.colorScheme.onSurface,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
          // Submit / Next button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _nextQuestion,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text(
                isLastQ ? 'Submit & Continue' : 'Next Question',
                style: const TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w700),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimerRing(Color color) {
    return SizedBox(
      width: 44,
      height: 44,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            value: _secondsLeft / _totalSeconds,
            strokeWidth: 3,
            backgroundColor: color.withOpacity(0.15),
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
          Text(
            '$_secondsLeft',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.check_circle_rounded,
              size: 60, color: Color(0xFF00BFA5)),
          const SizedBox(height: 16),
          const Text(
            "Great progress! Keep watching.",
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: widget.onComplete,
            child: const Text('Continue Lecture'),
          ),
        ],
      ),
    );
  }
}
