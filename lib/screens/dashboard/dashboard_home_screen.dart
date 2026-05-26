// ╔══════════════════════════════════════════════════════════════════╗
// ║              DASHBOARD HOME SCREEN                               ║
// ║  Progress card, summary tiles, today's lectures, active quizzes  ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../providers/auth_provider.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/settings_provider.dart';
import '../../models/models.dart';

// ════════════════════════════════════════════════════════════════════
//  DashboardHomeScreen
// ════════════════════════════════════════════════════════════════════

class DashboardHomeScreen extends ConsumerStatefulWidget {
  const DashboardHomeScreen({super.key});

  @override
  ConsumerState<DashboardHomeScreen> createState() =>
      _DashboardHomeScreenState();
}

class _DashboardHomeScreenState extends ConsumerState<DashboardHomeScreen> {
  @override
  void initState() {
    super.initState();
    // Screen load hone par data fetch karo
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(dashboardProvider.notifier).fetchDashboard();
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashState = ref.watch(dashboardProvider);
    final authState = ref.watch(authProvider);
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';
    final firstName = (authState.userName ?? 'Student').split(' ').first;

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: RefreshIndicator(
        color: theme.colorScheme.primary,
        onRefresh: () => ref.read(dashboardProvider.notifier).refresh(),
        child: CustomScrollView(
          slivers: [
            // ── Header ───────────────────────────────────────────────
            SliverToBoxAdapter(
              child: _buildHeader(context, theme, firstName),
            ),

            // ── Content ──────────────────────────────────────────────
            if (dashState.isLoading && !dashState.hasData) ...[
              SliverToBoxAdapter(child: _buildSkeleton(theme)),
            ] else if (dashState.error != null && !dashState.hasData) ...[
              SliverFillRemaining(
                child: _buildError(theme, dashState.error!),
              ),
            ] else ...[
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Progress card
                      _buildProgressCard(theme, dashState.dashboardData),
                      const SizedBox(height: 24),
                      // Announcements from Admin/Teacher
                      if ((dashState.announcements ?? []).isNotEmpty) ...[
                        _buildSectionHeader(theme, isUrdu ? 'اعلانات' : 'Announcements', onViewAll: () {
                          context.push('/dashboard/profile/notifications');
                        }),
                        const SizedBox(height: 12),
                        _buildAnnouncementsList(theme, dashState.announcements ?? []),
                        const SizedBox(height: 28),
                      ],
                      // Summary tiles grid
                      _buildSummaryGrid(theme, dashState.dashboardData),
                      const SizedBox(height: 28),
                      // My Courses
                      _buildSectionHeader(theme, settings.translate('my_courses'), onViewAll: () {
                        context.go(AppConstants.routeDashboardCourses);
                      }),
                      const SizedBox(height: 12),
                      _buildCoursesList(theme, dashState.courses ?? []),
                      const SizedBox(height: 28),
                      // Today's Lectures
                      _buildSectionHeader(theme, isUrdu ? 'آج کے لیکچرز' : "Today's Lectures"),
                      const SizedBox(height: 12),
                      _buildLecturesList(
                          theme, dashState.todayLectures ?? []),
                      const SizedBox(height: 28),
                      // Active Quizzes
                      if ((dashState.activeQuizzes ?? []).isNotEmpty) ...[
                        _buildSectionHeader(theme, isUrdu ? 'سرگرم کوئز' : 'Active Quizzes'),
                        const SizedBox(height: 12),
                        _buildQuizzesList(
                            theme, dashState.activeQuizzes ?? []),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ── Header with greeting ─────────────────────────────────────────

  Widget _buildHeader(
      BuildContext context, ThemeData theme, String firstName) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    final hour = DateTime.now().hour;
    String greeting;
    if (isUrdu) {
      greeting = hour < 12
          ? 'صبح بخیر'
          : hour < 17
              ? 'سہ پہر بخیر'
              : 'شام بخیر';
    } else {
      greeting = hour < 12
          ? 'Good Morning'
          : hour < 17
              ? 'Good Afternoon'
              : 'Good Evening';
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 60, 20, 28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            theme.colorScheme.primary,
            theme.colorScheme.primary.withOpacity(0.85),
            const Color(0xFF1D9E75),
          ],
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isUrdu ? '$greeting،' : '$greeting,',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  firstName,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.3,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isUrdu ? 'خوش آمدید! بہترین کام جاری رکھیں 🎯' : 'Welcome back! Keep up the great work 🎯',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.75),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.15),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: Colors.white.withOpacity(0.25),
              ),
            ),
            child: const Icon(
              Icons.school_rounded,
              color: Colors.white,
              size: 28,
            ),
          ),
        ],
      ),
    );
  }

  // ── Circular progress card ───────────────────────────────────────

  Widget _buildProgressCard(ThemeData theme, Dashboard? data) {
    final progress = data?.overallProgress ?? 0.0;
    final label = progress >= 80
        ? 'Excellent! 🔥'
        : progress >= 60
            ? 'Keep it up! 💪'
            : progress >= 40
                ? 'Good progress 📚'
                : 'Just getting started 🌱';

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.primary.withOpacity(0.12),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // Circular progress indicator
          SizedBox(
            width: 90,
            height: 90,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CustomPaint(
                  size: const Size(90, 90),
                  painter: _CircleProgressPainter(
                    progress: progress / 100,
                    color: theme.colorScheme.primary,
                    bgColor: theme.colorScheme.primary.withOpacity(0.12),
                  ),
                ),
                Text(
                  '${progress.toInt()}%',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Overall Progress',
                  style: TextStyle(
                    color: theme.colorScheme.onSurfaceVariant,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  label,
                  style: TextStyle(
                    color: theme.colorScheme.onSurface,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: progress / 100,
                    minHeight: 8,
                    backgroundColor:
                        theme.colorScheme.primary.withOpacity(0.12),
                    valueColor: AlwaysStoppedAnimation<Color>(
                      theme.colorScheme.primary,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── 2x2 summary tiles grid ───────────────────────────────────────

  Widget _buildSummaryGrid(ThemeData theme, Dashboard? data) {
    final tiles = [
      _SummaryTile(
        icon: Icons.menu_book_rounded,
        label: 'Courses',
        value: '${data?.totalCourses ?? 0}',
        color: const Color(0xFF6C63FF),
        onTap: () => GoRouter.of(context).go(AppConstants.routeDashboardCourses),
      ),
      _SummaryTile(
        icon: Icons.fact_check_rounded,
        label: 'Attendance',
        value: '${(data?.attendancePercentage ?? 0).toInt()}%',
        color: const Color(0xFF00BFA5),
        onTap: () => GoRouter.of(context).go(AppConstants.routeDashboardAttendance),
      ),
      _SummaryTile(
        icon: Icons.quiz_rounded,
        label: 'Quizzes',
        value: '${data?.activeQuizzesCount ?? 0}',
        color: const Color(0xFFFF6B6B),
        onTap: null,
      ),
      _SummaryTile(
        icon: Icons.assignment_rounded,
        label: 'Assignments',
        value: '1',
        color: const Color(0xFFFFB74D),
        onTap: null,
      ),
    ];

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.6,
      children: tiles.map((t) => _buildSummaryTile(theme, t)).toList(),
    );
  }

  Widget _buildSummaryTile(ThemeData theme, _SummaryTile tile) {
    if (tile.onTap == null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: tile.color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: tile.color.withOpacity(0.2)),
        ),
        child: _buildSummaryTileContent(theme, tile),
      );
    }
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: tile.onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: tile.color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: tile.color.withOpacity(0.2)),
        ),
        child: _buildSummaryTileContent(theme, tile),
      ),
    );
  }

  Widget _buildSummaryTileContent(ThemeData theme, _SummaryTile tile) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: tile.color.withOpacity(0.15),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(tile.icon, color: tile.color, size: 20),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                tile.value,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: tile.color,
                ),
              ),
              Text(
                tile.label,
                style: TextStyle(
                  fontSize: 11,
                  color: theme.colorScheme.onSurfaceVariant,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ── Section header ───────────────────────────────────────────────

  Widget _buildSectionHeader(ThemeData theme, String title,
      {VoidCallback? onViewAll}) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: theme.colorScheme.onSurface,
          ),
        ),
        if (onViewAll != null)
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onViewAll,
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: Text(
                  isUrdu ? 'سب دیکھیں' : 'View All',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  // ── Announcements list ───────────────────────────────────────────

  Widget _buildAnnouncementsList(ThemeData theme, List<Map<String, dynamic>> list) {
    return Column(
      children: list.take(2).map((ann) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                theme.colorScheme.primary.withOpacity(0.08),
                theme.colorScheme.secondary.withOpacity(0.04),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: theme.colorScheme.primary.withOpacity(0.2),
              width: 1.5,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.campaign_rounded,
                  color: theme.colorScheme.primary,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      ann['title'] ?? '',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      ann['content'] ?? '',
                      style: TextStyle(
                        fontSize: 12.5,
                        height: 1.4,
                        color: theme.colorScheme.onSurfaceVariant.withOpacity(0.9),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  // ── Courses list ─────────────────────────────────────────────────

  Widget _buildCoursesList(ThemeData theme, List<Course> courses) {
    if (courses.isEmpty) {
      return _buildEmptyCard(
          theme, Icons.menu_book_outlined, 'No courses enrolled yet');
    }
    final shown = courses.take(3).toList();
    return Column(
      children: shown.asMap().entries.map((entry) {
        final colors = [
          const Color(0xFF6C63FF),
          const Color(0xFF00BFA5),
          const Color(0xFFFF6B6B),
          const Color(0xFFFFB74D),
        ];
        final color = colors[entry.key % colors.length];
        return _buildCourseCard(theme, entry.value, color);
      }).toList(),
    );
  }

  Widget _buildCourseCard(ThemeData theme, Course course, Color color) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          final sectionId = course.sectionId ?? 0;
          context.push(
            '/dashboard/courses/lectures/$sectionId?courseName=${Uri.encodeComponent(course.name)}',
          );
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Center(
                  child: Text(
                    course.code.substring(0, math.min(2, course.code.length)),
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: color,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      course.name,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      course.instructor,
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSurfaceVariant,
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
    );
  }

  // ── Today's lectures ─────────────────────────────────────────────

  Widget _buildLecturesList(ThemeData theme, List<TodayLecture> lectures) {
    if (lectures.isEmpty) {
      return _buildEmptyCard(
          theme, Icons.video_library_outlined, 'No lectures scheduled today');
    }
    return Column(
      children: lectures
          .take(3)
          .map((l) => _buildLectureCard(theme, l))
          .toList(),
    );
  }

  Widget _buildLectureCard(ThemeData theme, TodayLecture lecture) {
    final time = '${lecture.scheduledTime.hour.toString().padLeft(2, '0')}:'
        '${lecture.scheduledTime.minute.toString().padLeft(2, '0')}';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => context.push(
            '${AppConstants.routeLecture}/${lecture.lectureId}'),
        borderRadius: BorderRadius.circular(16),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
            border: lecture.isCompleted
                ? Border.all(
                    color: theme.colorScheme.primary.withOpacity(0.3))
                : null,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: lecture.isCompleted
                      ? theme.colorScheme.primary.withOpacity(0.12)
                      : const Color(0xFF6C63FF).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  lecture.isCompleted
                      ? Icons.check_circle_rounded
                      : Icons.play_circle_rounded,
                  color: lecture.isCompleted
                      ? theme.colorScheme.primary
                      : const Color(0xFF6C63FF),
                  size: 26,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      lecture.title,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${lecture.courseName}  •  $time',
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              if (lecture.isCompleted)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Done',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Active quizzes ───────────────────────────────────────────────

  Widget _buildQuizzesList(ThemeData theme, List<ActiveQuiz> quizzes) {
    return Column(
      children: quizzes
          .take(3)
          .map((q) => _buildQuizCard(theme, q))
          .toList(),
    );
  }

  Widget _buildQuizCard(ThemeData theme, ActiveQuiz quiz) {
    final dueText = quiz.dueDate != null
        ? 'Due ${quiz.dueDate!.day}/${quiz.dueDate!.month}'
        : 'No deadline';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          if (quiz.lectureId != null) {
            context.push('${AppConstants.routeLecture}/${quiz.lectureId}');
          }
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFFF6B6B).withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: const Color(0xFFFF6B6B).withOpacity(0.2),
            ),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF6B6B).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.quiz_rounded,
                  color: Color(0xFFFF6B6B),
                  size: 22,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      quiz.lectureTitle,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${quiz.quizTypeLabel}  •  $dueText',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFFFF6B6B),
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
    );
  }

  // ── Empty state ──────────────────────────────────────────────────

  Widget _buildEmptyCard(ThemeData theme, IconData icon, String message) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: theme.colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: theme.colorScheme.onSurfaceVariant, size: 28),
          const SizedBox(width: 14),
          Text(
            message,
            style: TextStyle(
              color: theme.colorScheme.onSurfaceVariant,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  // ── Skeleton loader ──────────────────────────────────────────────

  Widget _buildSkeleton(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
      child: Column(
        children: [
          _SkeletonBox(height: 110, radius: 20, theme: theme),
          const SizedBox(height: 24),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.6,
            children: List.generate(
              4,
              (_) => _SkeletonBox(height: double.infinity, radius: 16, theme: theme),
            ),
          ),
          const SizedBox(height: 28),
          ...List.generate(
            3,
            (_) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _SkeletonBox(height: 76, radius: 16, theme: theme),
            ),
          ),
        ],
      ),
    );
  }

  // ── Error state ──────────────────────────────────────────────────

  Widget _buildError(ThemeData theme, String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.wifi_off_rounded,
                  size: 48, color: Colors.red),
            ),
            const SizedBox(height: 20),
            Text(
              'Could not load dashboard',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: theme.colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              error,
              style: TextStyle(
                color: theme.colorScheme.onSurfaceVariant,
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () =>
                  ref.read(dashboardProvider.notifier).refresh(),
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(
                    horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  Helper: Skeleton box for loading state
// ════════════════════════════════════════════════════════════════════

class _SkeletonBox extends StatefulWidget {
  final double height;
  final double radius;
  final ThemeData theme;

  const _SkeletonBox({
    required this.height,
    required this.radius,
    required this.theme,
  });

  @override
  State<_SkeletonBox> createState() => _SkeletonBoxState();
}

class _SkeletonBoxState extends State<_SkeletonBox>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.4, end: 0.9).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => Container(
        height: widget.height,
        decoration: BoxDecoration(
          color: widget.theme.colorScheme.onSurface
              .withOpacity(0.06 * _anim.value * 2),
          borderRadius: BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  Helper: Circular progress painter
// ════════════════════════════════════════════════════════════════════

class _CircleProgressPainter extends CustomPainter {
  final double progress;
  final Color color;
  final Color bgColor;

  _CircleProgressPainter({
    required this.progress,
    required this.color,
    required this.bgColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - 10) / 2;
    const startAngle = -math.pi / 2;

    // Background circle
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = bgColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8,
    );

    // Progress arc
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      2 * math.pi * progress,
      false,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_CircleProgressPainter old) =>
      old.progress != progress;
}

// ════════════════════════════════════════════════════════════════════
//  Summary tile data class
// ════════════════════════════════════════════════════════════════════

class _SummaryTile {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final VoidCallback? onTap;

  const _SummaryTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    this.onTap,
  });
}
