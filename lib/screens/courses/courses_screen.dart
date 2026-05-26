// ╔══════════════════════════════════════════════════════════════════╗
// ║              COURSES SCREEN — Dynamic Courses list               ║
// ║  Student ke enrolled courses ki detailed list                    ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../core/widgets/skeleton_shimmer.dart';
import '../../core/widgets/error_retry_widget.dart';
import '../../models/models.dart';
import '../../providers/courses_provider.dart';
import '../../providers/settings_provider.dart';
import '../../providers/qa_history_provider.dart';
import '../lecture/qa_search_delegate.dart';

class CoursesScreen extends ConsumerStatefulWidget {
  const CoursesScreen({super.key});

  @override
  ConsumerState<CoursesScreen> createState() => _CoursesScreenState();
}

class _CoursesScreenState extends ConsumerState<CoursesScreen> {
  @override
  void initState() {
    super.initState();
    // Load enrolled courses when screen is opened
    Future.microtask(() {
      ref.read(coursesProvider.notifier).getMyCourses();
    });
  }

  Future<void> _refresh() async {
    await ref.read(coursesProvider.notifier).getMyCourses();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(coursesProvider);
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        appBar: AppBar(
          title: Text(settings.translate('my_courses')),
          backgroundColor: theme.colorScheme.surface,
          elevation: 0,
          centerTitle: false,
          actions: [
            IconButton(
              icon: const Icon(Icons.app_registration_rounded),
              tooltip: isUrdu ? 'کورس رجسٹریشن' : 'Course Registration',
              onPressed: () {
                context.push(AppConstants.routeCourseRegistration);
              },
            ),
            IconButton(
              icon: const Icon(Icons.saved_search_rounded),
              tooltip: isUrdu ? 'محفوظ کردہ سوالات تلاش کریں' : 'Search Saved Doubts',
              onPressed: () {
                ref.read(qaHistoryProvider.notifier).loadBookmarks();
                showSearch(
                  context: context,
                  delegate: QaSearchDelegate(ref: ref),
                );
              },
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _refresh,
          child: _buildBody(state, theme),
        ),
      ),
    );
  }

  Widget _buildBody(CoursesState state, ThemeData theme) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    if (state.isLoading) {
      return _buildSkeletonLoader();
    }

    final isOfflineCache = state.error == 'Offline Mode (Cached Data)';
    if (state.error != null && !isOfflineCache) {
      return ErrorRetryWidget(
        errorMessage: state.error!,
        onRetry: _refresh,
      );
    }

    final courses = state.courses;

    if (courses.isEmpty) {
      return Center(
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.menu_book_rounded,
                size: 80,
                color: theme.colorScheme.primary.withOpacity(0.3),
              ),
              const SizedBox(height: 16),
              Text(
                'No courses enrolled',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Your enrolled courses will appear here',
                style: TextStyle(
                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () => context.push(AppConstants.routeCourseRegistration),
                style: ElevatedButton.styleFrom(
                  backgroundColor: theme.colorScheme.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                icon: const Icon(Icons.app_registration_rounded, size: 18),
                label: Text(
                  isUrdu ? 'کورسز رجسٹر کریں' : 'Register for Courses',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (isOfflineCache)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
            color: Colors.amber.withOpacity(0.12),
            child: Row(
              children: [
                const Icon(Icons.offline_bolt_rounded, color: Colors.amber, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Offline Mode: Displaying cached courses.',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: theme.colorScheme.onSurface.withOpacity(0.8),
                    ),
                  ),
                ),
              ],
            ),
          ),
        // Total Enrolled Header
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Enrolled Courses',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '(${courses.length} courses enrolled)',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        
        // List view of courses
        Expanded(
          child: ListView.builder(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            itemCount: courses.length,
            itemBuilder: (context, index) {
              final course = courses[index];
              final colors = [
                const Color(0xFF6C63FF),
                const Color(0xFF00BFA5),
                const Color(0xFFFF6B6B),
                const Color(0xFFFFB74D),
              ];
              final color = colors[index % colors.length];
              final progressPct = course.progress ?? 0.0;

              return Container(
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: color.withOpacity(0.08),
                      blurRadius: 15,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Course details row
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 56,
                            height: 56,
                            decoration: BoxDecoration(
                              color: color.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: Center(
                              child: Text(
                                course.code.length >= 2
                                    ? course.code.substring(0, 2)
                                    : course.code,
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: color,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  course.name,
                                  style: TextStyle(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w700,
                                    color: theme.colorScheme.onSurface,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${course.code}  |  ${course.instructor}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: theme.colorScheme.onSurfaceVariant,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Credit Hours: ${course.creditHours ?? 3}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: theme.colorScheme.onSurfaceVariant.withOpacity(0.8),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      
                      // Progress Bar Section
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Course Progress / Mastery',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                          Text(
                            '${progressPct.toInt()}%',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: color,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: progressPct / 100,
                          backgroundColor: color.withOpacity(0.12),
                          valueColor: AlwaysStoppedAnimation<Color>(color),
                          minHeight: 8,
                        ),
                      ),
                      const SizedBox(height: 20),
                      
                      // Actions row
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () {
                                // Navigate to lectures sub-screen using sectionId
                                final sectionId = course.sectionId ?? 0;
                                context.push(
                                  '/dashboard/courses/lectures/$sectionId?courseName=${Uri.encodeComponent(course.name)}',
                                );
                              },
                              icon: const Icon(Icons.video_library_rounded, size: 16),
                              label: const Text('View Lectures'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: color.withOpacity(0.1),
                                foregroundColor: color,
                                elevation: 0,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _handleNotesDownload(course),
                              icon: const Icon(Icons.picture_as_pdf_rounded, size: 16),
                              label: const Text('Notes PDF'),
                              style: OutlinedButton.styleFrom(
                                side: BorderSide(color: theme.colorScheme.outline.withOpacity(0.5)),
                                foregroundColor: theme.colorScheme.onSurface,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                padding: const EdgeInsets.symmetric(vertical: 12),
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
          ),
        ),
      ],
    );
  }

  void _handleNotesDownload(Course course) async {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Downloading lecture notes for ${course.code}...'),
        duration: const Duration(seconds: 1),
      ),
    );
    
    try {
      // Trigger notes download path fetch
      final pdfUrl = await ref.read(coursesProvider.notifier).downloadNotes(course.id);
      
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Text('Download Complete'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Notes PDF has been successfully generated & is ready for viewing.'),
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
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to download notes: ${e.toString()}'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  Widget _buildSkeletonLoader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 20, 20, 10),
          child: SkeletonShimmer(width: 150, height: 20),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
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
                  children: [
                    Row(
                      children: [
                        const SkeletonShimmer(width: 56, height: 56, borderRadius: 14),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: const [
                              SkeletonShimmer(width: double.infinity, height: 18),
                              SizedBox(height: 6),
                              SkeletonShimmer(width: 120, height: 14),
                              SizedBox(height: 6),
                              SkeletonShimmer(width: 80, height: 12),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    const SkeletonShimmer(width: double.infinity, height: 14),
                    const SizedBox(height: 20),
                    Row(
                      children: const [
                        Expanded(child: SkeletonShimmer(width: double.infinity, height: 40, borderRadius: 10)),
                        SizedBox(width: 12),
                        Expanded(child: SkeletonShimmer(width: double.infinity, height: 40, borderRadius: 10)),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
