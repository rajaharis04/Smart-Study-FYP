// ╔══════════════════════════════════════════════════════════════════╗
// ║              PROFILE SCREEN — Detailed Sub-Tabs                 ║
// ║  Student profile summary, progress tracker, question bank,        ║
// ║  and local app configurations (settings).                        ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../core/widgets/skeleton_shimmer.dart';
import '../../core/widgets/error_retry_widget.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';
import '../../providers/progress_provider.dart';
import '../../providers/question_bank_provider.dart';
import '../../providers/settings_provider.dart';

// Auto-disposing future provider for student profile details
final studentProfileProvider = FutureProvider.autoDispose<Student>((ref) async {
  return ApiService().getStudentProfile();
});

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);

    Future.microtask(() {
      _loadData();
    });
  }

  void _loadData() {
    ref.invalidate(studentProfileProvider);
    ref.read(progressProvider.notifier).getProgress();
    ref.read(questionBankProvider.notifier).getQuestionBank();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(studentProfileProvider);
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: NestedScrollView(
        headerSliverBuilder: (context, innerBoxIsScrolled) {
          return [
            SliverAppBar(
              expandedHeight: 220.0,
              floating: false,
              pinned: true,
              backgroundColor: theme.colorScheme.primary,
              elevation: 0,
              flexibleSpace: FlexibleSpaceBar(
                background: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        theme.colorScheme.primary,
                        const Color(0xFF1D9E75),
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                  child: profileAsync.when(
                    data: (student) => _buildProfileHeader(theme, student),
                    loading: () => _buildHeaderSkeleton(theme),
                    error: (err, _) => _buildHeaderError(theme, err.toString()),
                  ),
                ),
              ),
            ),
            SliverPersistentHeader(
              pinned: true,
              delegate: _SliverAppBarDelegate(
                TabBar(
                  controller: _tabController,
                  labelColor: theme.colorScheme.primary,
                  unselectedLabelColor: theme.colorScheme.onSurfaceVariant,
                  indicatorColor: theme.colorScheme.primary,
                  indicatorWeight: 3,
                  labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                  unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                  tabs: [
                    Tab(text: ref.watch(settingsProvider).translate('my_progress'), icon: const Icon(Icons.analytics_rounded, size: 20)),
                    Tab(text: ref.watch(settingsProvider).translate('question_bank'), icon: const Icon(Icons.bookmark_rounded, size: 20)),
                    Tab(text: ref.watch(settingsProvider).translate('settings'), icon: const Icon(Icons.settings_rounded, size: 20)),
                  ],
                ),
                theme.colorScheme.surface,
              ),
            ),
          ];
        },
        body: TabBarView(
          controller: _tabController,
          children: [
            _buildProgressTab(theme),
            _buildQuestionBankTab(theme),
            _buildSettingsTab(theme, profileAsync),
          ],
        ),
      ),
    );
  }

  // ── PROFILE HEADER WIDGETS ─────────────────────────────────────────

  Widget _buildProfileHeader(ThemeData theme, Student student) {
    final name = student.fullName;
    final initials = name
        .split(' ')
        .take(2)
        .map((w) => w.isNotEmpty ? w[0].toUpperCase() : '')
        .join();

    return Padding(
      padding: const EdgeInsets.only(top: 40.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Avatar
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withOpacity(0.2),
              border: Border.all(color: Colors.white.withOpacity(0.4), width: 3),
            ),
            child: Center(
              child: Text(
                initials,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            student.email,
            style: TextStyle(
              color: Colors.white.withOpacity(0.8),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderSkeleton(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: const [
          SkeletonShimmer(width: 80, height: 80, borderRadius: 40),
          SizedBox(height: 12),
          SkeletonShimmer(width: 140, height: 18),
          SizedBox(height: 6),
          SkeletonShimmer(width: 180, height: 12),
        ],
      ),
    );
  }

  Widget _buildHeaderError(ThemeData theme, String err) {
    return Center(
      child: Text(
        'Header failed: $err',
        style: const TextStyle(color: Colors.white70, fontSize: 12),
      ),
    );
  }

  // ── SUB-TAB 1: MY PROGRESS ─────────────────────────────────────────

  Widget _buildProgressTab(ThemeData theme) {
    final state = ref.watch(progressProvider);

    if (state.isLoading) {
      return _buildProgressSkeleton();
    }

    if (state.error != null) {
      return ErrorRetryWidget(
        errorMessage: state.error!,
        onRetry: () => ref.read(progressProvider.notifier).getProgress(),
      );
    }

    final data = state.progressData;
    if (data == null || data.courseProgress.isEmpty) {
      return _buildEmptyState(
        theme,
        icon: Icons.bar_chart_rounded,
        title: 'No progress recorded',
        subtitle: 'Watch lectures and complete quizzes to track learning trends.',
      );
    }

    // Calculate total topics, average mastery, and strong/weak counts
    int totalTopics = 0;
    double totalMasterySum = 0.0;
    int strongTopics = 0;
    int weakTopics = 0;

    for (var course in data.courseProgress) {
      for (var topic in course.topics) {
        totalTopics++;
        totalMasterySum += topic.mastery;
        if (topic.mastery >= 75.0) {
          strongTopics++;
        } else if (topic.mastery < 60.0) {
          weakTopics++;
        }
      }
    }

    final averageMastery = totalTopics > 0 ? totalMasterySum / totalTopics : 0.0;

    return ListView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.all(20),
      children: [
        // Quiz Performance Analytics Doughnut/Radial Card
        Container(
          margin: const EdgeInsets.only(bottom: 20),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.02),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
            border: Border.all(color: theme.colorScheme.outline.withOpacity(0.08)),
          ),
          child: Row(
            children: [
              // Radial Doughnut Chart
              SizedBox(
                width: 100,
                height: 100,
                child: CustomPaint(
                  painter: _RadialQuizAnalyticsPainter(
                    percentage: averageMastery,
                    primaryColor: theme.colorScheme.primary,
                    remainingColor: theme.colorScheme.error.withOpacity(0.2),
                  ),
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '${averageMastery.toInt()}%',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                        const Text(
                          'Mastery',
                          style: TextStyle(fontSize: 9, color: Colors.grey, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 24),

              // Legend details
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Quiz Performance',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                    const SizedBox(height: 10),
                    _buildAnalyticsLegendRow(
                      theme,
                      'Strong Topics',
                      '$strongTopics',
                      const Color(0xFF00BFA5),
                    ),
                    const SizedBox(height: 6),
                    _buildAnalyticsLegendRow(
                      theme,
                      'Weak Topics',
                      '$weakTopics',
                      const Color(0xFFFF6B6B),
                    ),
                    const SizedBox(height: 6),
                    _buildAnalyticsLegendRow(
                      theme,
                      'Total Checked',
                      '$totalTopics',
                      theme.colorScheme.primary,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // Smart Learning Insights Panel
        _buildInsightsPanel(
          theme,
          data.insights,
          ref.watch(settingsProvider).language == 'Urdu',
        ),

        // Topic Mastery Progress Bars
        ...data.courseProgress.map((course) {
          return Card(
            margin: const EdgeInsets.only(bottom: 20),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            elevation: 0,
            color: theme.colorScheme.surface,
            borderOnForeground: false,
            child: ExpansionTile(
              initiallyExpanded: true,
              shape: const Border(), // remove separator borders
              title: Text(
                '${course.courseName} (${course.courseCode})',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
              ),
              childrenPadding: const EdgeInsets.all(16),
              children: course.topics.isEmpty
                  ? [const Text('No topics currently listed.', style: TextStyle(color: Colors.grey, fontSize: 12))]
                  : course.topics.map((topic) {
                      // HSL/tailored colors based on mastery level
                      Color barColor;
                      if (topic.mastery >= 75) {
                        barColor = const Color(0xFF00BFA5); // Strong Green
                      } else if (topic.mastery >= 60) {
                        barColor = const Color(0xFF6C63FF); // Working Purple
                      } else if (topic.mastery >= 50) {
                        barColor = const Color(0xFFFFB74D); // Weak Yellow
                      } else {
                        barColor = const Color(0xFFFF6B6B); // Very Weak Red
                      }

                      return Padding(
                        padding: const EdgeInsets.only(bottom: 20.0),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surface,
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.015),
                                blurRadius: 10,
                                offset: const Offset(0, 4),
                              ),
                            ],
                            border: Border.all(color: theme.colorScheme.outline.withOpacity(0.05)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      topic.title,
                                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  Text(
                                    '${topic.mastery.toInt()}%  ${topic.statusSymbol} ${topic.statusLabel}',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w700,
                                      fontSize: 12,
                                      color: barColor,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: LinearProgressIndicator(
                                  value: topic.mastery / 100,
                                  minHeight: 6,
                                  backgroundColor: barColor.withOpacity(0.1),
                                  valueColor: AlwaysStoppedAnimation<Color>(barColor),
                                ),
                              ),
                              const SizedBox(height: 12),
                              // Micro-statistics row for learning model metrics
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  _MicroMetricItem(
                                    icon: Icons.psychology_rounded,
                                    label: ref.watch(settingsProvider).language == 'Urdu' ? 'اعتماد' : 'Confidence',
                                    value: '${topic.confidence.toInt()}%',
                                    color: theme.colorScheme.primary,
                                  ),
                                  _MicroMetricItem(
                                    icon: Icons.bolt_rounded,
                                    label: ref.watch(settingsProvider).language == 'Urdu' ? 'سرگرمی' : 'Engagement',
                                    value: '${topic.engagement.toInt()}%',
                                    color: const Color(0xFFFFB74D),
                                  ),
                                  _MicroMetricItem(
                                    icon: Icons.timer_outlined,
                                    label: ref.watch(settingsProvider).language == 'Urdu' ? 'رفتار' : 'Pace',
                                    value: '${topic.learningPace.toInt()}s',
                                    color: const Color(0xFF6C63FF),
                                  ),
                                  _MicroMetricItem(
                                    icon: Icons.lightbulb_outline_rounded,
                                    label: ref.watch(settingsProvider).language == 'Urdu' ? 'اشارہ' : 'Hints',
                                    value: '${(topic.hintDependency * 100).toInt()}%',
                                    color: const Color(0xFFFF6B6B),
                                  ),
                                  _MicroMetricItem(
                                    icon: Icons.auto_awesome_rounded,
                                    label: ref.watch(settingsProvider).language == 'Urdu' ? 'لرننگ سکور' : 'Learning Score',
                                    value: '${topic.learningScore.toInt()}%',
                                    color: const Color(0xFF00BFA5),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                );
              }).toList(),

        // Weak Topics Recommendations section
        if (data.recommendations.isNotEmpty) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  const Color(0xFFFF6B6B).withOpacity(0.08),
                  const Color(0xFFFFB74D).withOpacity(0.08),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFFFF6B6B).withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.lightbulb_outline_rounded, color: Color(0xFFFF6B6B)),
                    SizedBox(width: 10),
                    Text(
                      'Focus Areas & Recommendations',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFFFF6B6B),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                ...data.recommendations.map((rec) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '• ${rec['topic_title']} (${rec['course_code']}) — Mastery: ${rec['mastery']}%',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Colors.black87),
                        ),
                        const SizedBox(height: 3),
                        Padding(
                          padding: const EdgeInsets.only(left: 10.0),
                          child: Text(
                            rec['recommendation']?.toString() ?? '',
                            style: const TextStyle(fontSize: 11.5, color: Colors.grey, height: 1.4),
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildProgressSkeleton() {
    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: 3,
      itemBuilder: (context, index) {
        return Container(
          margin: const EdgeInsets.only(bottom: 16),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              SkeletonShimmer(width: 140, height: 16),
              SizedBox(height: 20),
              SkeletonShimmer(width: double.infinity, height: 40),
              SizedBox(height: 16),
              SkeletonShimmer(width: double.infinity, height: 40),
            ],
          ),
        );
      },
    );
  }

  // ── SUB-TAB 2: QUESTION BANK ───────────────────────────────────────

  Widget _buildQuestionBankTab(ThemeData theme) {
    final state = ref.watch(questionBankProvider);

    if (state.isLoading) {
      return _buildQuestionBankSkeleton();
    }

    if (state.error != null) {
      return ErrorRetryWidget(
        errorMessage: state.error!,
        onRetry: () => ref.read(questionBankProvider.notifier).getQuestionBank(),
      );
    }

    final questions = state.wrongQuestions;

    if (questions.isEmpty) {
      return _buildEmptyState(
        theme,
        icon: Icons.check_circle_outline_rounded,
        title: 'Perfect Record!',
        subtitle: 'No weak quiz responses inside your practice queue.',
      );
    }

    return ListView.builder(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.all(20),
      itemCount: questions.length,
      itemBuilder: (context, index) {
        final q = questions[index];

        return Container(
          margin: const EdgeInsets.only(bottom: 16),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.03),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Badge topic / course
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '${q.courseCode}  •  ${q.topicTitle}',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ),
                  const Icon(Icons.bookmark_added_rounded, color: Colors.grey, size: 16),
                ],
              ),
              const SizedBox(height: 14),

              // Question body
              Text(
                q.questionText,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, height: 1.4),
              ),
              const SizedBox(height: 14),

              // Answers comparison
              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFF6B6B).withOpacity(0.08),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Your Answer', style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.w600)),
                          const SizedBox(height: 2),
                          Text('Option ${q.yourAnswer}', style: const TextStyle(color: Color(0xFFFF6B6B), fontWeight: FontWeight.w700, fontSize: 12)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00BFA5).withOpacity(0.08),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Correct Answer', style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.w600)),
                          const SizedBox(height: 2),
                          Text('Option ${q.correctAnswer}', style: const TextStyle(color: Color(0xFF00BFA5), fontWeight: FontWeight.w700, fontSize: 12)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Action button "Attempt Again"
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => _openReattemptModal(q),
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  label: const Text('Attempt Again'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: theme.colorScheme.primary,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildQuestionBankSkeleton() {
    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: 3,
      itemBuilder: (context, index) {
        return Container(
          margin: const EdgeInsets.only(bottom: 16),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              SkeletonShimmer(width: 100, height: 16),
              SizedBox(height: 14),
              SkeletonShimmer(width: double.infinity, height: 40),
              SizedBox(height: 14),
              SkeletonShimmer(width: double.infinity, height: 35),
              SizedBox(height: 16),
              SkeletonShimmer(width: double.infinity, height: 40),
            ],
          ),
        );
      },
    );
  }

  // Question Bank re-attempt modal implementation
  void _openReattemptModal(QuestionBankItem question) {
    String? chosenOption;
    bool isSubmitted = false;
    bool isCorrect = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 30),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Practice Attempt',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ),
                      IconButton(
                        onPressed: () => Navigator.pop(context),
                        icon: const Icon(Icons.close_rounded),
                      ),
                    ],
                  ),
                  const Divider(height: 20),
                  
                  // Question text
                  Text(
                    question.questionText,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, height: 1.4),
                  ),
                  const SizedBox(height: 20),

                  if (!isSubmitted) ...[
                    // Option cards
                    _buildOptionCard(context, 'A', question.optionA, chosenOption == 'A', (val) {
                      setModalState(() => chosenOption = val);
                    }),
                    const SizedBox(height: 10),
                    _buildOptionCard(context, 'B', question.optionB, chosenOption == 'B', (val) {
                      setModalState(() => chosenOption = val);
                    }),
                    const SizedBox(height: 10),
                    _buildOptionCard(context, 'C', question.optionC, chosenOption == 'C', (val) {
                      setModalState(() => chosenOption = val);
                    }),
                    const SizedBox(height: 10),
                    _buildOptionCard(context, 'D', question.optionD, chosenOption == 'D', (val) {
                      setModalState(() => chosenOption = val);
                    }),
                    const SizedBox(height: 24),
                    
                    // Submit button
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: chosenOption == null
                            ? null
                            : () async {
                                final notifier = ref.read(questionBankProvider.notifier);
                                try {
                                  final correct = await notifier.attemptQuestionAgain(question.id, chosenOption!);
                                  setModalState(() {
                                    isCorrect = correct;
                                    isSubmitted = true;
                                  });
                                } catch (e) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Error: ${e.toString()}')),
                                  );
                                }
                              },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Theme.of(context).colorScheme.primary,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                        child: const Text('Submit Attempt', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ),
                  ] else ...[
                    // Result feedback screen inside modal
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.all(20.0),
                        child: Column(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: isCorrect
                                    ? const Color(0xFF00BFA5).withOpacity(0.12)
                                    : const Color(0xFFFF6B6B).withOpacity(0.12),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                isCorrect ? Icons.check_circle_rounded : Icons.cancel_rounded,
                                color: isCorrect ? const Color(0xFF00BFA5) : const Color(0xFFFF6B6B),
                                size: 48,
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              isCorrect ? 'Correct Answer! 🎉' : 'Incorrect Answer',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: isCorrect ? const Color(0xFF00BFA5) : const Color(0xFFFF6B6B),
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              isCorrect
                                  ? 'This question has been successfully cleared from your practice bank!'
                                  : 'The correct option was ${question.correctAnswer}. Keep studying and try again.',
                              textAlign: TextAlign.center,
                              style: const TextStyle(fontSize: 13, color: Colors.grey),
                            ),
                            const SizedBox(height: 24),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton(
                                onPressed: () {
                                  Navigator.pop(context);
                                  // Refresh question bank log
                                  ref.read(questionBankProvider.notifier).getQuestionBank();
                                },
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Theme.of(context).colorScheme.primary,
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  padding: const EdgeInsets.symmetric(vertical: 12),
                                ),
                                child: const Text('Close'),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildOptionCard(
    BuildContext context,
    String key,
    String text,
    bool isSelected,
    Function(String) onSelect,
  ) {
    final theme = Theme.of(context);
    final highlightColor = theme.colorScheme.primary;

    return InkWell(
      onTap: () => onSelect(key),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isSelected ? highlightColor.withOpacity(0.08) : theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? highlightColor : theme.colorScheme.outline.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 26,
              height: 26,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isSelected ? highlightColor : Colors.grey[200],
              ),
              child: Center(
                child: Text(
                  key,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: isSelected ? Colors.white : Colors.black87,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                text,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  color: isSelected ? highlightColor : theme.colorScheme.onSurface,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── SUB-TAB 3: SETTINGS ────────────────────────────────────────────

  Widget _buildSettingsTab(ThemeData theme, AsyncValue<Student> profileAsync) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    return ListView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.all(20),
      children: [
        // A. Profile Section
        profileAsync.when(
          data: (student) => _buildSettingsSection(theme, isUrdu ? 'پروفائل کی تفصیلات' : 'Profile Details', [
            _buildSettingsInfoRow(isUrdu ? 'پورا نام' : 'Full Name', student.fullName),
            _buildSettingsInfoRow(isUrdu ? 'ای میل ایڈریس' : 'Email Address', student.email),
            _buildSettingsInfoRow(isUrdu ? 'رجسٹریشن نمبر' : 'Registration No.', student.regNumber ?? 'SP23-BCS-011'),
            _buildSettingsInfoRow(isUrdu ? 'شعبہ' : 'Department', student.department ?? 'Computer Science'),
            _buildSettingsInfoRow(isUrdu ? 'سیشن / بیچ' : 'Batch / Session', student.batch ?? 'Spring 2023'),
          ]),
          loading: () => const SkeletonShimmer(width: double.infinity, height: 180),
          error: (err, _) => Text('Error loading profile: $err', style: const TextStyle(color: Colors.red)),
        ),
        const SizedBox(height: 20),

        // B. Security Section
        _buildSettingsSection(theme, isUrdu ? 'سیکیورٹی' : 'Security', [
          ListTile(
            leading: Icon(Icons.lock_rounded, color: theme.colorScheme.primary),
            title: Text(settings.translate('change_password'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text(isUrdu ? 'آخری بار 3 ماہ پہلے تبدیل کیا گیا' : 'Last changed 3 months ago', style: const TextStyle(fontSize: 11, color: Colors.grey)),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () => _openChangePasswordDialog(context),
          ),
        ]),
        const SizedBox(height: 20),

        // C. Preferences Section
        _buildSettingsSection(theme, isUrdu ? 'ترجیحات اور رازداری' : 'Preferences & Privacy', [
          SwitchListTile(
            activeColor: theme.colorScheme.primary,
            secondary: Icon(Icons.notifications_rounded, color: theme.colorScheme.primary),
            title: Text(settings.translate('notifications'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text(isUrdu ? 'سسٹم کے نشریاتی نوٹیفکیشنز' : 'System broadcast notifications', style: const TextStyle(fontSize: 11)),
            value: settings.isNotificationsEnabled,
            onChanged: (val) => ref.read(settingsProvider.notifier).toggleNotifications(),
          ),
          const Divider(height: 1),
          ListTile(
            leading: Icon(Icons.notifications_active_rounded, color: theme.colorScheme.primary),
            title: Text(isUrdu ? 'نوٹیفکیشن ہسٹری' : 'Notification History', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text(isUrdu ? 'تمام نشریاتی الرٹس کی ہسٹری دیکھیں' : 'View history of all broadcast alerts', style: const TextStyle(fontSize: 11, color: Colors.grey)),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () {
              context.push('/dashboard/profile/notifications');
            },
          ),
          const Divider(height: 1),
          SwitchListTile(
            activeColor: theme.colorScheme.primary,
            secondary: Icon(Icons.dark_mode_rounded, color: theme.colorScheme.primary),
            title: Text(settings.translate('theme_dark'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text(isUrdu ? 'ڈارک تھیم والی بصری UI کو فعال کریں' : 'Toggle dark themed visual UI', style: const TextStyle(fontSize: 11)),
            value: settings.isDarkMode,
            onChanged: (val) => ref.read(settingsProvider.notifier).toggleDarkMode(),
          ),
          const Divider(height: 1),
          SwitchListTile(
            activeColor: theme.colorScheme.primary,
            secondary: Icon(Icons.camera_front_rounded, color: theme.colorScheme.primary),
            title: Text(settings.translate('attention_mode'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            subtitle: Text(isUrdu ? 'شراکت کی نگرانی کے لئے کیمرے تک رسائی' : 'Camera access for engagement monitoring', style: const TextStyle(fontSize: 11)),
            value: settings.isAttentionModeEnabled,
            onChanged: (val) => ref.read(settingsProvider.notifier).toggleAttentionMode(),
          ),
          const Divider(height: 1),
          ListTile(
            leading: Icon(Icons.language_rounded, color: theme.colorScheme.primary),
            title: Text(settings.translate('language'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            trailing: DropdownButton<String>(
              value: settings.language,
              underline: const SizedBox(),
              onChanged: (String? val) {
                if (val != null) {
                  ref.read(settingsProvider.notifier).setLanguage(val);
                }
              },
              items: const [
                DropdownMenuItem(value: 'English', child: Text('English', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold))),
                DropdownMenuItem(value: 'Urdu', child: Text('Urdu', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold))),
              ],
            ),
          ),
        ]),
        const SizedBox(height: 20),

        // D. App Settings Section
        _buildSettingsSection(theme, isUrdu ? 'ایپلی کیشن کی معلومات' : 'Application Info', [
          _buildSettingsInfoRow(isUrdu ? 'ایپ کا ورژن' : 'App Version', '1.0.0'),
          _buildSettingsInfoRow(isUrdu ? 'بلڈ نمبر' : 'Build Number', '42'),
          _buildSettingsInfoRow(isUrdu ? 'استعمال شدہ اسٹوریج' : 'Storage Used', '245 MB'),
          ListTile(
            leading: const Icon(Icons.cleaning_services_rounded, color: Colors.blue),
            title: Text(settings.translate('clear_cache'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Colors.blue)),
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text(isUrdu ? 'ایپ کیشے کامیابی سے صاف ہو گیا' : 'App cache cleared successfully.')),
              );
            },
          ),
          const Divider(height: 1),
          ListTile(
            leading: const Icon(Icons.logout_rounded, color: Colors.red),
            title: Text(settings.translate('logout'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Colors.red)),
            onTap: () => _confirmLogout(context),
          ),
        ]),
        const SizedBox(height: 40),
      ],
    );
  }

  Widget _buildSettingsSection(ThemeData theme, String sectionTitle, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            sectionTitle,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: theme.colorScheme.onSurfaceVariant,
              letterSpacing: 0.5,
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.02),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
            border: Border.all(color: theme.colorScheme.outline.withOpacity(0.08)),
          ),
          child: Column(
            children: children,
          ),
        ),
      ],
    );
  }

  Widget _buildSettingsInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 14.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5, color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: Colors.black87)),
        ],
      ),
    );
  }

  void _openChangePasswordDialog(BuildContext context) {
    final curCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: const Text('Change Password', style: TextStyle(fontWeight: FontWeight.bold)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: curCtrl,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Current Password',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: newCtrl,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'New Password',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          if (curCtrl.text.isEmpty || newCtrl.text.isEmpty) {
                            return;
                          }
                          setDialogState(() => isSubmitting = true);
                          try {
                            await ref.read(settingsProvider.notifier).changePassword(
                                  curCtrl.text,
                                  newCtrl.text,
                                );
                            if (ctx.mounted) {
                              Navigator.pop(ctx);
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Password changed successfully!')),
                              );
                            }
                          } catch (e) {
                            setDialogState(() => isSubmitting = false);
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
                            );
                          }
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    foregroundColor: Colors.white,
                  ),
                  child: isSubmitting
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Change'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _confirmLogout(BuildContext context) {
    final settings = ref.read(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(settings.translate('logout')),
        content: Text(isUrdu ? 'کیا آپ واقعی لاگ آؤٹ کرنا چاہتے ہیں؟' : 'Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(isUrdu ? 'منسوخ کریں' : 'Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              await ref.read(settingsProvider.notifier).logout();
              if (context.mounted) {
                context.go(AppConstants.routeLogin);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: Text(settings.translate('logout')),
          ),
        ],
      ),
    );
  }

  // ── COMMON HELPER WIDGETS ──────────────────────────────────────────

  Widget _buildEmptyState(
    ThemeData theme, {
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 72, color: theme.colorScheme.primary.withOpacity(0.2)),
            const SizedBox(height: 16),
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalyticsLegendRow(
    ThemeData theme,
    String label,
    String value,
    Color color,
  ) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: theme.colorScheme.onSurface,
          ),
        ),
      ],
    );
  }

  Widget _buildInsightsPanel(ThemeData theme, List<Map<String, dynamic>> insights, bool isUrdu) {
    if (insights.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: theme.brightness == Brightness.dark
              ? [const Color(0xFF1E293B), const Color(0xFF0F172A)]
              : [const Color(0xFFF8FAFC), const Color(0xFFF1F5F9)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome_rounded, color: theme.colorScheme.primary, size: 18),
              const SizedBox(width: 8),
              Text(
                isUrdu ? 'سمارٹ لرننگ تجزیات' : 'Smart Learning Insights',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: theme.colorScheme.onSurface,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Vertical list of insight cards
          ...insights.map((insight) {
            final type = insight['type'] as String? ?? 'general';
            final title = isUrdu
                ? (insight['title_ur'] as String? ?? 'تجویز')
                : (insight['title_en'] as String? ?? 'Suggestion');
            final message = isUrdu
                ? (insight['message_ur'] as String? ?? '')
                : (insight['message_en'] as String? ?? '');
            final courseCode = insight['course_code'] as String? ?? '';

            Color iconColor;
            IconData iconData;
            Color bgColor;

            if (type == 'hint') {
              iconColor = const Color(0xFFFF6B6B);
              iconData = Icons.lightbulb_outline_rounded;
              bgColor = iconColor.withOpacity(0.08);
            } else if (type == 'pace') {
              iconColor = const Color(0xFF6C63FF);
              iconData = Icons.timer_outlined;
              bgColor = iconColor.withOpacity(0.08);
            } else if (type == 'engagement') {
              iconColor = const Color(0xFFFFB74D);
              iconData = Icons.bolt_rounded;
              bgColor = iconColor.withOpacity(0.08);
            } else if (type == 'consistency') {
              iconColor = const Color(0xFF00BFA5);
              iconData = Icons.psychology_rounded;
              bgColor = iconColor.withOpacity(0.08);
            } else {
              iconColor = theme.colorScheme.primary;
              iconData = Icons.emoji_events_rounded;
              bgColor = iconColor.withOpacity(0.08);
            }

            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: theme.colorScheme.outline.withOpacity(0.06)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.01),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: bgColor,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(iconData, color: iconColor, size: 16),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              title,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: theme.colorScheme.onSurface,
                              ),
                            ),
                            if (courseCode != 'ALL' && courseCode.isNotEmpty)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: theme.colorScheme.outline.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  courseCode,
                                  style: TextStyle(
                                    fontSize: 8.5,
                                    fontWeight: FontWeight.w700,
                                    color: theme.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          message,
                          style: TextStyle(
                            fontSize: 11,
                            color: theme.colorScheme.onSurfaceVariant,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ],
      ),
    );
  }
}

// ── CUSTOM SLIVER HEADER PERSISTENT DELEGATE ─────────────────────────

class _SliverAppBarDelegate extends SliverPersistentHeaderDelegate {
  final TabBar _tabBar;
  final Color _bgColor;

  _SliverAppBarDelegate(this._tabBar, this._bgColor);

  @override
  double get minExtent => _tabBar.preferredSize.height;
  @override
  double get maxExtent => _tabBar.preferredSize.height;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      color: _bgColor,
      child: _tabBar,
    );
  }

  @override
  bool shouldRebuild(_SliverAppBarDelegate oldDelegate) {
    return false;
  }
}

// ── RADIAL ANALYTICS CUSTOM PAINTER ──────────────────────────────────

class _RadialQuizAnalyticsPainter extends CustomPainter {
  final double percentage;
  final Color primaryColor;
  final Color remainingColor;

  _RadialQuizAnalyticsPainter({
    required this.percentage,
    required this.primaryColor,
    required this.remainingColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 8; // subtract half of stroke width for padding
    final strokeWidth = 8.0;

    // Background track
    final bgPaint = Paint()
      ..color = remainingColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;

    canvas.drawCircle(center, radius, bgPaint);

    // Foreground progress arc
    final progressPaint = Paint()
      ..color = primaryColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final sweepAngle = (percentage / 100) * 2 * 3.141592653589793;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -3.141592653589793 / 2, // Start at 12 o'clock
      sweepAngle,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RadialQuizAnalyticsPainter oldDelegate) {
    return oldDelegate.percentage != percentage ||
        oldDelegate.primaryColor != primaryColor ||
        oldDelegate.remainingColor != remainingColor;
  }
}


// ── MICRO METRIC ITEM WIDGET ──────────────────────────────────────────

class _MicroMetricItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _MicroMetricItem({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.w800,
            color: color,
          ),
        ),
        const SizedBox(height: 1),
        Text(
          label,
          style: const TextStyle(
            fontSize: 7.5,
            color: Colors.grey,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
