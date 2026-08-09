// ╔══════════════════════════════════════════════════════════════════╗
// ║              QUIZZES SCREEN — Dedicated Student Section           ║
// ║  Displays all active & published quizzes with interactive attempt  ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:async';
import 'dart:io' show Platform;
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';
import '../../services/ai_proctoring_service.dart';

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
    final settings = ref.read(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    if (quiz.isAttempted) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            isUrdu
                ? 'کوئز مکمل ہو چکا ہے! آپ گریڈز سیکشن میں نمبرز دیکھ سکتے ہیں۔'
                : 'Quiz already completed! You can check your marks in Grades section.',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
          backgroundColor: Colors.green.shade800,
          duration: const Duration(seconds: 3),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    final agreed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.shield_outlined, color: Colors.indigo, size: 28),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                isUrdu ? 'امتحانی قوانین و معاہدہ' : 'Anti-Cheating Rules & Agreement',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isUrdu
                    ? 'کوئز شروع کرنے سے پہلے سیکیورٹی قوانین کو دھیان سے پڑھیں:'
                    : 'Please read and agree to the exam security rules before starting:',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 14),
              _buildRuleRow(
                icon: Icons.cancel_outlined,
                color: Colors.red,
                text: isUrdu
                    ? 'ایپ / ٹیب سوئچنگ پر پابندی: کوئز کے دوران سکرین چھوڑنے یا دوسری ایپ کھولنے پر کوئز 0 نمبروں کے ساتھ فوری منسوخ کر دیا جائے گا۔'
                    : 'No App/Tab Switching: Minimizing app, opening split-screen, or switching tabs will IMMEDIATELY submit your quiz with 0 marks.',
              ),
              const SizedBox(height: 10),
              _buildRuleRow(
                icon: Icons.photo_camera_front_outlined,
                color: Colors.orange,
                text: isUrdu
                    ? 'سکرین شاٹ و ریکارڈنگ بلاک: سکرین شاٹ یا سکرین ریکارڈنگ کرنے پر سکرین بلیک (Black) ہو جائے گی۔'
                    : 'Screenshots & Screen Recording Blocked: Any recording or screenshot attempt will turn the screen black.',
              ),
              const SizedBox(height: 10),
              _buildRuleRow(
                icon: Icons.copy_outlined,
                color: Colors.purple,
                text: isUrdu
                    ? 'کاپی پیسٹ کی ممانعت: سوالات کا متن کاپی یا سلیکٹ کرنا مکمل طور پر معطل ہے۔'
                    : 'No Copying: Text selection and copying question text are completely disabled.',
              ),
              const SizedBox(height: 10),
              _buildRuleRow(
                icon: Icons.timer_outlined,
                color: Colors.blue,
                text: isUrdu
                    ? 'ہر سوال کا الگ ٹائمر: ہر سوال کا ٹائمر ختم ہوتے ہی اگلا سوال آئے گا اور پچھلا سوال لاک ہو جائے گا۔'
                    : 'Per-Question Hard Timer: Each question has a fixed time limit. Previous questions are strictly locked.',
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(isUrdu ? 'منسوخ' : 'Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.indigo,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text(isUrdu ? 'میں متفق ہوں • شروع کریں' : 'I Agree & Start Quiz'),
          ),
        ],
      ),
    );

    if (agreed == true && mounted) {
      await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        isDismissible: false,
        enableDrag: false,
        backgroundColor: Colors.transparent,
        builder: (context) => _QuizAttemptSheet(quiz: quiz),
      );
      if (mounted) {
        _fetchQuizzes();
      }
    }
  }

  Widget _buildRuleRow({required IconData icon, required Color color, required String text}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 12, height: 1.35, fontWeight: FontWeight.w500),
          ),
        ),
      ],
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
                            isUrdu ? 'کوئز مکمل ہو گیا' : 'Quiz Completed',
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
                    isUrdu
                        ? '${quiz.perQuestionTimerSeconds} سیکنڈ / سوال'
                        : '${quiz.perQuestionTimerSeconds}s / question',
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
                          ? (isUrdu ? 'کوئز مکمل ہو گیا' : 'Quiz Completed')
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

class _QuizAttemptSheetState extends ConsumerState<_QuizAttemptSheet> with WidgetsBindingObserver {
  static const MethodChannel _securityChannel = MethodChannel('com.smartstudy.security');

  bool _loading = true;
  int? _actualQuizId;
  List<QuizQuestion> _questions = [];
  final Map<int, String> _selectedAnswers = {};
  final Map<int, List<MapEntry<String, String>>> _shuffledOptionsMap = {};
  int _currentIndex = 0;
  bool _isSubmitted = false;

  Timer? _questionTimer;
  int _secondsPerQuestion = 30;
  int _questionRemainingSeconds = 30;

  late final AIProctoringService _proctoringService;
  int _proctoringWarningsCount = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _enableSecurityFeatures();
    _initAIProctoring();
    _loadQuestions();
  }

  void _initAIProctoring() {
    _proctoringService = AIProctoringService(
      onWarning: (warningCount, title, details) {
        if (_isSubmitted) return;
        setState(() {
          _proctoringWarningsCount = warningCount;
        });

        // Log to backend
        ApiService().logProctoringViolation(
          quizId: widget.quiz.quizId,
          violationType: 'AI_WARNING',
          details: details,
          warningCount: warningCount,
        );

        ScaffoldMessenger.of(context).clearSnackBars();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: Colors.black87),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'AI Warning ($warningCount/3): $details',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black87),
                  ),
                ),
              ],
            ),
            backgroundColor: Colors.amber.shade300,
            duration: const Duration(seconds: 4),
            behavior: SnackBarBehavior.floating,
          ),
        );
      },
      onTerminated: (reason) {
        if (_isSubmitted) return;
        setState(() {
          _proctoringWarningsCount = 3;
        });
        ApiService().logProctoringViolation(
          quizId: widget.quiz.quizId,
          violationType: 'AI_TERMINATED',
          details: reason,
          warningCount: 3,
        );
        _handleSecurityViolation(reason);
      },
    );
    _proctoringService.startProctoring();
  }

  @override
  void dispose() {
    _proctoringService.stopProctoring();
    WidgetsBinding.instance.removeObserver(this);
    _disableSecurityFeatures();
    _questionTimer?.cancel();
    super.dispose();
  }

  void _enableSecurityFeatures() async {
    try {
      // Enter immersive sticky mode — hides system bars
      await SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
      // Enable native secure mode (FLAG_SECURE on Android, overlay protection on iOS)
      await _securityChannel.invokeMethod('enableSecure');
      // On Android, also request screen pinning (locks app to foreground)
      if (Platform.isAndroid) {
        try {
          await _securityChannel.invokeMethod('requestScreenPin');
        } catch (_) {
          // Screen pinning may not be available on all devices
        }
      }
    } catch (_) {}
  }

  void _disableSecurityFeatures() async {
    try {
      await SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
      await _securityChannel.invokeMethod('disableSecure');
    } catch (_) {}
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_isSubmitted) return;
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive ||
        state == AppLifecycleState.detached ||
        state == AppLifecycleState.hidden) {
      _handleSecurityViolation(
        'App or Tab switching detected! Your quiz attempt has been auto-submitted with 0 marks.',
      );
    }
  }

  void _handleSecurityViolation(String reason) async {
    if (_isSubmitted) return;
    _questionTimer?.cancel();
    setState(() => _isSubmitted = true);
    _disableSecurityFeatures();

    // Submit proctoring violation log & empty answers / 0 marks to backend
    try {
      await ApiService().logProctoringViolation(
        quizId: widget.quiz.quizId,
        violationType: 'SECURITY_VIOLATION',
        details: reason,
        warningCount: 3,
      );
      await ApiService().submitQuiz(
        quizId: widget.quiz.quizId,
        answers: {},
      );
    } catch (_) {}

    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.block_rounded, color: Colors.red, size: 30),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Quiz Cancelled',
                style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Security Violation Detected!',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.red),
            ),
            const SizedBox(height: 8),
            Text(
              reason,
              style: const TextStyle(fontSize: 13, color: Colors.black87),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: const Row(
                children: [
                  Icon(Icons.cancel, color: Colors.red, size: 18),
                  SizedBox(width: 6),
                  Text(
                    'Score Assigned: 0 Marks (Cancelled)',
                    style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red, fontSize: 12),
                  ),
                ],
              ),
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
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _startQuestionTimer() {
    _questionTimer?.cancel();
    setState(() {
      _questionRemainingSeconds = _secondsPerQuestion;
    });

    _questionTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }

      if (_questionRemainingSeconds > 1) {
        setState(() {
          _questionRemainingSeconds--;
        });
      } else {
        timer.cancel();
        _handleQuestionTimeExpired();
      }
    });
  }

  void _saveCurrentQuestionAnswer() {
    if (_currentIndex < 0 || _currentIndex >= _questions.length) return;
    final q = _questions[_currentIndex];
    final userAns = _selectedAnswers[_currentIndex];
    ApiService().saveQuestionAnswer(
      quizId: _actualQuizId ?? widget.quiz.quizId,
      questionId: q.id,
      answer: userAns,
      timeTakenSeconds: (_secondsPerQuestion - _questionRemainingSeconds).toDouble(),
    );
  }

  void _handleQuestionTimeExpired() {
    if (_isSubmitted) return;
    _saveCurrentQuestionAnswer();

    if (_currentIndex < _questions.length - 1) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Time expired for Q${_currentIndex + 1}! Moving to next question.',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
          backgroundColor: Colors.orange.shade800,
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
      setState(() {
        _currentIndex++;
      });
      _startQuestionTimer();
    } else {
      // Last question timer expired -> Auto submit
      _submitQuiz();
    }
  }

  void _goToNextQuestion() {
    if (_isSubmitted) return;
    _saveCurrentQuestionAnswer();

    if (_currentIndex < _questions.length - 1) {
      setState(() {
        _currentIndex++;
      });
      _startQuestionTimer();
    } else {
      _submitQuiz();
    }
  }

  Future<void> _loadQuestions() async {
    try {
      final data = await ApiService().getQuizById(widget.quiz.quizId);
      final fetchedQuizId = data['quiz_id'] as int?;
      if (fetchedQuizId != null) {
        _actualQuizId = fetchedQuizId;
      }
      final list = data['questions'] as List<QuizQuestion>? ?? [];
      final perQSecs = data['per_question_timer_seconds'] as int? ?? widget.quiz.perQuestionTimerSeconds;

      if (mounted) {
        final loadedQuestions = List<QuizQuestion>.from(list.isNotEmpty ? list : _fallbackQuestions());

        _shuffledOptionsMap.clear();
        for (int i = 0; i < loadedQuestions.length; i++) {
          final q = loadedQuestions[i];
          final opts = <MapEntry<String, String>>[
            if (q.optionA.trim().isNotEmpty) MapEntry('A', q.optionA),
            if (q.optionB.trim().isNotEmpty) MapEntry('B', q.optionB),
            if (q.optionC.trim().isNotEmpty) MapEntry('C', q.optionC),
            if (q.optionD.trim().isNotEmpty) MapEntry('D', q.optionD),
          ];
          _shuffledOptionsMap[i] = opts;
        }

        setState(() {
          _questions = loadedQuestions;
          _secondsPerQuestion = perQSecs > 0 ? perQSecs : 30;
          _loading = false;
        });
        _startQuestionTimer();
      }
    } catch (_) {
      if (mounted) {
        final fallbackList = List<QuizQuestion>.from(_fallbackQuestions());

        _shuffledOptionsMap.clear();
        for (int i = 0; i < fallbackList.length; i++) {
          final q = fallbackList[i];
          final opts = <MapEntry<String, String>>[
            if (q.optionA.trim().isNotEmpty) MapEntry('A', q.optionA),
            if (q.optionB.trim().isNotEmpty) MapEntry('B', q.optionB),
            if (q.optionC.trim().isNotEmpty) MapEntry('C', q.optionC),
            if (q.optionD.trim().isNotEmpty) MapEntry('D', q.optionD),
          ];
          _shuffledOptionsMap[i] = opts;
        }

        setState(() {
          _questions = fallbackList;
          _secondsPerQuestion = widget.quiz.perQuestionTimerSeconds > 0
              ? widget.quiz.perQuestionTimerSeconds
              : 30;
          _loading = false;
        });
        _startQuestionTimer();
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
    _questionTimer?.cancel();
    setState(() => _isSubmitted = true);

    final Map<int, String?> answersMap = {};

    for (int i = 0; i < _questions.length; i++) {
      final q = _questions[i];
      final userAns = _selectedAnswers[i];
      answersMap[q.id] = userAns;
    }

    // Send submission to backend database so teacher panel receives it
    try {
      await ApiService().submitQuiz(
        quizId: _actualQuizId ?? widget.quiz.quizId,
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
        title: const Row(
          children: [
            Icon(
              Icons.check_circle_rounded,
              color: Colors.green,
              size: 28,
            ),
            SizedBox(width: 8),
            Text('Quiz Completed'),
          ],
        ),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quiz completed! You can check your marks in Grades section.',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, height: 1.4),
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
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('OK', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _handleExitAttempt() async {
    if (_isSubmitted) {
      Navigator.of(context).pop();
      return;
    }

    final shouldQuit = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.orange),
            SizedBox(width: 8),
            Text('Quit Quiz?'),
          ],
        ),
        content: const Text(
          'Quitting now will auto-submit your quiz with your current progress. Are you sure?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
            child: const Text('Submit & Exit'),
          ),
        ],
      ),
    );

    if (shouldQuit == true && mounted) {
      _submitQuiz();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final bool isLowTime = _questionRemainingSeconds <= 5;
    final bool isWarnTime = _questionRemainingSeconds <= 10;
    final Color timerColor = isLowTime
        ? Colors.red
        : isWarnTime
            ? Colors.orange
            : theme.colorScheme.primary;

    final currentShuffledOptions = _shuffledOptionsMap[_currentIndex] ?? [];
    final displayLabels = ['A', 'B', 'C', 'D'];

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        _handleExitAttempt();
      },
      child: SelectionContainer.disabled(
        child: Container(
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
                    // AI Proctoring Indicator Badge
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      margin: const EdgeInsets.only(right: 8),
                      decoration: BoxDecoration(
                        color: _proctoringWarningsCount == 0
                            ? Colors.green.shade50
                            : Colors.amber.shade50,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _proctoringWarningsCount == 0
                              ? Colors.green.shade400
                              : Colors.amber.shade600,
                          width: 1.5,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.shield_rounded,
                            size: 14,
                            color: _proctoringWarningsCount == 0
                                ? Colors.green.shade700
                                : Colors.amber.shade800,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            _proctoringWarningsCount == 0
                                ? 'AI Active'
                                : 'Strike $_proctoringWarningsCount/3',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: _proctoringWarningsCount == 0
                                  ? Colors.green.shade800
                                  : Colors.amber.shade900,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      margin: const EdgeInsets.only(right: 8),
                      decoration: BoxDecoration(
                        color: timerColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: timerColor.withOpacity(0.7),
                          width: 1.5,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.timer_outlined,
                            size: 16,
                            color: timerColor,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '$_questionRemainingSeconds s',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: timerColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: _handleExitAttempt,
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
                      // Question progress bar header
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
                              '$_secondsPerQuestion s/Question',
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

                      // Per-question timer progress bar
                      LinearProgressIndicator(
                        value: (_questionRemainingSeconds / _secondsPerQuestion).clamp(0.0, 1.0),
                        backgroundColor: theme.colorScheme.surfaceVariant,
                        valueColor: AlwaysStoppedAnimation<Color>(timerColor),
                        borderRadius: BorderRadius.circular(4),
                        minHeight: 6,
                      ),
                      const SizedBox(height: 20),

                      // Question text
                      Text(
                        _questions[_currentIndex].questionText,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Shuffled Options A, B, C, D
                      Expanded(
                        child: ListView.builder(
                          itemCount: currentShuffledOptions.length,
                          itemBuilder: (context, idx) {
                            final label = idx < displayLabels.length ? displayLabels[idx] : '${idx + 1}';
                            final optionEntry = currentShuffledOptions[idx];
                            return _buildOptionTile(
                              displayLabel: label,
                              originalKey: optionEntry.key,
                              text: optionEntry.value,
                            );
                          },
                        ),
                      ),

                      // Bottom Navigation Buttons
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          // Anti-Cheating indicator: Locked status for previous questions
                          Row(
                            children: [
                              Icon(Icons.lock_outline_rounded, size: 14, color: Colors.grey.shade500),
                              const SizedBox(width: 4),
                              Text(
                                'Previous Locked',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey.shade600,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),

                          if (_currentIndex < _questions.length - 1)
                            ElevatedButton.icon(
                              onPressed: _goToNextQuestion,
                              icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                              label: const Text('Next'),
                            )
                          else
                            ElevatedButton.icon(
                              onPressed: _submitQuiz,
                              icon: const Icon(Icons.check_circle_rounded, size: 16),
                              label: const Text('Submit Quiz'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.green,
                                foregroundColor: Colors.white,
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    ),
  );
  }

  Widget _buildOptionTile({
    required String displayLabel,
    required String originalKey,
    required String text,
  }) {
    final theme = Theme.of(context);
    final isSelected = _selectedAnswers[_currentIndex] == originalKey;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => setState(() => _selectedAnswers[_currentIndex] = originalKey),
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
                    displayLabel,
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
