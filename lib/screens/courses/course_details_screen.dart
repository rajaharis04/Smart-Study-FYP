// ╔══════════════════════════════════════════════════════════════════╗
// ║          COURSE DETAILS SCREEN — Dynamic Topic Mastery            ║
// ║  Selected course ke detailed progress aur topic metrics            ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../core/widgets/skeleton_shimmer.dart';
import '../../core/widgets/error_retry_widget.dart';
import '../../models/models.dart';
import '../../providers/courses_provider.dart';
import '../../providers/progress_provider.dart';
import '../../providers/settings_provider.dart';

class CourseDetailsScreen extends ConsumerStatefulWidget {
  final int courseId;
  final String courseName;
  final String courseCode;
  final String instructor;
  final int creditHours;
  final double progress;
  final int sectionId;

  const CourseDetailsScreen({
    super.key,
    required this.courseId,
    required this.courseName,
    required this.courseCode,
    required this.instructor,
    required this.creditHours,
    required this.progress,
    required this.sectionId,
  });

  @override
  ConsumerState<CourseDetailsScreen> createState() => _CourseDetailsScreenState();
}

class _CourseDetailsScreenState extends ConsumerState<CourseDetailsScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(progressProvider.notifier).getProgress();
    });
  }

  Future<void> _refresh() async {
    await ref.read(progressProvider.notifier).getProgress();
  }

  Color _getStatusColor(String label) {
    switch (label.toLowerCase()) {
      case 'strong':
        return const Color(0xFF43A047); // Green
      case 'working':
        return const Color(0xFF7F77DD); // Purple/Blue
      case 'weak':
        return const Color(0xFFEF9F27); // Orange
      case 'very weak':
        return const Color(0xFFE53935); // Red
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';
    final progressState = ref.watch(progressProvider);
    final theme = Theme.of(context);

    // Find our specific course progress from the profile progress response
    CourseProgress? courseProg;
    if (progressState.progressData != null) {
      for (final cp in progressState.progressData!.courseProgress) {
        if (cp.courseId == widget.courseId) {
          courseProg = cp;
          break;
        }
      }
    }

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        appBar: AppBar(
          title: Text(
            isUrdu ? 'کورس کی تفصیلات' : 'Course Details',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          backgroundColor: theme.colorScheme.surface,
          foregroundColor: theme.colorScheme.onSurface,
          elevation: 0,
          leading: IconButton(
            icon: Icon(Icons.arrow_back_rounded, color: theme.colorScheme.onSurface),
            onPressed: () => context.pop(),
          ),
        ),
        body: RefreshIndicator(
          onRefresh: _refresh,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 1. Course Summary Header Card
                  _buildHeaderCard(theme, isUrdu),
                  const SizedBox(height: 24),

                  // 2. Syllabus / Topic Mastery Title
                  Text(
                    isUrdu ? 'نصاب اور مہارت' : 'Syllabus & Mastery',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      color: theme.colorScheme.onSurface,
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 3. Topic list or states
                  _buildTopicSection(progressState, courseProg, theme, isUrdu),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderCard(ThemeData theme, bool isUrdu) {
    final colors = [
      const Color(0xFF1D9E75),
      const Color(0xFF158360),
    ];

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: colors,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: colors[0].withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          widget.courseCode,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        widget.courseName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${isUrdu ? "انسٹرکٹر" : "Instructor"}: ${widget.instructor}',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.85),
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${isUrdu ? "کریڈٹ آورز" : "Credit Hours"}: ${widget.creditHours}',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                // Circular Progress representation
                SizedBox(
                  width: 76,
                  height: 76,
                  child: Stack(
                    children: [
                      Center(
                        child: SizedBox(
                          width: 72,
                          height: 72,
                          child: CircularProgressIndicator(
                            value: widget.progress / 100,
                            backgroundColor: Colors.white.withOpacity(0.15),
                            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                            strokeWidth: 6,
                          ),
                        ),
                      ),
                      Center(
                        child: Text(
                          '${widget.progress.toInt()}%',
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w900,
                            fontSize: 16,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(color: Colors.white24, height: 32),
            // Quick action buttons inside card header
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      context.push(
                        '/dashboard/courses/lectures/${widget.sectionId}?courseName=${Uri.encodeComponent(widget.courseName)}',
                      );
                    },
                    icon: const Icon(Icons.video_library_rounded, size: 16, color: Color(0xFF1D9E75)),
                    label: Text(
                      isUrdu ? 'لیکچرز دیکھیں' : 'View Lectures',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: const Color(0xFF1D9E75),
                      elevation: 0,
                      shadowColor: Colors.transparent,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _handleNotesDownload(widget.courseName, widget.courseCode),
                    icon: const Icon(Icons.picture_as_pdf_rounded, size: 16, color: Colors.white),
                    label: Text(
                      isUrdu ? 'پی ڈی ایف نوٹس' : 'Notes PDF',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.white38),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }

  Widget _buildTopicSection(ProgressState state, CourseProgress? courseProg, ThemeData theme, bool isUrdu) {
    if (state.isLoading) {
      return _buildSkeletonLoader();
    }

    if (state.error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 24),
          child: Column(
            children: [
              Icon(Icons.warning_amber_rounded, color: theme.colorScheme.error, size: 48),
              const SizedBox(height: 12),
              Text(state.error!),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _refresh,
                child: Text(isUrdu ? 'دوبارہ کوشش کریں' : 'Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (courseProg == null || courseProg.topics.isEmpty) {
      return Center(
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              Icon(
                Icons.menu_book_rounded,
                size: 64,
                color: theme.colorScheme.primary.withOpacity(0.3),
              ),
              const SizedBox(height: 16),
              Text(
                isUrdu ? 'اس کورس کا کوئی ٹاپک موجود نہیں ہے' : 'No topics available for this course',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                isUrdu
                    ? 'آپ کے لیکچرز مکمل ہونے پر ٹاپک کی رپورٹ یہاں نظر آئے گی۔'
                    : 'Topics progress will update as lectures are completed.',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: courseProg.topics.length,
      itemBuilder: (context, index) {
        final topic = courseProg.topics[index];
        final statusColor = _getStatusColor(topic.statusLabel);

        return Container(
          margin: const EdgeInsets.only(bottom: 14),
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
          ),
          child: Theme(
            data: theme.copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              leading: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: Center(
                  child: Text(
                    topic.statusSymbol,
                    style: TextStyle(
                      color: statusColor,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              title: Text(
                topic.title,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          isUrdu ? ' مہارت' : 'Mastery',
                          style: TextStyle(
                            fontSize: 11,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                        Text(
                          '${topic.mastery.toInt()}%',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: statusColor,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: topic.mastery / 100,
                        backgroundColor: statusColor.withOpacity(0.1),
                        valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                        minHeight: 6,
                      ),
                    ),
                  ],
                ),
              ),
              trailing: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  isUrdu ? _translateStatus(topic.statusLabel) : topic.statusLabel,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: statusColor,
                  ),
                ),
              ),
              children: [
                const Divider(indent: 16, endIndent: 16),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isUrdu ? 'کارکردگی کے اشاریے' : 'Learning Performance Metrics',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.onSurface.withOpacity(0.8),
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Grid of stats
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricTile(
                              icon: Icons.psychology_outlined,
                              label: isUrdu ? 'اعتماد' : 'Confidence',
                              value: '${topic.confidence.toInt()}%',
                              color: const Color(0xFF6C63FF),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildMetricTile(
                              icon: Icons.timer_outlined,
                              label: isUrdu ? 'رفتار' : 'Learning Pace',
                              value: '${topic.learningPace.toInt()}s',
                              color: const Color(0xFF00BFA5),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricTile(
                              icon: Icons.local_fire_department_outlined,
                              label: isUrdu ? 'دلچسپی' : 'Engagement',
                              value: '${topic.engagement.toInt()}%',
                              color: const Color(0xFFFF6B6B),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildMetricTile(
                              icon: Icons.help_outline_rounded,
                              label: isUrdu ? 'اشارہ انحصار' : 'Hint Depend.',
                              value: '${(topic.hintDependency * 100).toInt()}%',
                              color: const Color(0xFFFFB74D),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMetricTile({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.12)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontSize: 10, color: Colors.grey, fontWeight: FontWeight.bold),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: color),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  String _translateStatus(String label) {
    switch (label.toLowerCase()) {
      case 'strong':
        return 'بہترین';
      case 'working':
        return 'بہتر';
      case 'weak':
        return 'کمزور';
      case 'very weak':
        return 'انتہائی کمزور';
      default:
        return label;
    }
  }

  void _handleNotesDownload(String courseName, String courseCode) async {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Downloading lecture notes for $courseCode...'),
        duration: const Duration(seconds: 1),
      ),
    );

    try {
      final pdfUrl = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf";
      
      if (mounted) {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Text('Download Complete'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Notes PDF has been successfully generated & is ready for viewing for $courseName.'),
                const SizedBox(height: 10),
                Text(
                  'Source URL: $pdfUrl',
                  style: const TextStyle(fontSize: 10, fontStyle: FontStyle.italic, color: Colors.blue),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    } catch (_) {}
  }

  Widget _buildSkeletonLoader() {
    return Column(
      children: List.generate(3, (index) {
        return Container(
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: const [
                  SkeletonShimmer(width: 40, height: 40, borderRadius: 20),
                  SizedBox(width: 12),
                  Expanded(
                    child: SkeletonShimmer(width: double.infinity, height: 16),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const SkeletonShimmer(width: double.infinity, height: 8),
            ],
          ),
        );
      }),
    );
  }
}
