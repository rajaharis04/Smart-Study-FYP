// ╔══════════════════════════════════════════════════════════════════╗
// ║          COURSE LECTURES SCREEN — Dynamic Lectures List          ║
// ║  Selected course/section ke saare lectures dikhata hai           ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../core/constants.dart';
import '../../core/widgets/skeleton_shimmer.dart';
import '../../core/widgets/error_retry_widget.dart';
import '../../providers/courses_provider.dart';

class CourseLecturesScreen extends ConsumerStatefulWidget {
  final int sectionId;
  final String courseName;

  const CourseLecturesScreen({
    super.key,
    required this.sectionId,
    required this.courseName,
  });

  @override
  ConsumerState<CourseLecturesScreen> createState() => _CourseLecturesScreenState();
}

class _CourseLecturesScreenState extends ConsumerState<CourseLecturesScreen> {
  @override
  void initState() {
    super.initState();
    // Load lectures when screen is opened
    Future.microtask(() {
      ref.read(coursesProvider.notifier).getCourseLectures(widget.sectionId);
    });
  }

  Future<void> _refresh() async {
    await ref.read(coursesProvider.notifier).getCourseLectures(widget.sectionId);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(coursesProvider);
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(
          widget.courseName,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        backgroundColor: theme.colorScheme.surface,
        elevation: 0,
        centerTitle: false,
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: _buildBody(state, theme),
      ),
    );
  }

  Widget _buildBody(CoursesState state, ThemeData theme) {
    if (state.isLecturesLoading) {
      return _buildSkeletonLoader();
    }

    if (state.lecturesError != null) {
      return ErrorRetryWidget(
        errorMessage: state.lecturesError!,
        onRetry: _refresh,
      );
    }

    final lectures = state.courseLectures;

    if (lectures.isEmpty) {
      return Center(
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.video_library_outlined,
                size: 80,
                color: theme.colorScheme.primary.withOpacity(0.3),
              ),
              const SizedBox(height: 16),
              Text(
                'No lectures uploaded yet',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Check back later for newly published videos.',
                style: TextStyle(
                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      itemCount: lectures.length,
      itemBuilder: (context, index) {
        final lecture = lectures[index];
        
        // Status indicator configurations
        Color badgeColor;
        String badgeText;
        if (lecture.status.toLowerCase() == 'published') {
          badgeColor = const Color(0xFF00BFA5); // Green (Live)
          badgeText = 'Live';
        } else if (lecture.status.toLowerCase() == 'upcoming') {
          badgeColor = const Color(0xFF64B5F6); // Blue (Upcoming)
          badgeText = 'Upcoming';
        } else if (lecture.status.toLowerCase() == 'archived') {
          badgeColor = Colors.grey; // Grey (Archived)
          badgeText = 'Archived';
        } else {
          badgeColor = const Color(0xFF6C63FF); // Purple (Ready)
          badgeText = 'Ready';
        }

        final publishDateStr = DateFormat('MMM dd, yyyy').format(lecture.publishDate);

        return Container(
          margin: const EdgeInsets.only(bottom: 14),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.04),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () {
                // Redirect to pre-assessment path (which forwards to lecture player)
                context.push('${AppConstants.routeLecture}/${lecture.id}');
              },
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    // Play circle container
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: badgeColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        Icons.play_circle_fill_rounded,
                        color: badgeColor,
                        size: 28,
                      ),
                    ),
                    const SizedBox(width: 14),
                    
                    // Lecture text detail
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: badgeColor.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  badgeText,
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    color: badgeColor,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                lecture.durationFormatted,
                                style: TextStyle(
                                  fontSize: 11,
                                  color: theme.colorScheme.onSurfaceVariant,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            lecture.title,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.onSurface,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Published: $publishDateStr',
                            style: TextStyle(
                              fontSize: 11,
                              color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                            ),
                          ),
                        ],
                      ),
                    ),
                    
                    Icon(
                      Icons.chevron_right_rounded,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildSkeletonLoader() {
    return ListView.builder(
      padding: const EdgeInsets.all(20),
      itemCount: 5,
      itemBuilder: (context, index) {
        return Container(
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              const SkeletonShimmer(width: 48, height: 48, borderRadius: 12),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        SkeletonShimmer(width: 50, height: 16, borderRadius: 6),
                        SizedBox(width: 8),
                        SkeletonShimmer(width: 40, height: 12, borderRadius: 4),
                      ],
                    ),
                    const SizedBox(height: 10),
                    const SkeletonShimmer(width: double.infinity, height: 16, borderRadius: 6),
                    const SizedBox(height: 6),
                    const SkeletonShimmer(width: 100, height: 12, borderRadius: 4),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
