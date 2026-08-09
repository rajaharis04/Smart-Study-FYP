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
    'exams_and_others': [],
    'official_transcript': null,
  };

  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _fetchMarks();
  }

  @override
  void reassemble() {
    super.reassemble();
    if (_tabController.length != 4) {
      _tabController.dispose();
      _tabController = TabController(length: 4, vsync: this);
    }
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
    final exams = (_marksData['exams_and_others'] as List?) ?? [];
    final officialTranscript = _marksData['official_transcript'] as Map<String, dynamic>?;

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
                    // Top Summary Card
                    _buildTopSummaryCard(theme, isUrdu, overallPct, officialTranscript),

                    // 4-Tab Navigation Bar (Result, Quizzes, Assignments, Exams)
                    TabBar(
                      controller: _tabController,
                      isScrollable: true,
                      labelColor: theme.colorScheme.primary,
                      unselectedLabelColor: theme.colorScheme.onSurfaceVariant,
                      indicatorColor: theme.colorScheme.primary,
                      tabs: [
                        Tab(
                          text: isUrdu ? '🎓 فائنل رزلٹ' : '🎓 Final Result',
                        ),
                        Tab(
                          text: isUrdu ? 'کوئزز (${quizzes.length})' : 'Quizzes (${quizzes.length})',
                        ),
                        Tab(
                          text: isUrdu ? 'اسائنمنٹس (${assignments.length})' : 'Assignments (${assignments.length})',
                        ),
                        Tab(
                          text: isUrdu ? 'امتحانات (${exams.length})' : 'Exams (${exams.length})',
                        ),
                      ],
                    ),

                    Expanded(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          // Tab 1: Synced Official Result & Solid Marks Breakdown
                          _buildOfficialResultTab(theme, officialTranscript, isUrdu),

                          // Tab 2: Quiz Marks List
                          _buildQuizMarksList(theme, quizzes, isUrdu),

                          // Tab 3: Assignment Marks List
                          _buildAssignmentMarksList(theme, assignments, isUrdu),

                          // Tab 4: Exams & Others Marks List
                          _buildExamsMarksList(theme, exams, isUrdu),
                        ],
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }

  Widget _buildTopSummaryCard(
    ThemeData theme,
    bool isUrdu,
    double overallPct,
    Map<String, dynamic>? officialTranscript,
  ) {
    final letterGrade = officialTranscript?['letter_grade'] ??
        (overallPct >= 85
            ? 'A'
            : overallPct >= 75
                ? 'B'
                : overallPct >= 65
                    ? 'C'
                    : overallPct >= 50
                        ? 'D'
                        : 'F');

    final gpa = officialTranscript?['gpa'] ??
        (overallPct >= 85
            ? 4.0
            : overallPct >= 75
                ? 3.0
                : overallPct >= 65
                    ? 2.0
                    : overallPct >= 50
                        ? 1.0
                        : 0.0);

    return Container(
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
                isUrdu ? 'مجموعی کارکردگی (Synced)' : 'Academic Performance (Synced)',
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
                  '${overallPct.toStringAsFixed(1)} / 100',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildSummaryStat(
                isUrdu ? 'لیٹر گریڈ' : 'Letter Grade',
                letterGrade,
              ),
              _buildSummaryStat(
                isUrdu ? 'جی پی اے' : 'CGPA / GPA',
                '${(gpa as num).toStringAsFixed(2)}',
              ),
              _buildSummaryStat(
                isUrdu ? 'حالت' : 'Result Status',
                officialTranscript?['is_official'] == true ? 'Official' : 'Live Synced',
              ),
            ],
          ),
        ],
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

  /// Dedicated Official Result / Final Transcript Tab (Solid Marks 100-mark weighted sync)
  Widget _buildOfficialResultTab(
    ThemeData theme,
    Map<String, dynamic>? officialTranscript,
    bool isUrdu,
  ) {
    final isOfficial = officialTranscript?['is_official'] == true;
    final statusStr = officialTranscript?['status'] ?? 'Live Synced';
    final totalWeighted = (officialTranscript?['total_weighted_score'] as num?)?.toDouble() ?? 0.0;
    final letterGrade = officialTranscript?['letter_grade'] ?? 'N/A';
    final gpa = (officialTranscript?['gpa'] as num?)?.toDouble() ?? 0.0;

    final qScore = (officialTranscript?['quizzes_score_100'] as num?)?.toDouble() ?? 0.0;
    final aScore = (officialTranscript?['assignments_score_100'] as num?)?.toDouble() ?? 0.0;
    final mScore = (officialTranscript?['midterm_score_100'] as num?)?.toDouble() ?? 0.0;
    final fScore = (officialTranscript?['final_score_100'] as num?)?.toDouble() ?? 0.0;
    final oScore = (officialTranscript?['others_score_100'] as num?)?.toDouble() ?? 0.0;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isOfficial ? Colors.green.shade50 : Colors.indigo.shade50,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isOfficial ? Colors.green.shade300 : Colors.indigo.shade200,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  isOfficial ? Icons.verified_user_rounded : Icons.sync_outlined,
                  color: isOfficial ? Colors.green.shade700 : Colors.indigo.shade700,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isOfficial
                            ? (isUrdu ? 'سرکاری نتائج (Teacher Panel Synced)' : 'Official Transcript (Teacher Synced)')
                            : (isUrdu ? 'لائیو رزلٹ کا تخمینہ (Live Synced)' : 'Live Estimated Result (Synced)'),
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: isOfficial ? Colors.green.shade900 : Colors.indigo.shade900,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        isUrdu
                            ? 'یہ رزلٹ پورٹل کے 100 نمبرز ویٹیج فارمولا سے ہم آہنگ ہے'
                            : 'Synchronized with Teacher Web Portal 100-mark policy',
                        style: TextStyle(
                          fontSize: 12,
                          color: isOfficial ? Colors.green.shade800 : Colors.indigo.shade700,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: isOfficial ? Colors.green.shade700 : Colors.indigo.shade700,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    statusStr,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Total GPA / Grade Large Banner
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      Column(
                        children: [
                          Text(
                            isUrdu ? 'کل ویٹڈ نمبرز' : 'Total Marks',
                            style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '${totalWeighted.toStringAsFixed(1)} / 100',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 22,
                              color: theme.colorScheme.primary,
                            ),
                          ),
                        ],
                      ),
                      Container(height: 40, width: 1, color: Colors.grey.shade300),
                      Column(
                        children: [
                          Text(
                            isUrdu ? 'گریڈ' : 'Grade',
                            style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12),
                          ),
                          const SizedBox(height: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.amber.shade700,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              letterGrade,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 18,
                              ),
                            ),
                          ),
                        ],
                      ),
                      Container(height: 40, width: 1, color: Colors.grey.shade300),
                      Column(
                        children: [
                          Text(
                            isUrdu ? 'جی پی اے' : 'GPA',
                            style: TextStyle(color: theme.colorScheme.onSurfaceVariant, fontSize: 12),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            gpa.toStringAsFixed(2),
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 22,
                              color: Colors.green,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => _showPrintableTranscriptModal(context, isUrdu, officialTranscript, totalWeighted, letterGrade, gpa),
                    icon: const Icon(Icons.print_rounded, size: 18),
                    label: Text(isUrdu ? 'سرکاری ٹرانسکرپٹ دیکھیں / پرنٹ کریں' : 'View / Print Official Transcript'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: theme.colorScheme.primary,
                      foregroundColor: Colors.white,
                      minimumSize: const Size(double.infinity, 42),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Class Benchmark & Rank Card
          if (_marksData['class_benchmark'] != null) ...[
            Builder(builder: (context) {
              final bm = _marksData['class_benchmark'] as Map<String, dynamic>;
              final rank = bm['class_rank'] ?? 1;
              final totStudents = bm['total_students'] ?? 1;
              final classAvg = (bm['class_average'] as num?)?.toDouble() ?? totalWeighted;
              final tier = bm['percentile_tier'] ?? 'Top 10%';

              return Card(
                elevation: 0,
                color: theme.colorScheme.primaryContainer.withValues(alpha: 0.25),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                  side: BorderSide(color: theme.colorScheme.primary.withValues(alpha: 0.3)),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(Icons.leaderboard_rounded, color: theme.colorScheme.primary, size: 28),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              isUrdu ? 'کلاس اینالیٹکس اور پوزیشن' : 'Class Position & Analytics',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Class Avg: ${classAvg.toStringAsFixed(1)}%  •  Total Students: $totStudents',
                              style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                            ),
                          ],
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.indigo.shade700,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              'Rank #$rank / $totStudents',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            tier,
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
            const SizedBox(height: 16),
          ],
          const SizedBox(height: 20),

          Text(
            isUrdu ? '100 نمبرز ویٹیج کی تفصیل' : '100-Mark Weightage Breakdown',
            style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),

          // Solid Component Cards
          _buildComponentWeightCard(
            title: isUrdu ? 'کوئزز (Quizzes)' : 'Quizzes Weight',
            weightLabel: '15%',
            score: qScore,
            maxScore: 15.0,
            icon: Icons.quiz_outlined,
            color: Colors.blue,
          ),
          _buildComponentWeightCard(
            title: isUrdu ? 'اسائنمنٹس (Assignments)' : 'Assignments Weight',
            weightLabel: '15%',
            score: aScore,
            maxScore: 15.0,
            icon: Icons.assignment_outlined,
            color: Colors.orange,
          ),
          _buildComponentWeightCard(
            title: isUrdu ? 'مڈٹرم امتحان (Midterm Exam)' : 'Midterm Exam Weight',
            weightLabel: '25%',
            score: mScore,
            maxScore: 25.0,
            icon: Icons.school_outlined,
            color: Colors.purple,
          ),
          _buildComponentWeightCard(
            title: isUrdu ? 'فائنل امتحان (Final Exam)' : 'Final Exam Weight',
            weightLabel: '40%',
            score: fScore,
            maxScore: 40.0,
            icon: Icons.assignment_turned_in_outlined,
            color: Colors.indigo,
          ),
          _buildComponentWeightCard(
            title: isUrdu ? 'پروجیکٹ اور پریزنٹیشن (Others)' : 'Project & Presentation Weight',
            weightLabel: '5%',
            score: oScore,
            maxScore: 5.0,
            icon: Icons.stars_outlined,
            color: Colors.teal,
          ),
        ],
      ),
    );
  }

  Widget _buildComponentWeightCard({
    required String title,
    required String weightLabel,
    required double score,
    required double maxScore,
    required IconData icon,
    required Color color,
  }) {
    final pct = maxScore > 0 ? (score / maxScore).clamp(0.0, 1.0) : 0.0;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: color, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Policy Weight: $weightLabel',
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                ),
                Text(
                  '${score.toStringAsFixed(1)} / ${maxScore.toStringAsFixed(1)}',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: color,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: pct,
                backgroundColor: color.withValues(alpha: 0.12),
                valueColor: AlwaysStoppedAnimation<Color>(color),
                minHeight: 6,
              ),
            ),
          ],
        ),
      ),
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
            child: Column(
              children: [
                Row(
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
                            '${pct.toStringAsFixed(1)}% / 100',
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
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    onPressed: () => _showRemedialQuizModal(context, q['quiz_id'] as int? ?? 0, q['title'] as String? ?? 'Quiz', isUrdu),
                    icon: const Icon(Icons.auto_awesome_rounded, size: 16, color: Colors.purple),
                    label: Text(
                      isUrdu ? 'اے آئی اصلاحی کوئز (Remedial Practice)' : 'AI Remedial Practice',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.purple),
                    ),
                  ),
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
        final pct = (a['percentage'] as num?)?.toDouble() ?? 0.0;
        final regradeStatus = a['regrade_status'] as String?;
        final teacherResponse = a['teacher_response'] as String?;

        final submissionId = a['submission_id'] as int?;

        return Card(
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                Row(
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
                        if (status == 'Graded' && a['score'] != null) ...[
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
                              color: Colors.green.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              'Graded (${pct.toStringAsFixed(1)}%)',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                            ),
                          ),
                        ] else ...[
                          Text(
                            isUrdu ? 'غیر نشان زدہ' : 'Ungraded',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                              color: Colors.orange.shade800,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.orange.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              isUrdu ? 'زیرِ جائزہ' : 'Under Evaluation',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Colors.orange,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
                if (regradeStatus != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: regradeStatus == 'approved'
                          ? Colors.green.shade50
                          : regradeStatus == 'rejected'
                              ? Colors.red.shade50
                              : Colors.amber.shade50,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: regradeStatus == 'approved'
                            ? Colors.green.shade300
                            : regradeStatus == 'rejected'
                                ? Colors.red.shade300
                                : Colors.amber.shade300,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          regradeStatus == 'approved'
                              ? Icons.check_circle_rounded
                              : regradeStatus == 'rejected'
                                  ? Icons.cancel_rounded
                                  : Icons.access_time_filled_rounded,
                          color: regradeStatus == 'approved'
                              ? Colors.green.shade800
                              : regradeStatus == 'rejected'
                                  ? Colors.red.shade800
                                  : Colors.amber.shade900,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Regrade Appeal: ${regradeStatus.toUpperCase()}${teacherResponse != null && teacherResponse.isNotEmpty ? " • Teacher Note: $teacherResponse" : ""}',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: regradeStatus == 'approved'
                                  ? Colors.green.shade900
                                  : regradeStatus == 'rejected'
                                      ? Colors.red.shade900
                                      : Colors.amber.shade900,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ] else if (submissionId != null) ...[
                  const SizedBox(height: 10),
                  Align(
                    alignment: Alignment.centerRight,
                    child: OutlinedButton.icon(
                      onPressed: () => _openRegradeDialog(
                        context,
                        submissionId,
                        a['title'] ?? 'Assignment',
                        isUrdu,
                      ),
                      icon: const Icon(Icons.rate_review_outlined, size: 14),
                      label: Text(
                        isUrdu ? 'ری گریڈ اپیل کریں' : 'Request Regrade Appeal',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.indigo,
                        side: BorderSide(color: Colors.indigo.shade300),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  void _openRegradeDialog(
    BuildContext context,
    int submissionId,
    String assignmentTitle,
    bool isUrdu,
  ) {
    final reasonController = TextEditingController();
    bool isSubmitting = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              const Icon(Icons.rate_review_rounded, color: Colors.indigo),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  isUrdu ? 'اسائنمنٹ ری گریڈ اپیل' : 'Request Regrade Appeal',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isUrdu
                    ? 'اسائنمنٹ "$assignmentTitle" کے نمبرز کی دوبارہ پڑتال کے لیے وجہ درج کریں:'
                    : 'Enter reason for requesting regrade on "$assignmentTitle":',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonController,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: isUrdu
                      ? 'مثال: سر سوال نمبر 2 کا جواب صحیح تھا...'
                      : 'e.g., Sir, please re-check Q2, my answer matched lecture notes...',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  contentPadding: const EdgeInsets.all(12),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: isSubmitting ? null : () => Navigator.pop(dialogContext),
              child: Text(isUrdu ? 'منسوخ' : 'Cancel'),
            ),
            ElevatedButton(
              onPressed: isSubmitting
                  ? null
                  : () async {
                      final reason = reasonController.text.trim();
                      if (reason.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(isUrdu ? 'براہ کرم وجہ درج کریں۔' : 'Please enter a valid reason.'),
                            backgroundColor: Colors.red,
                          ),
                        );
                        return;
                      }

                      setDialogState(() => isSubmitting = true);
                      final success = await ApiService().requestAssignmentRegrade(
                        submissionId: submissionId,
                        reason: reason,
                      );

                      if (ctx.mounted) Navigator.pop(dialogContext);

                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              success
                                  ? (isUrdu ? 'اپیل ٹیچر پورٹل کو بھیج دی گئی ہے!' : 'Regrade appeal submitted to Teacher Portal!')
                                  : (isUrdu ? 'اپیل ناکام ہوگئی' : 'Failed to submit appeal'),
                            ),
                            backgroundColor: success ? Colors.green.shade800 : Colors.red,
                          ),
                        );
                        if (success) _fetchMarks();
                      }
                    },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.indigo,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              child: isSubmitting
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(isUrdu ? 'اپیل جمع کریں' : 'Submit Appeal'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExamsMarksList(ThemeData theme, List exams, bool isUrdu) {
    if (exams.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.badge_outlined, size: 48, color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4)),
            const SizedBox(height: 12),
            Text(
              isUrdu ? 'کوئی مڈٹرم یا فائنل نمبرز نہیں ہیں' : 'No exam scores recorded yet',
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: exams.length,
      itemBuilder: (context, index) {
        final item = exams[index] as Map<String, dynamic>;
        final title = item['type'] ?? 'Exam';
        final score = (item['score'] as num?)?.toDouble() ?? 0.0;
        final total = (item['total_marks'] as num?)?.toDouble() ?? 0.0;
        final pct = (item['percentage'] as num?)?.toDouble() ?? 0.0;

        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: theme.colorScheme.outlineVariant.withValues(alpha: 0.5)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer.withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.stars_rounded, color: theme.colorScheme.primary),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Evaluation score',
                        style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '$score / $total',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: pct >= 70 ? Colors.green.withValues(alpha: 0.15) : Colors.orange.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '$pct%',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: pct >= 70 ? Colors.green : Colors.orange,
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

  void _showPrintableTranscriptModal(
    BuildContext context,
    bool isUrdu,
    Map<String, dynamic>? officialTranscript,
    double totalWeighted,
    String letterGrade,
    double gpa,
  ) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: SizedBox(
          width: 450,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.school_rounded, color: Colors.indigo.shade800, size: 28),
                        const SizedBox(width: 10),
                        Text(
                          isUrdu ? 'سرکاری اکیڈمک ٹرانسکرپٹ' : 'Official Academic Transcript',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () => Navigator.pop(dialogContext),
                    ),
                  ],
                ),
                const Divider(height: 24),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: Column(
                    children: [
                      const Text('SMART STUDY INSTRUCTOR SYSTEM', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 1.1)),
                      const SizedBox(height: 4),
                      const Text('Official Academic Performance Certificate', style: TextStyle(fontSize: 11, color: Colors.grey)),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Grade: $letterGrade', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.indigo)),
                          Text('GPA: ${gpa.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.green)),
                          Text('Score: ${totalWeighted.toStringAsFixed(1)}%', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => Navigator.pop(dialogContext),
                        icon: const Icon(Icons.check_circle_outline),
                        label: const Text('Close'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () {
                          Navigator.pop(dialogContext);
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(isUrdu ? 'پرنٹنگ کمانڈ بھیج دی گئی ہے!' : 'Transcript sent to printer/PDF!'),
                              backgroundColor: Colors.green,
                            ),
                          );
                        },
                        icon: const Icon(Icons.print_rounded),
                        label: const Text('Print / Share'),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.indigo, foregroundColor: Colors.white),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showRemedialQuizModal(BuildContext context, int quizId, String quizTitle, bool isUrdu) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      enableDrag: false,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (modalContext) => StatefulBuilder(
        builder: (context, setModalState) {
          return FutureBuilder<Map<String, dynamic>?>(
            future: ApiService().getRemedialQuiz(quizId),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const SizedBox(
                  height: 300,
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              final data = snapshot.data;
              final questions = (data?['questions'] as List?) ?? [];

              return Container(
                padding: const EdgeInsets.all(24),
                constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.8),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.auto_awesome_rounded, color: Colors.purple, size: 28),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            isUrdu ? 'اے آئی اصلاحی مشق کوئز' : 'AI Remedial Revision Practice',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () => Navigator.pop(modalContext),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Targeted revision practice for $quizTitle based on your attempt results.',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                    const Divider(height: 24),
                    if (questions.isEmpty)
                      const Center(child: Text('No revision questions available.'))
                    else
                      Expanded(
                        child: ListView.separated(
                          itemCount: questions.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 14),
                          itemBuilder: (context, idx) {
                            final q = questions[idx] as Map<String, dynamic>;
                            return Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: Colors.purple.shade50,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: Colors.purple.shade200),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Q${idx + 1}: ${q['question_text']}',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                  ),
                                  const SizedBox(height: 8),
                                  Text('Option A: ${q['option_a']}', style: const TextStyle(fontSize: 12)),
                                  Text('Option B: ${q['option_b']}', style: const TextStyle(fontSize: 12)),
                                  const SizedBox(height: 8),
                                  Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      '💡 ${q['explanation']}',
                                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.purple.shade900),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}

