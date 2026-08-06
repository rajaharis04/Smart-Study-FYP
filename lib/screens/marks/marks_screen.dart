// ╔══════════════════════════════════════════════════════════════════╗
// ║             MARKS SCREEN — Dedicated Student Gradebook           ║
// ║   Displays student scores, percentages & overall academic report ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';

class MarksScreen extends ConsumerStatefulWidget {
  const MarksScreen({super.key});

  @override
  ConsumerState<MarksScreen> createState() => _MarksScreenState();
}

class _MarksScreenState extends ConsumerState<MarksScreen> with SingleTickerProviderStateMixin {
  bool _isLoading = true;
  Map<String, dynamic> _marksData = {
    'overall_percentage': 0.0,
    'total_quizzes_attempted': 0,
    'total_assignments_submitted': 0,
    'quizzes': [],
    'assignments': [],
  };

  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _fetchMarks();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchMarks() async {
    setState(() => _isLoading = true);
    try {
      final data = await ApiService().getStudentMarks();
      if (mounted) {
        setState(() {
          _marksData = data;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    final overallPct = (_marksData['overall_percentage'] as num?)?.toDouble() ?? 0.0;
    final quizzes = (_marksData['quizzes'] as List?) ?? [];
    final assignments = (_marksData['assignments'] as List?) ?? [];

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        appBar: AppBar(
          title: Text(
            isUrdu ? 'نمبرز اور نتائج' : 'Marks & Results',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: _fetchMarks,
              tooltip: isUrdu ? 'ریفریش کریں' : 'Refresh',
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _fetchMarks,
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    // Overall Grade Summary Card
                    Container(
                      width: double.infinity,
                      margin: const EdgeInsets.all(16),
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            theme.colorScheme.primary,
                            theme.colorScheme.tertiary,
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: theme.colorScheme.primary.withValues(alpha: 0.3),
                            blurRadius: 12,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                isUrdu ? 'مجموعی کارکردگی' : 'Overall Academic Performance',
                                style: const TextStyle(
                                  color: Colors.white70,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: Colors.white24,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  '${overallPct.toStringAsFixed(1)}%',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              _buildSummaryStat(
                                isUrdu ? 'کوئزز' : 'Quizzes',
                                '${_marksData['total_quizzes_attempted']}',
                              ),
                              _buildSummaryStat(
                                isUrdu ? 'اسائنمنٹس' : 'Assignments',
                                '${_marksData['total_assignments_submitted']}',
                              ),
                              _buildSummaryStat(
                                isUrdu ? 'مجموعی' : 'Overall Grade',
                                overallPct >= 80
                                    ? 'A'
                                    : overallPct >= 70
                                        ? 'B'
                                        : overallPct >= 60
                                            ? 'C'
                                            : 'D',
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // Tab Navigation Bar
                    TabBar(
                      controller: _tabController,
                      labelColor: theme.colorScheme.primary,
                      unselectedLabelColor: theme.colorScheme.onSurfaceVariant,
                      indicatorColor: theme.colorScheme.primary,
                      tabs: [
                        Tab(
                          text: isUrdu
                              ? 'کوئزز (${quizzes.length})'
                              : 'Quizzes (${quizzes.length})',
                        ),
                        Tab(
                          text: isUrdu
                              ? 'اسائنمنٹس (${assignments.length})'
                              : 'Assignments (${assignments.length})',
                        ),
                      ],
                    ),

                    Expanded(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          // Tab 1: Quiz Marks
                          _buildQuizMarksList(theme, quizzes, isUrdu),
                          // Tab 2: Assignment Marks
                          _buildAssignmentMarksList(theme, assignments, isUrdu),
                        ],
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }

  Widget _buildSummaryStat(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 11,
          ),
        ),
      ],
    );
  }

  Widget _buildQuizMarksList(ThemeData theme, List quizzes, bool isUrdu) {
    if (quizzes.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.quiz_outlined, size: 48, color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4)),
            const SizedBox(height: 12),
            Text(
              isUrdu ? 'کوئی کوئز کا رزلٹ نہیں ہے' : 'No quiz attempts recorded yet',
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: quizzes.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final q = quizzes[index] as Map<String, dynamic>;
        final score = q['score'] ?? 0;
        final total = q['total_marks'] ?? 0;
        final pct = (q['percentage'] as num?)?.toDouble() ?? 0.0;

        return Card(
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: pct >= 50
                        ? Colors.green.withValues(alpha: 0.1)
                        : Colors.red.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    pct >= 50 ? Icons.emoji_events_rounded : Icons.info_outline_rounded,
                    color: pct >= 50 ? Colors.green : Colors.red,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        q['title'] ?? 'Quiz',
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        q['course_name'] ?? 'Course',
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '$score / $total',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                        color: pct >= 50 ? Colors.green : Colors.red,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: pct >= 50
                            ? Colors.green.withValues(alpha: 0.15)
                            : Colors.red.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${pct.toStringAsFixed(0)}%',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: pct >= 50 ? Colors.green : Colors.red,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildAssignmentMarksList(ThemeData theme, List assignments, bool isUrdu) {
    if (assignments.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.assignment_outlined, size: 48, color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4)),
            const SizedBox(height: 12),
            Text(
              isUrdu ? 'کوئی اسائنمنٹ کا رزلٹ نہیں ہے' : 'No assignment submissions recorded yet',
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: assignments.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final a = assignments[index] as Map<String, dynamic>;
        final score = a['score'] ?? 0;
        final total = a['total_marks'] ?? 100;
        final status = a['status'] ?? 'Submitted';

        return Card(
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: status == 'Graded'
                        ? Colors.blue.withValues(alpha: 0.1)
                        : Colors.orange.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    status == 'Graded' ? Icons.verified_rounded : Icons.pending_actions_rounded,
                    color: status == 'Graded' ? Colors.blue : Colors.orange,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        a['title'] ?? 'Assignment',
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        a['course_name'] ?? 'Course',
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '$score / $total',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: status == 'Graded'
                            ? Colors.green.withValues(alpha: 0.15)
                            : Colors.orange.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: status == 'Graded' ? Colors.green : Colors.orange,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
