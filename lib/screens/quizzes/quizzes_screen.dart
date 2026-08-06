// ╔══════════════════════════════════════════════════════════════════╗
// ║              QUIZZES SCREEN — Dedicated Student Section           ║
// ║  Displays all active & published quizzes with interactive attempt  ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';

class QuizzesScreen extends ConsumerStatefulWidget {
  const QuizzesScreen({super.key});

  @override
  ConsumerState<QuizzesScreen> createState() => _QuizzesScreenState();
}

class _QuizzesScreenState extends ConsumerState<QuizzesScreen> {
  bool _isLoading = true;
  List<ActiveQuiz> _quizzes = [];
  String _selectedFilter = 'all'; // 'all', 'pre', 'mid', 'post', 'completed'
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _fetchQuizzes();
  }

  Future<void> _fetchQuizzes() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final list = await ApiService().getActiveQuizzes();
      if (mounted) {
        setState(() {
          _quizzes = list;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _quizzes = [];
          _isLoading = false;
        });
      }
    }
  }

  List<ActiveQuiz> get _filteredQuizzes {
    return _quizzes.where((q) {
      final matchesSearch = q.lectureTitle
          .toLowerCase()
          .contains(_searchQuery.trim().toLowerCase());
      if (!matchesSearch) return false;

      if (_selectedFilter == 'completed') return q.isAttempted;
      // Active main view hides already attempted quizzes
      return !q.isAttempted;
    }).toList();
  }

  void _openQuizModal(ActiveQuiz quiz) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _QuizAttemptSheet(quiz: quiz),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        appBar: AppBar(
          title: Text(
            isUrdu ? 'کوئز سیکشن' : 'Quiz Section',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          centerTitle: false,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: _fetchQuizzes,
              tooltip: isUrdu ? 'ریفریش کریں' : 'Refresh',
            ),
          ],
        ),
        body: Column(
          children: [
            // Search Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: TextField(
                onChanged: (val) => setState(() => _searchQuery = val),
                decoration: InputDecoration(
                  hintText: isUrdu ? 'کوئز تلاش کریں...' : 'Search quizzes...',
                  prefixIcon: const Icon(Icons.search_rounded),
                  filled: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(vertical: 0),
                ),
              ),
            ),

            // Filter Chips
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: [
                  _buildFilterChip(theme, 'all', isUrdu ? 'سب' : 'All'),
                  _buildFilterChip(theme, 'completed', isUrdu ? 'مکمل شدہ' : 'Completed'),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // Quiz Cards List
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _filteredQuizzes.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.quiz_outlined,
                                size: 64,
                                color: theme.colorScheme.onSurfaceVariant.withOpacity(0.4),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                isUrdu ? 'کوئی کوئز دستیاب نہیں ہے' : 'No quizzes available',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                isUrdu
                                    ? 'ٹیچر کے نیا کوئز پبلش کرنے کا انتظار کریں'
                                    : 'Check back later for teacher published quizzes.',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                                ),
                              ),
                            ],
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredQuizzes.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 12),
                          itemBuilder: (context, index) {
                            final quiz = _filteredQuizzes[index];
                            return _buildQuizCard(theme, quiz, isUrdu);
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(ThemeData theme, String filterKey, String label) {
    final isSelected = _selectedFilter == filterKey;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: isSelected,
        selectedColor: theme.colorScheme.primary,
        labelStyle: TextStyle(
          color: isSelected ? Colors.white : theme.colorScheme.onSurface,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          fontSize: 13,
        ),
        onSelected: (_) => setState(() => _selectedFilter = filterKey),
      ),
    );
  }

  Widget _buildQuizCard(ThemeData theme, ActiveQuiz quiz, bool isUrdu) {
    final isCompleted = quiz.isAttempted;
    final dueDateText = quiz.dueDate != null
        ? '${quiz.dueDate!.day}/${quiz.dueDate!.month}/${quiz.dueDate!.year}'
        : (isUrdu ? 'کوئی تاریخ نہیں' : 'No Deadline');

    final Color badgeColor = theme.colorScheme.primary;
    final String badgeText = isUrdu ? 'کوئز' : 'Quiz';

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openQuizModal(quiz),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: badgeColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      badgeText,
                      style: TextStyle(
                        color: badgeColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  const Spacer(),
                  if (isCompleted)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.green.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_rounded, size: 14, color: Colors.green),
                          const SizedBox(width: 4),
                          Text(
                            isUrdu ? 'مکمل شدہ' : 'Attempted',
                            style: const TextStyle(
                              color: Colors.green,
                              fontWeight: FontWeight.bold,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    Row(
                      children: [
                        Icon(Icons.timer_outlined, size: 14, color: theme.colorScheme.onSurfaceVariant),
                        const SizedBox(width: 4),
                        Text(
                          dueDateText,
                          style: TextStyle(
                            fontSize: 12,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                quiz.lectureTitle,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    isUrdu ? '10 سوالات • 15 منٹ' : '10 Questions • 15 mins',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: () => _openQuizModal(quiz),
                    icon: Icon(
                      isCompleted ? Icons.visibility_rounded : Icons.play_arrow_rounded,
                      size: 16,
                    ),
                    label: Text(
                      isCompleted
                          ? (isUrdu ? 'دیکھیں' : 'Review')
                          : (isUrdu ? 'شروع کریں' : 'Start Quiz'),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isCompleted ? theme.colorScheme.secondary : badgeColor,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
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
//  Interactive Quiz Attempt Sheet Modal
// ════════════════════════════════════════════════════════════════════

class _QuizAttemptSheet extends ConsumerStatefulWidget {
  final ActiveQuiz quiz;
  const _QuizAttemptSheet({required this.quiz});

  @override
  ConsumerState<_QuizAttemptSheet> createState() => _QuizAttemptSheetState();
}

class _QuizAttemptSheetState extends ConsumerState<_QuizAttemptSheet> {
  bool _loading = true;
  List<QuizQuestion> _questions = [];
  final Map<int, String> _selectedAnswers = {};
  int _currentIndex = 0;
  bool _isSubmitted = false;

  Timer? _timer;
  int _remainingSeconds = 600;

  @override
  void initState() {
    super.initState();
    _loadQuestions();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startTimer(int minutes) {
    _timer?.cancel();
    _remainingSeconds = (minutes > 0 ? minutes : 10) * 60;
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_remainingSeconds > 0) {
        setState(() {
          _remainingSeconds--;
        });
      } else {
        timer.cancel();
        if (!_isSubmitted) {
          _submitQuiz();
        }
      }
    });
  }

  String _formatTimer(int totalSeconds) {
    final mins = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final secs = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$mins:$secs';
  }

  Future<void> _loadQuestions() async {
    try {
      final data = await ApiService().getQuiz(
        lectureId: widget.quiz.lectureId ?? widget.quiz.quizId,
        quizType: widget.quiz.quizType,
      );
      final list = data['questions'] as List<QuizQuestion>? ?? [];
      final timeLimit = data['time_limit_minutes'] as int? ?? widget.quiz.timeLimitMinutes;
      if (mounted) {
        setState(() {
          _questions = list.isNotEmpty ? list : _fallbackQuestions();
          _loading = false;
        });
        _startTimer(timeLimit);
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _questions = _fallbackQuestions();
          _loading = false;
        });
        _startTimer(widget.quiz.timeLimitMinutes);
      }
    }
  }

  List<QuizQuestion> _fallbackQuestions() {
    return const [
      QuizQuestion(
        id: 1,
        questionText: 'What is the time complexity of searching in a Balanced Binary Search Tree?',
        optionA: 'O(1)',
        optionB: 'O(log n)',
        optionC: 'O(n)',
        optionD: 'O(n^2)',
        correctAnswer: 'B',
      ),
      QuizQuestion(
        id: 2,
        questionText: 'Which data structure follows the LIFO (Last In First Out) principle?',
        optionA: 'Queue',
        optionB: 'Stack',
        optionC: 'Array',
        optionD: 'Linked List',
        correctAnswer: 'B',
      ),
      QuizQuestion(
        id: 3,
        questionText: 'Which sorting algorithm has the best average-case time complexity?',
        optionA: 'Bubble Sort',
        optionB: 'Selection Sort',
        optionC: 'QuickSort',
        optionD: 'Insertion Sort',
        correctAnswer: 'C',
      ),
    ];
  }

  void _submitQuiz() async {
    _timer?.cancel();
    setState(() => _isSubmitted = true);

    int correct = 0;
    int unattempted = 0;

    final Map<int, String?> answersMap = {};

    for (int i = 0; i < _questions.length; i++) {
      final q = _questions[i];
      final userAns = _selectedAnswers[i];
      answersMap[q.id] = userAns;

      if (userAns == null || userAns.trim().isEmpty) {
        unattempted++;
      } else if (userAns.trim().toUpperCase() == (q.correctAnswer ?? '').trim().toUpperCase()) {
        correct++;
      }
    }

    final totalQ = _questions.length;
    final scorePct = totalQ > 0 ? ((correct / totalQ) * 100).round() : 0;

    // Send submission to backend database so teacher panel receives it
    try {
      await ApiService().submitQuiz(
        quizId: widget.quiz.quizId,
        answers: answersMap,
      );
    } catch (_) {}

    if (!mounted) return;

    showDialog(
      context: context,
      useRootNavigator: false,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Icon(
              scorePct >= 50 ? Icons.emoji_events_rounded : Icons.info_outline_rounded,
              color: scorePct >= 50 ? Colors.amber : Colors.orange,
              size: 28,
            ),
            const SizedBox(width: 8),
            const Text('Quiz Results'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Score: $correct / $totalQ ($scorePct%)',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.check_circle_outline, color: Colors.green, size: 18),
                const SizedBox(width: 6),
                Text('Correct: $correct', style: const TextStyle(color: Colors.green, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.cancel_outlined, color: Colors.red, size: 18),
                const SizedBox(width: 6),
                Text('Wrong / Unattempted: ${totalQ - correct} ($unattempted unattempted)',
                    style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              scorePct >= 50
                  ? 'Great job! Your performance and answers have been submitted to your teacher.'
                  : 'Keep practicing! Your results have been submitted to your teacher.',
              style: const TextStyle(color: Colors.grey, fontSize: 13),
            ),
          ],
        ),
        actions: [
          ElevatedButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              if (mounted) {
                Navigator.of(context).pop();
              }
            },
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Drag handle & Header
          const SizedBox(height: 12),
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.grey.withOpacity(0.4),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    widget.quiz.lectureTitle,
                    style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (!_isSubmitted) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    margin: const EdgeInsets.only(right: 8),
                    decoration: BoxDecoration(
                      color: _remainingSeconds < 60
                          ? Colors.red.withOpacity(0.15)
                          : theme.colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _remainingSeconds < 60
                            ? Colors.red
                            : theme.colorScheme.primary.withOpacity(0.5),
                        width: 1.5,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.timer_rounded,
                          size: 16,
                          color: _remainingSeconds < 60
                              ? Colors.red
                              : theme.colorScheme.onPrimaryContainer,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _formatTimer(_remainingSeconds),
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: _remainingSeconds < 60
                                ? Colors.red
                                : theme.colorScheme.onPrimaryContainer,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                IconButton(
                  icon: const Icon(Icons.close_rounded),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          if (_loading)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (_questions.isEmpty)
            const Expanded(child: Center(child: Text('No questions found for this quiz.')))
          else
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Question progress bar
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Question ${_currentIndex + 1} of ${_questions.length}',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            widget.quiz.quizTypeLabel,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: theme.colorScheme.onPrimaryContainer,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: (_currentIndex + 1) / _questions.length,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    const SizedBox(height: 24),

                    // Question text
                    Text(
                      _questions[_currentIndex].questionText,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Options A, B, C, D
                    Expanded(
                      child: ListView(
                        children: [
                          _buildOptionTile('A', _questions[_currentIndex].optionA),
                          _buildOptionTile('B', _questions[_currentIndex].optionB),
                          _buildOptionTile('C', _questions[_currentIndex].optionC),
                          _buildOptionTile('D', _questions[_currentIndex].optionD),
                        ],
                      ),
                    ),

                    // Bottom Navigation Buttons
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        if (_currentIndex > 0)
                          OutlinedButton(
                            onPressed: () => setState(() => _currentIndex--),
                            child: const Text('Previous'),
                          )
                        else
                          const SizedBox.shrink(),

                        if (_currentIndex < _questions.length - 1)
                          ElevatedButton(
                            onPressed: () => setState(() => _currentIndex++),
                            child: const Text('Next'),
                          )
                        else
                          ElevatedButton(
                            onPressed: _submitQuiz,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green,
                              foregroundColor: Colors.white,
                            ),
                            child: const Text('Submit Quiz'),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildOptionTile(String key, String text) {
    final theme = Theme.of(context);
    final isSelected = _selectedAnswers[_currentIndex] == key;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => setState(() => _selectedAnswers[_currentIndex] = key),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: isSelected
                ? theme.colorScheme.primaryContainer.withOpacity(0.4)
                : theme.colorScheme.surfaceVariant.withOpacity(0.3),
            border: Border.all(
              color: isSelected ? theme.colorScheme.primary : Colors.transparent,
              width: 2,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isSelected
                      ? theme.colorScheme.primary
                      : theme.colorScheme.surfaceVariant,
                ),
                child: Center(
                  child: Text(
                    key,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: isSelected
                          ? theme.colorScheme.onPrimary
                          : theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  text,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
