// ╔══════════════════════════════════════════════════════════════════╗
// ║          COURSE REGISTRATION SCREEN                               ║
// ║  Students can register/withdraw from offered courses/sections.    ║
// ║  Withdrawal is blocked and hidden after the admin deadline.      ║
// ║  Bilingual support and dynamic remaining time countdown.         ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/settings_provider.dart';
import '../../providers/courses_provider.dart';
import '../../services/api_service.dart';

class CourseRegistrationScreen extends ConsumerStatefulWidget {
  const CourseRegistrationScreen({super.key});

  @override
  ConsumerState<CourseRegistrationScreen> createState() =>
      _CourseRegistrationScreenState();
}

class _CourseRegistrationScreenState
    extends ConsumerState<CourseRegistrationScreen> {
  final ApiService _apiService = ApiService();
  
  String? _semesterName;
  DateTime? _registrationDeadline;
  List<dynamic>? _sections;
  bool _isLoading = true;
  String? _errorMessage;
  Timer? _countdownTimer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    // Setup countdown refresh timer
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted && _registrationDeadline != null) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchData() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final data = await _apiService.getRegistrationOfferedCourses();
      if (!mounted) return;
      setState(() {
        _semesterName = data['semester_name'] as String?;
        final deadlineStr = data['registration_deadline'] as String?;
        _registrationDeadline =
            deadlineStr != null ? DateTime.parse(deadlineStr).toLocal() : null;
        _sections = data['sections'] as List<dynamic>?;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  Future<void> _register(int sectionId, String courseName) async {
    try {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(
          child: CircularProgressIndicator(),
        ),
      );
      
      await _apiService.registerCourse(sectionId);
      
      if (!mounted) return;
      Navigator.pop(context); // Close loading dialog
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            ref.read(settingsProvider).language == 'Urdu'
                ? '$courseName میں کامیابی سے رجسٹریشن ہو گئی۔'
                : 'Successfully registered in $courseName.',
          ),
          backgroundColor: Colors.green,
        ),
      );
      
      _fetchData();
      ref.read(coursesProvider.notifier).getMyCourses(); // Refresh student courses
    } catch (e) {
      if (!mounted) return;
      Navigator.pop(context); // Close loading dialog
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _withdraw(int sectionId, String courseName) async {
    final settings = ref.read(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          isUrdu ? 'کورس سے دستبرداری کی تصدیق' : 'Confirm Course Withdrawal',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        content: Text(
          isUrdu
              ? 'کیا آپ واقعی اس کورس سے خارج ہونا چاہتے ہیں؟ یہ عمل فوری نافذ العمل ہوگا۔'
              : 'Are you sure you want to withdraw from $courseName? This action cannot be undone during this session.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(isUrdu ? 'منسوخ کریں' : 'Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: Text(isUrdu ? 'دستبردار ہوں' : 'Withdraw'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(
          child: CircularProgressIndicator(),
        ),
      );
      
      await _apiService.withdrawCourse(sectionId);
      
      if (!mounted) return;
      Navigator.pop(context); // Close loading dialog
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            isUrdu
                ? '$courseName سے کامیابی کے ساتھ اخراج کر دیا گیا۔'
                : 'Successfully withdrawn from $courseName.',
          ),
          backgroundColor: Colors.amber[800],
        ),
      );
      
      _fetchData();
      ref.read(coursesProvider.notifier).getMyCourses(); // Refresh student courses
    } catch (e) {
      if (!mounted) return;
      Navigator.pop(context); // Close loading dialog
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  String _getCountdownText(DateTime deadline, bool isUrdu) {
    final now = DateTime.now();
    final difference = deadline.difference(now);

    if (difference.isNegative) {
      return isUrdu ? 'وقت ختم ہو چکا ہے' : 'Deadline Passed';
    }

    final days = difference.inDays;
    final hours = difference.inHours % 24;
    final minutes = difference.inMinutes % 60;
    final seconds = difference.inSeconds % 60;

    if (isUrdu) {
      return '$days دن، $hours گھنٹے، $minutes منٹ، $seconds سیکنڈ باقی';
    }
    return '$days days, $hours hrs, $minutes mins, $seconds secs remaining';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    final isClosed = _registrationDeadline != null &&
        DateTime.now().isAfter(_registrationDeadline!);

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        appBar: AppBar(
          title: Text(
            isUrdu ? 'کورسز کی رجسٹریشن' : 'Course Registration',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          backgroundColor: theme.colorScheme.surface,
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => context.pop(),
          ),
        ),
        body: _buildBody(theme, isUrdu, isClosed),
      ),
    );
  }

  Widget _buildBody(ThemeData theme, bool isUrdu, bool isClosed) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline_rounded, size: 64, color: theme.colorScheme.error),
              const SizedBox(height: 16),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _fetchData,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(isUrdu ? 'دوبارہ کوشش کریں' : 'Retry'),
              )
            ],
          ),
        ),
      );
    }

    final sectionsList = _sections ?? [];

    return RefreshIndicator(
      onRefresh: _fetchData,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          // ── Deadline & Session Banner ──────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Container(
                padding: const EdgeInsets.all(20.0),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      theme.colorScheme.primary,
                      theme.colorScheme.primary.withOpacity(0.8),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: theme.colorScheme.primary.withOpacity(0.2),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.school_rounded, color: Colors.white, size: 24),
                        const SizedBox(width: 8),
                        Text(
                          isUrdu
                              ? 'تعلیمی سیشن: ${_semesterName ?? ""}'
                              : 'Session: ${_semesterName ?? ""}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Divider(color: Colors.white24, height: 1),
                    const SizedBox(height: 16),
                    if (_registrationDeadline != null) ...[
                      Row(
                        children: [
                          const Icon(Icons.timer_rounded, color: Colors.white70, size: 18),
                          const SizedBox(width: 6),
                          Text(
                            isUrdu
                                ? 'آخری تاریخ: ${_registrationDeadline!.toString().substring(0, 16)}'
                                : 'Deadline: ${_registrationDeadline!.toString().substring(0, 16)}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          _getCountdownText(_registrationDeadline!, isUrdu),
                          style: TextStyle(
                            color: isClosed ? Colors.red[300] : Colors.amber[200],
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ] else ...[
                      Row(
                        children: [
                          const Icon(Icons.check_circle_outline_rounded, color: Colors.white70, size: 18),
                          const SizedBox(width: 6),
                          Text(
                            isUrdu ? 'ڈیڈ لائن: متعین نہیں ہے' : 'Deadline: Not Restricted',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),

          // ── Catalog Title ──────────────────────────────────────────────
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: Text(
                isUrdu ? 'دستیاب کورسز کا نصاب' : 'Offered Courses Catalog',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),

          // ── Catalog List ───────────────────────────────────────────────
          if (sectionsList.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.menu_book_rounded, size: 64, color: theme.colorScheme.primary.withOpacity(0.2)),
                      const SizedBox(height: 16),
                      Text(
                        isUrdu
                            ? 'اس سیشن میں فی الحال کوئی خودکار رجسٹریشن کے لیے کورس دستیاب نہیں ہے۔'
                            : 'No courses are offered for self-registration right now.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            )
          else
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final sec = sectionsList[index];
                  final isRegistered = sec['is_registered'] as bool? ?? false;
                  final sectionId = sec['section_id'] as int;
                  final courseCode = sec['course_code'] as String;
                  final courseName = sec['course_name'] as String;
                  final instructor = sec['instructor'] as String;
                  final sectionLabel = sec['section_label'] as String;
                  final schedule = sec['schedule'] as String?;
                  final room = sec['room'] as String?;
                  final creditHours = sec['credit_hours'] as int? ?? 3;

                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
                    child: Card(
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                        side: BorderSide(
                          color: isRegistered
                              ? Colors.green.withOpacity(0.5)
                              : theme.colorScheme.outline.withOpacity(0.08),
                          width: isRegistered ? 2.0 : 1.0,
                        ),
                      ),
                      color: isRegistered
                          ? Colors.green.withOpacity(0.02)
                          : theme.colorScheme.surface,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Badge and Code row
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: theme.colorScheme.primary.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    courseCode,
                                    style: TextStyle(
                                      color: theme.colorScheme.primary,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 11,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: theme.colorScheme.secondary.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    isUrdu ? 'سیکشن $sectionLabel' : 'Section $sectionLabel',
                                    style: TextStyle(
                                      color: theme.colorScheme.secondary,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 11,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            // Course Name
                            Text(
                              courseName,
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            // Details (Instructor, Credit Hours)
                            Row(
                              children: [
                                const Icon(Icons.person_rounded, size: 14, color: Colors.grey),
                                const SizedBox(width: 4),
                                Text(
                                  instructor,
                                  style: const TextStyle(fontSize: 13, color: Colors.grey),
                                ),
                                const SizedBox(width: 16),
                                const Icon(Icons.credit_card_rounded, size: 14, color: Colors.grey),
                                const SizedBox(width: 4),
                                Text(
                                  isUrdu ? '$creditHours کریڈٹ آورز' : '$creditHours Cr. Hours',
                                  style: const TextStyle(fontSize: 13, color: Colors.grey),
                                ),
                              ],
                            ),
                            // Schedule / Room if present
                            if ((schedule != null && schedule.isNotEmpty) ||
                                (room != null && room.isNotEmpty)) ...[
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  if (schedule != null && schedule.isNotEmpty) ...[
                                    const Icon(Icons.calendar_today_rounded, size: 14, color: Colors.grey),
                                    const SizedBox(width: 4),
                                    Text(
                                      schedule,
                                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                                    ),
                                    const SizedBox(width: 16),
                                  ],
                                  if (room != null && room.isNotEmpty) ...[
                                    const Icon(Icons.meeting_room_rounded, size: 14, color: Colors.grey),
                                    const SizedBox(width: 4),
                                    Text(
                                      isUrdu ? 'کمرہ $room' : 'Room $room',
                                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                                    ),
                                  ],
                                ],
                              ),
                            ],
                            const SizedBox(height: 16),
                            const Divider(height: 1),
                            const SizedBox(height: 12),
                            // Action Buttons
                            Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                if (isRegistered) ...[
                                  // Registered Status Badge
                                  Row(
                                    children: [
                                      const Icon(Icons.check_circle_rounded, color: Colors.green, size: 18),
                                      const SizedBox(width: 4),
                                      Text(
                                        isUrdu ? 'رجسٹرڈ' : 'Registered',
                                        style: const TextStyle(
                                          color: Colors.green,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const Spacer(),
                                  // Delete / Withdraw Button (Visible ONLY before deadline)
                                  if (!isClosed)
                                    TextButton.icon(
                                      onPressed: () => _withdraw(sectionId, courseName),
                                      icon: const Icon(Icons.delete_outline_rounded, size: 16, color: Colors.red),
                                      label: Text(
                                        isUrdu ? 'خارج کریں' : 'Unregister',
                                        style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w600, fontSize: 13),
                                      ),
                                    ),
                                ] else ...[
                                  // Register Button
                                  ElevatedButton.icon(
                                    onPressed: isClosed ? null : () => _register(sectionId, courseName),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: theme.colorScheme.primary,
                                      foregroundColor: Colors.white,
                                      elevation: 0,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                    ),
                                    icon: const Icon(Icons.app_registration_rounded, size: 16),
                                    label: Text(
                                      isUrdu ? 'رجسٹر کریں' : 'Register',
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
                childCount: sectionsList.length,
              ),
            ),
          // Bottom spacing
          const SliverToBoxAdapter(
            child: SizedBox(height: 40),
          )
        ],
      ),
    );
  }
}
