// ╔══════════════════════════════════════════════════════════════════╗
// ║              LEARNING PROFILE SCREEN — BKT Student Dashboard     ║
// ║  Displays overall learning score, topic masteries, badges,       ║
// ║  weekly trend, and weak topic revision recommendations           ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../providers/learning_provider.dart';
import '../../providers/settings_provider.dart';

class LearningProfileScreen extends ConsumerStatefulWidget {
  const LearningProfileScreen({super.key});

  @override
  ConsumerState<LearningProfileScreen> createState() => _LearningProfileScreenState();
}

class _LearningProfileScreenState extends ConsumerState<LearningProfileScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(learningProfileProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(learningProfileProvider);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          isUrdu ? 'سیکھنے کا ماڈل پروفائل' : 'My Learning Profile',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(learningProfileProvider.notifier).refresh(),
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        state.error!,
                        style: TextStyle(color: theme.colorScheme.error),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: () => ref.read(learningProfileProvider.notifier).refresh(),
                        child: Text(isUrdu ? 'دوبارہ کوشش کریں' : 'Retry'),
                      ),
                    ],
                  ),
                )
              : state.profile == null
                  ? Center(child: Text(isUrdu ? 'کوئی ڈیٹا موجود نہیں ہے' : 'No learning profile data found.'))
                  : RefreshIndicator(
                      onRefresh: () async {
                        ref.read(learningProfileProvider.notifier).refresh();
                      },
                      child: SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildScoreHeader(theme, state.profile!, isUrdu),
                            const SizedBox(height: 20),
                            if (state.profile!.badges.isNotEmpty) ...[
                              _buildBadgesSection(theme, state.profile!.badges, isUrdu),
                              const SizedBox(height: 20),
                            ],
                            if (state.profile!.weakTopics.isNotEmpty) ...[
                              _buildWeakTopicsCard(theme, state.profile!.weakTopics, isUrdu),
                              const SizedBox(height: 20),
                            ],
                            _buildCoursesTopicBreakdown(theme, state.profile!.courses, isUrdu),
                          ],
                        ),
                      ),
                    ),
    );
  }

  Widget _buildScoreHeader(ThemeData theme, LearningProfile profile, bool isUrdu) {
    final score = profile.overallLearningScore;
    final color = score >= 75
        ? Colors.green
        : score >= 50
            ? Colors.orange
            : Colors.red;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 80,
                height: 80,
                child: CircularProgressIndicator(
                  value: score / 100.0,
                  strokeWidth: 8,
                  backgroundColor: color.withOpacity(0.15),
                  color: color,
                ),
              ),
              Text(
                '${score.toStringAsFixed(0)}%',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isUrdu ? 'مجموعی طور پر سیکھنے کا اسکور' : 'Overall Learning Score',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isUrdu
                      ? 'مجموعی ماسٹری: ${profile.overallMastery.toStringAsFixed(1)}%'
                      : 'Overall Mastery: ${profile.overallMastery.toStringAsFixed(1)}%',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.textTheme.bodySmall?.color,
                  ),
                ),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    score >= 75
                        ? (isUrdu ? 'بہترین رفتار 🔥' : 'Excellent Progress 🔥')
                        : score >= 50
                            ? (isUrdu ? 'اچھی کوشش 💪' : 'Good Effort 💪')
                            : (isUrdu ? 'توجہ کی ضرورت ہے ⚠️' : 'Needs Focus ⚠️'),
                    style: TextStyle(
                      color: color,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
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

  Widget _buildBadgesSection(ThemeData theme, List<LearningBadge> badges, bool isUrdu) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          isUrdu ? 'حاصل کردہ بیجز 🏆' : 'Earned Badges 🏆',
          style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 100,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: badges.length,
            separatorBuilder: (_, __) => const SizedBox(width: 12),
            itemBuilder: (context, index) {
              final badge = badges[index];
              return Container(
                width: 140,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: theme.dividerColor.withOpacity(0.3),
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(badge.icon, style: const TextStyle(fontSize: 24)),
                    const SizedBox(height: 4),
                    Text(
                      badge.title,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      badge.description,
                      style: TextStyle(fontSize: 9, color: theme.textTheme.bodySmall?.color),
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
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

  Widget _buildWeakTopicsCard(ThemeData theme, List<Map<String, dynamic>> weakTopics, bool isUrdu) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.red.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 22),
              const SizedBox(width: 8),
              Text(
                isUrdu ? 'کمزور موضوعات (ریویژن کی ضرورت ہے)' : 'Focus Areas (Needs Revision)',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.red,
                  fontSize: 14,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...weakTopics.map((wt) {
            final title = wt['topic_title'] ?? '';
            final code = wt['course_code'] ?? '';
            final m = (wt['mastery'] as num?)?.toDouble() ?? 0.0;
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$code: $title',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                        Text(
                          isUrdu ? 'ماسٹری اسکور: ${m.toStringAsFixed(0)}%' : 'Mastery: ${m.toStringAsFixed(0)}%',
                          style: const TextStyle(fontSize: 11, color: Colors.red),
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

  Widget _buildCoursesTopicBreakdown(ThemeData theme, List<CourseLearning> courses, bool isUrdu) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          isUrdu ? 'کورس کے لحاظ سے بریک ڈاؤن' : 'Course Topic Mastery Breakdown',
          style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        ...courses.map((course) {
          return Card(
            margin: const EdgeInsets.only(bottom: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${course.courseCode} - ${course.courseName}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  const Divider(height: 20),
                  ...course.topics.map((t) {
                    final color = t.masteryScore >= 75
                        ? Colors.green
                        : t.masteryScore >= 50
                            ? Colors.orange
                            : Colors.red;

                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(
                                  t.topicTitle,
                                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                                ),
                              ),
                              Text(
                                '${t.masteryScore.toStringAsFixed(0)}%',
                                style: TextStyle(fontWeight: FontWeight.bold, color: color),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          LinearProgressIndicator(
                            value: t.masteryScore / 100.0,
                            backgroundColor: color.withOpacity(0.15),
                            color: color,
                            minHeight: 6,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          const SizedBox(height: 4),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                isUrdu ? 'اعتماد: ${t.confidenceScore.toStringAsFixed(0)}%' : 'Confidence: ${t.confidenceScore.toStringAsFixed(0)}%',
                                style: TextStyle(fontSize: 10, color: theme.textTheme.bodySmall?.color),
                              ),
                              Text(
                                isUrdu ? 'انحصار: ${t.hintDependencyPct.toStringAsFixed(0)}%' : 'Hint Dep: ${t.hintDependencyPct.toStringAsFixed(0)}%',
                                style: TextStyle(fontSize: 10, color: theme.textTheme.bodySmall?.color),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ],
              ),
            ),
          );
        }).toList(),
      ],
    );
  }
}
