// ╔══════════════════════════════════════════════════════════════════╗
// ║         PRE-ASSESSMENT SCREEN — Phase 5                          ║
// ║  3 diagnostic MCQs before lecture starts                         ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../providers/lecture_provider.dart';
import '../../models/models.dart';

class PreAssessmentScreen extends ConsumerStatefulWidget {
  final String lectureId;

  const PreAssessmentScreen({super.key, required this.lectureId});

  @override
  ConsumerState<PreAssessmentScreen> createState() =>
      _PreAssessmentScreenState();
}

class _PreAssessmentScreenState extends ConsumerState<PreAssessmentScreen>
    with SingleTickerProviderStateMixin {
  int _currentIndex = 0;
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeInOut);
    _fadeCtrl.forward();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(lectureProvider.notifier)
          .generatePreQuiz(int.parse(widget.lectureId));
    });
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    super.dispose();
  }

  void _nextQuestion(int total) {
    if (_currentIndex < total - 1) {
      _fadeCtrl.reverse().then((_) {
        setState(() => _currentIndex++);
        _fadeCtrl.forward();
      });
    }
  }

  void _prevQuestion() {
    if (_currentIndex > 0) {
      _fadeCtrl.reverse().then((_) {
        setState(() => _currentIndex--);
        _fadeCtrl.forward();
      });
    }
  }

  Future<void> _submitAndProceed() async {
    await ref.read(lectureProvider.notifier).submitPreQuiz();
    if (mounted) {
      context.pushReplacement(
        '${AppConstants.routeLecturePlayer}/${widget.lectureId}',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final lectureState = ref.watch(lectureProvider);
    final theme = Theme.of(context);
    final questions = lectureState.preQuestions;
    final isLast = questions.isEmpty || _currentIndex == questions.length - 1;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            // ── Header ───────────────────────────────────────────────
            _buildHeader(theme, questions.length),

            // ── Progress bar ─────────────────────────────────────────
            if (questions.isNotEmpty) _buildProgressBar(theme, questions.length),

            // ── Content ──────────────────────────────────────────────
            Expanded(
              child: lectureState.isLoading
                  ? _buildLoading(theme)
                  : questions.isEmpty
                      ? _buildEmpty(theme)
                      : FadeTransition(
                          opacity: _fadeAnim,
                          child: _buildQuestion(
                              theme, questions[_currentIndex]),
                        ),
            ),

            // ── Bottom buttons ────────────────────────────────────────
            _buildBottomBar(theme, questions, isLast),
          ],
        ),
      ),
    );
  }

  // ── Header ──────────────────────────────────────────────────────

  Widget _buildHeader(ThemeData theme, int total) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              GestureDetector(
                onTap: () => context.pop(),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surface,
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.06),
                        blurRadius: 8,
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.arrow_back_ios_new_rounded,
                    size: 18,
                    color: theme.colorScheme.onSurface,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Before you begin...',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                    Text(
                      'Quick diagnostic — not graded!',
                      style: TextStyle(
                        fontSize: 13,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  total == 0 ? '— / —' : '${_currentIndex + 1} / $total',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ── Step progress bar ─────────────────────────────────────────────

  Widget _buildProgressBar(ThemeData theme, int total) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: List.generate(total, (i) {
          final filled = i <= _currentIndex;
          return Expanded(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: 4,
              margin: EdgeInsets.only(right: i < total - 1 ? 6 : 0),
              decoration: BoxDecoration(
                color: filled
                    ? theme.colorScheme.primary
                    : theme.colorScheme.primary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          );
        }),
      ),
    );
  }

  // ── Single question card ──────────────────────────────────────────

  Widget _buildQuestion(ThemeData theme, QuizQuestion q) {
    final answers = ref.watch(lectureProvider).preAnswers;
    final selected = answers[q.id];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          // Question text
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 12,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Text(
              q.questionText,
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface,
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(height: 20),
          // Options
          ...q.optionsList.map((entry) {
            final label = entry.key;
            final text = entry.value;
            final isSelected = selected == label;

            return GestureDetector(
              onTap: () => ref
                  .read(lectureProvider.notifier)
                  .setPreAnswer(q.id, label),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isSelected
                      ? theme.colorScheme.primary
                      : theme.colorScheme.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isSelected
                        ? theme.colorScheme.primary
                        : theme.colorScheme.outline.withOpacity(0.25),
                    width: isSelected ? 2 : 1,
                  ),
                  boxShadow: isSelected
                      ? [
                          BoxShadow(
                            color:
                                theme.colorScheme.primary.withOpacity(0.3),
                            blurRadius: 12,
                            offset: const Offset(0, 4),
                          ),
                        ]
                      : null,
                ),
                child: Row(
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isSelected
                            ? Colors.white.withOpacity(0.25)
                            : theme.colorScheme.primary.withOpacity(0.08),
                      ),
                      child: Center(
                        child: Text(
                          label,
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            color: isSelected
                                ? Colors.white
                                : theme.colorScheme.primary,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        text,
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                          color: isSelected
                              ? Colors.white
                              : theme.colorScheme.onSurface,
                        ),
                      ),
                    ),
                    if (isSelected)
                      const Icon(Icons.check_circle_rounded,
                          color: Colors.white, size: 20),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  // ── Bottom bar ────────────────────────────────────────────────────

  Widget _buildBottomBar(
      ThemeData theme, List<QuizQuestion> questions, bool isLast) {
    final lectureState = ref.watch(lectureProvider);

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius: 12,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: Row(
        children: [
          // Back / Skip
          if (_currentIndex > 0)
            Expanded(
              child: OutlinedButton(
                onPressed: _prevQuestion,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: const Text('Back'),
              ),
            )
          else
            Expanded(
              child: OutlinedButton(
                onPressed: questions.isEmpty ? null : _submitAndProceed,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: const Text('Skip All'),
              ),
            ),
          const SizedBox(width: 12),
          // Next / Start lecture
          Expanded(
            flex: 2,
            child: ElevatedButton(
              onPressed: lectureState.isLoading
                  ? null
                  : () {
                      if (isLast) {
                        _submitAndProceed();
                      } else {
                        _nextQuestion(questions.length);
                      }
                    },
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: lectureState.isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          isLast ? 'Start Lecture' : 'Next',
                          style: const TextStyle(
                              fontSize: 15, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(width: 6),
                        Icon(
                          isLast
                              ? Icons.play_arrow_rounded
                              : Icons.arrow_forward_rounded,
                          size: 20,
                        ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  // ── Loading ──────────────────────────────────────────────────────

  Widget _buildLoading(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: theme.colorScheme.primary),
          const SizedBox(height: 16),
          Text(
            'Generating questions...',
            style: TextStyle(
              color: theme.colorScheme.onSurfaceVariant,
              fontSize: 15,
            ),
          ),
        ],
      ),
    );
  }

  // ── Empty / Error ─────────────────────────────────────────────────

  Widget _buildEmpty(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.quiz_outlined,
              size: 64,
              color: theme.colorScheme.primary.withOpacity(0.4),
            ),
            const SizedBox(height: 16),
            Text(
              'No questions available',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tap "Start Lecture" to proceed',
              style: TextStyle(
                color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
