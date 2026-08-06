// ╔══════════════════════════════════════════════════════════════════╗
// ║           ASSIGNMENTS SCREEN — Dedicated Student Section         ║
// ║  Displays all active & published assignments with submission ui   ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';

class AssignmentQuestion {
  final int id;
  final String questionText;
  final String questionType; // 'short_answer' or 'long_answer'
  final int marks;

  AssignmentQuestion({
    required this.id,
    required this.questionText,
    required this.questionType,
    required this.marks,
  });

  factory AssignmentQuestion.fromJson(Map<String, dynamic> json) {
    return AssignmentQuestion(
      id: json['id'] as int? ?? 0,
      questionText: json['question_text'] as String? ?? '',
      questionType: json['question_type'] as String? ?? 'short_answer',
      marks: json['marks'] as int? ?? 5,
    );
  }
}

class StudentAssignmentItem {
  final int id;
  final String title;
  final String courseName;
  final String courseCode;
  final String description;
  final int totalMarks;
  final DateTime dueDate;
  final String type; // 'manual' or 'ai_generated'
  bool isSubmitted;
  final int submittedCount;
  final int totalStudents;
  final int? score;
  final List<AssignmentQuestion> questions;

  StudentAssignmentItem({
    required this.id,
    required this.title,
    required this.courseName,
    required this.courseCode,
    required this.description,
    required this.totalMarks,
    required this.dueDate,
    required this.type,
    required this.isSubmitted,
    this.submittedCount = 0,
    this.totalStudents = 1,
    this.score,
    required this.questions,
  });

  factory StudentAssignmentItem.fromJson(Map<String, dynamic> json) {
    final qList = (json['questions'] as List? ?? [])
        .map((q) => AssignmentQuestion.fromJson(q as Map<String, dynamic>))
        .toList();
    return StudentAssignmentItem(
      id: json['id'] as int? ?? 0,
      title: json['title'] as String? ?? 'Assignment',
      courseName: json['course_name'] as String? ?? 'Course',
      courseCode: json['course_code'] as String? ?? 'CS',
      description: json['description'] as String? ?? '',
      totalMarks: json['total_marks'] as int? ?? 100,
      dueDate: json['due_date'] != null
          ? DateTime.parse(json['due_date'] as String)
          : DateTime.now().add(const Duration(days: 7)),
      type: json['type'] as String? ?? 'manual',
      isSubmitted: json['is_submitted'] as bool? ?? false,
      submittedCount: json['submitted_count'] as int? ?? 0,
      totalStudents: json['total_students'] as int? ?? 1,
      score: json['score'] as int?,
      questions: qList,
    );
  }
}

class AssignmentsScreen extends ConsumerStatefulWidget {
  const AssignmentsScreen({super.key});

  @override
  ConsumerState<AssignmentsScreen> createState() => _AssignmentsScreenState();
}

class _AssignmentsScreenState extends ConsumerState<AssignmentsScreen> {
  bool _isLoading = false;
  String _selectedFilter = 'all'; // 'all', 'pending', 'submitted', 'overdue'
  String _searchQuery = '';

  List<StudentAssignmentItem> _assignments = [];

  @override
  void initState() {
    super.initState();
    _fetchAssignments();
  }

  Future<void> _fetchAssignments() async {
    setState(() => _isLoading = true);
    try {
      final rawList = await ApiService().getStudentAssignmentsRaw();
      if (mounted) {
        setState(() {
          _assignments = rawList.map((j) => StudentAssignmentItem.fromJson(j)).toList();
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _assignments = [];
          _isLoading = false;
        });
      }
    }
  }

  List<StudentAssignmentItem> get _filteredAssignments {
    return _assignments.where((a) {
      final matchesSearch = a.title.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          a.courseName.toLowerCase().contains(_searchQuery.toLowerCase());
      if (!matchesSearch) return false;

      final isOverdue = DateTime.now().isAfter(a.dueDate) && !a.isSubmitted;

      if (_selectedFilter == 'submitted') return a.isSubmitted;
      if (_selectedFilter == 'pending') return !a.isSubmitted && !isOverdue;
      if (_selectedFilter == 'overdue') return isOverdue;
      // In default view, hide submitted assignments
      return !a.isSubmitted;
    }).toList();
  }

  void _openSubmissionSheet(StudentAssignmentItem item) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _AssignmentSubmissionSheet(
        item: item,
        onSubmitted: () {
          setState(() {
            item.isSubmitted = true;
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    final totalCount = _assignments.length;
    final submittedCount = _assignments.where((a) => a.isSubmitted).length;
    final pendingCount = _assignments.where((a) => !a.isSubmitted).length;
    final totalSubmittedAll = _assignments.fold(0, (sum, a) => sum + a.submittedCount);
    final totalCapacity = _assignments.fold(0, (sum, a) => sum + a.totalStudents);
    final avgSubmissionRate = totalCapacity > 0 ? ((totalSubmittedAll / totalCapacity) * 100).round() : 0;

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        appBar: AppBar(
          title: Text(
            isUrdu ? 'اسائنمنٹس سیکشن' : 'Assignments Section',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          centerTitle: false,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: () {
                setState(() => _isLoading = true);
                Future.delayed(const Duration(milliseconds: 500), () {
                  if (mounted) setState(() => _isLoading = false);
                });
              },
              tooltip: isUrdu ? 'ریفریش کریں' : 'Refresh',
            ),
          ],
        ),
        body: Column(
          children: [
            // Top Stats Overview Grid (Matching Quizzes Screen Style)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: Row(
                children: [
                  Expanded(
                    child: _buildStatCard(
                      theme,
                      title: isUrdu ? 'کل اسائنمنٹس' : 'Total',
                      value: '$totalCount',
                      icon: Icons.assignment_outlined,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildStatCard(
                      theme,
                      title: isUrdu ? 'بقیہ' : 'Pending',
                      value: '$pendingCount',
                      icon: Icons.pending_actions_rounded,
                      color: Colors.orange,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildStatCard(
                      theme,
                      title: isUrdu ? 'جمع شدہ' : 'Submitted',
                      value: '$submittedCount',
                      icon: Icons.task_alt_rounded,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _buildStatCard(
                      theme,
                      title: isUrdu ? 'اوسط کی شرح' : 'Sub. Rate',
                      value: '$avgSubmissionRate%',
                      icon: Icons.analytics_outlined,
                      color: Colors.purple,
                    ),
                  ),
                ],
              ),
            ),

            // Search Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: TextField(
                onChanged: (val) => setState(() => _searchQuery = val),
                decoration: InputDecoration(
                  hintText: isUrdu ? 'اسائنمنٹ تلاش کریں...' : 'Search assignments...',
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
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Row(
                children: [
                  _buildFilterChip(theme, 'all', isUrdu ? 'سب' : 'All'),
                  _buildFilterChip(theme, 'pending', isUrdu ? 'بقیہ' : 'Pending'),
                  _buildFilterChip(theme, 'submitted', isUrdu ? 'جمع شدہ' : 'Submitted'),
                  _buildFilterChip(theme, 'overdue', isUrdu ? 'تاخیر شدہ' : 'Overdue'),
                ],
              ),
            ),

            const SizedBox(height: 4),

            // List of assignments
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _filteredAssignments.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.assignment_outlined,
                                size: 64,
                                color: theme.colorScheme.onSurfaceVariant.withOpacity(0.4),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                isUrdu ? 'کوئی اسائنمنٹ موجود نہیں' : 'No assignments found',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                isUrdu
                                    ? 'ٹیچر کے نئی اسائنمنٹ پوسٹ کرنے کا انتظار کریں'
                                    : 'Check back later for newly published assignments.',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                                ),
                              ),
                            ],
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredAssignments.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 12),
                          itemBuilder: (context, index) {
                            final item = _filteredAssignments[index];
                            return _buildAssignmentCard(theme, item, isUrdu);
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(
    ThemeData theme, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 15,
              color: theme.colorScheme.onSurface,
            ),
          ),
          Text(
            title,
            style: TextStyle(
              fontSize: 10,
              color: theme.colorScheme.onSurfaceVariant,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(ThemeData theme, String key, String label) {
    final isSelected = _selectedFilter == key;
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
        onSelected: (_) => setState(() => _selectedFilter = key),
      ),
    );
  }

  Widget _buildAssignmentCard(ThemeData theme, StudentAssignmentItem item, bool isUrdu) {
    final isOverdue = DateTime.now().isAfter(item.dueDate) && !item.isSubmitted;
    final dueFormatted = '${item.dueDate.day}/${item.dueDate.month}/${item.dueDate.year}';

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openSubmissionSheet(item),
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
                      color: theme.colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '${item.courseCode} — ${item.courseName}',
                      style: TextStyle(
                        color: theme.colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.bold,
                        fontSize: 11,
                      ),
                    ),
                  ),
                  const Spacer(),
                  // Question Type Badge (Short & Long Questions)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.notes_rounded, size: 12, color: Colors.blue),
                        SizedBox(width: 4),
                        Text(
                          'Short & Long Qs',
                          style: TextStyle(color: Colors.blue, fontSize: 10, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                item.title,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  height: 1.3,
                ),
              ),
              if (item.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  item.description,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              const SizedBox(height: 12),
              // Submission Stats Bar
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.4),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.groups_outlined, size: 14, color: theme.colorScheme.onSurfaceVariant),
                    const SizedBox(width: 6),
                    Text(
                      'Submissions: ${item.submittedCount} / ${item.totalStudents}',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: theme.colorScheme.onSurfaceVariant),
                    ),
                    const Spacer(),
                    if (item.score != null) ...[
                      const Icon(Icons.star_rounded, size: 14, color: Colors.amber),
                      const SizedBox(width: 4),
                      Text(
                        'Score: ${item.score}/${item.totalMarks}',
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.amber),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Icon(Icons.numbers_rounded, size: 14, color: theme.colorScheme.onSurfaceVariant),
                  const SizedBox(width: 4),
                  Text(
                    '${item.totalMarks} ${isUrdu ? 'نمبر' : 'Marks'}',
                    style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
                  ),
                  const SizedBox(width: 14),
                  Icon(
                    isOverdue ? Icons.warning_amber_rounded : Icons.schedule_rounded,
                    size: 14,
                    color: isOverdue ? Colors.red : theme.colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${isUrdu ? 'آخری تاریخ' : 'Due'}: $dueFormatted',
                    style: TextStyle(
                      fontSize: 12,
                      color: isOverdue ? Colors.red : theme.colorScheme.onSurfaceVariant,
                      fontWeight: isOverdue ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                  const Spacer(),
                  ElevatedButton(
                    onPressed: () => _openSubmissionSheet(item),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: item.isSubmitted ? Colors.green : (isOverdue ? Colors.red : theme.colorScheme.primary),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: Text(
                      item.isSubmitted
                          ? (isUrdu ? 'جمع شدہ' : 'Submitted')
                          : (isOverdue ? (isUrdu ? 'تاخیر شدہ' : 'Overdue') : (isUrdu ? 'جمع کروائیں' : 'Submit')),
                      style: const TextStyle(fontWeight: FontWeight.bold),
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
//  Assignment Submission Sheet (Short & Long Answer Questions)
// ════════════════════════════════════════════════════════════════════

class _AssignmentSubmissionSheet extends StatefulWidget {
  final StudentAssignmentItem item;
  final VoidCallback onSubmitted;

  const _AssignmentSubmissionSheet({
    required this.item,
    required this.onSubmitted,
  });

  @override
  State<_AssignmentSubmissionSheet> createState() => _AssignmentSubmissionSheetState();
}

class _AssignmentSubmissionSheetState extends State<_AssignmentSubmissionSheet> {
  final Map<int, TextEditingController> _controllers = {};
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    for (var q in widget.item.questions) {
      _controllers[q.id] = TextEditingController();
    }
  }

  @override
  void dispose() {
    for (var c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() async {
    bool hasAnyAnswer = _controllers.values.any((c) => c.text.trim().isNotEmpty);
    if (!hasAnyAnswer) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please answer at least one question before submitting.')),
      );
      return;
    }

    setState(() => _submitting = true);

    final List<Map<String, dynamic>> answersPayload = [];
    _controllers.forEach((qId, controller) {
      if (controller.text.trim().isNotEmpty) {
        answersPayload.add({
          'question_id': qId,
          'answer_text': controller.text.trim(),
        });
      }
    });

    try {
      await ApiService().submitStudentAssignment(
        assignmentId: widget.item.id,
        answers: answersPayload,
      );
      if (mounted) {
        widget.onSubmitted();
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Assignment "${widget.item.title}" submitted to teacher successfully!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _submitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to submit assignment: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
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
              children: [
                Expanded(
                  child: Text(
                    widget.item.title,
                    style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Info Box
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.4),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Instructions:',
                          style: theme.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          widget.item.description,
                          style: theme.textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Chip(
                              label: Text('${widget.item.totalMarks} Total Marks'),
                              visualDensity: VisualDensity.compact,
                            ),
                            const SizedBox(width: 8),
                            Chip(
                              label: Text('${widget.item.questions.length} Short/Long Questions'),
                              visualDensity: VisualDensity.compact,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  Text(
                    'Assignment Questions:',
                    style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),

                  // Questions List (Short and Long questions only)
                  ...widget.item.questions.asMap().entries.map((entry) {
                    final index = entry.key;
                    final q = entry.value;
                    final controller = _controllers[q.id]!;
                    final isLong = q.questionType == 'long_answer';

                    return Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        border: Border.all(color: theme.colorScheme.outlineVariant),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: isLong ? Colors.purple.withOpacity(0.1) : Colors.blue.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  isLong ? 'Long Answer' : 'Short Answer',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: isLong ? Colors.purple : Colors.blue,
                                  ),
                                ),
                              ),
                              const Spacer(),
                              Text(
                                '${q.marks} Marks',
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Q${index + 1}: ${q.questionText}',
                            style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: controller,
                            maxLines: isLong ? 6 : 3,
                            decoration: InputDecoration(
                              hintText: isLong
                                  ? 'Write your detailed response / code here...'
                                  : 'Write your concise 2-4 sentence response here...',
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                          ),
                        ],
                      ),
                    );
                  }),

                  const SizedBox(height: 8),

                  // File upload simulation button
                  OutlinedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('File attachment selected (PDF / Code / ZIP)')),
                      );
                    },
                    icon: const Icon(Icons.attach_file_rounded),
                    label: const Text('Attach File (PDF/Doc/ZIP)'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                  const SizedBox(height: 20),

                  ElevatedButton(
                    onPressed: _submitting ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 50),
                      backgroundColor: theme.colorScheme.primary,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: _submitting
                        ? const CircularProgressIndicator(color: Colors.white)
                        : const Text(
                            'Submit Assignment',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
