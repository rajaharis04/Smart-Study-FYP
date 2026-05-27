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
  final bool showBackButton;
  final bool hideAppBar;
  final VoidCallback? onDeadlinePassed;

  const CourseRegistrationScreen({
    super.key,
    this.showBackButton = true,
    this.hideAppBar = false,
    this.onDeadlinePassed,
  });

  @override
  ConsumerState<CourseRegistrationScreen> createState() =>
      _CourseRegistrationScreenState();
}

class _CourseRegistrationScreenState
    extends ConsumerState<CourseRegistrationScreen> {
  final ApiService _apiService = ApiService();
  
  String? _semesterName;
  DateTime? _registrationDeadline;
  DateTime? _serverTime;
  DateTime? _responseReceivedAt;
  List<dynamic>? _sections;
  bool _isLoading = true;
  bool _isActionLoading = false;
  String? _errorMessage;
  Timer? _countdownTimer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    // Setup countdown refresh timer
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted && _registrationDeadline != null) {
        final remaining = _getRemainingDuration();
        if (remaining != null && remaining.isNegative) {
          _countdownTimer?.cancel();
          widget.onDeadlinePassed?.call();
        }
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Duration? _getRemainingDuration() {
    if (_registrationDeadline == null || _serverTime == null || _responseReceivedAt == null) {
      return null;
    }
    final initialDiff = _registrationDeadline!.difference(_serverTime!);
    final elapsed = DateTime.now().difference(_responseReceivedAt!);
    return initialDiff - elapsed;
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
        final serverTimeStr = data['server_time'] as String?;

        String? normDeadline = deadlineStr;
        if (normDeadline != null && !normDeadline.endsWith('Z') && !normDeadline.contains(RegExp(r'[+-]\d{2}:\d{2}$'))) {
          normDeadline += 'Z';
        }
        _registrationDeadline = normDeadline != null ? DateTime.parse(normDeadline).toLocal() : null;

        String? normServer = serverTimeStr;
        if (normServer != null && !normServer.endsWith('Z') && !normServer.contains(RegExp(r'[+-]\d{2}:\d{2}$'))) {
          normServer += 'Z';
        }
        _serverTime = normServer != null ? DateTime.parse(normServer).toLocal() : null;
        _responseReceivedAt = DateTime.now();

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
    setState(() {
      _isActionLoading = true;
    });
    try {
      await _apiService.registerCourse(sectionId);
      
      if (!mounted) return;
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isActionLoading = false;
        });
      }
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

    setState(() {
      _isActionLoading = true;
    });
    try {
      await _apiService.withdrawCourse(sectionId);
      
      if (!mounted) return;
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isActionLoading = false;
        });
      }
    }
  }

  String _getCountdownText(Duration? remaining, bool isUrdu) {
    if (remaining == null) {
      return '';
    }
    if (remaining.isNegative) {
      return isUrdu ? 'وقت ختم ہو چکا ہے' : 'Deadline Passed';
    }

    final days = remaining.inDays;
    final hours = remaining.inHours % 24;
    final minutes = remaining.inMinutes % 60;
    final seconds = remaining.inSeconds % 60;

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

    final remaining = _getRemainingDuration();
    final isClosed = remaining != null && remaining.isNegative;

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        appBar: widget.hideAppBar
            ? null
            : AppBar(
                title: Text(
                  isUrdu ? 'کورسز کی رجسٹریشن' : 'Course Registration',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                backgroundColor: theme.colorScheme.surface,
                elevation: 0,
                leading: widget.showBackButton
                    ? IconButton(
                        icon: const Icon(Icons.arrow_back_rounded),
                        onPressed: () => context.pop(),
                      )
                    : null,
              ),
        body: Stack(
          children: [
            _buildBody(theme, isUrdu, isClosed),
            if (_isActionLoading)
              Container(
                color: Colors.black54,
                child: const Center(
                  child: CircularProgressIndicator(),
                ),
              ),
          ],
        ),
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
    final availableSections = sectionsList.where((sec) => (sec['is_registered'] as bool? ?? false) == false).toList();
    final registeredSections = sectionsList.where((sec) => (sec['is_registered'] as bool? ?? false) == true).toList();
    final remaining = _getRemainingDuration();

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
                          _getCountdownText(remaining, isUrdu),
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

          if (!isClosed) ...[
            // ── AVAILABLE COURSES SECTION ──────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Text(
                  isUrdu ? 'دستیاب کورسز' : 'Available Courses',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),

            if (availableSections.isEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24.0, horizontal: 16.0),
                  child: Center(
                    child: Text(
                      isUrdu
                          ? 'تمام دستیاب کورسز رجسٹرڈ ہیں۔'
                          : 'All available courses are registered.',
                      style: TextStyle(
                        color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6),
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ),
              )
            else
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    return _buildCourseCard(context, availableSections[index], isUrdu, isClosed, theme);
                  },
                  childCount: availableSections.length,
                ),
              ),

            // ── REGISTERED COURSES SECTION ──────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
                child: Text(
                  isUrdu ? 'رجسٹرڈ کورسز' : 'Registered Courses',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),

            if (registeredSections.isEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24.0, horizontal: 16.0),
                  child: Center(
                    child: Text(
                      isUrdu
                          ? 'آپ نے ابھی تک کوئی کورس رجسٹر نہیں کیا ہے۔'
                          : 'You have not registered for any courses yet.',
                      style: TextStyle(
                        color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6),
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ),
              )
            else
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    return _buildCourseCard(context, registeredSections[index], isUrdu, isClosed, theme);
                  },
                  childCount: registeredSections.length,
                ),
              ),
          ] else ...[
            // ── ENROLLED COURSES (AFTER DEADLINE) ─────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Text(
                  isUrdu ? 'شامل شدہ کورسز' : 'Enrolled Courses',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),

            if (registeredSections.isEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24.0, horizontal: 16.0),
                  child: Center(
                    child: Text(
                      isUrdu
                          ? 'رجسٹریشن کی آخری تاریخ گزر چکی ہے اور آپ نے کوئی کورس رجسٹر نہیں کیا تھا۔'
                          : 'Registration deadline has passed and you did not register for any courses.',
                      style: TextStyle(
                        color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6),
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ),
              )
            else
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    return _buildCourseCard(context, registeredSections[index], isUrdu, isClosed, theme);
                  },
                  childCount: registeredSections.length,
                ),
              ),
          ],

          // Bottom spacing
          const SliverToBoxAdapter(
            child: SizedBox(height: 40),
          )
        ],
      ),
    );
  }

  Widget _buildCourseCard(BuildContext context, dynamic sec, bool isUrdu, bool isClosed, ThemeData theme) {
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
                  if (isClosed) ...[
                    Row(
                      children: [
                        const Icon(Icons.check_circle_rounded, color: Colors.green, size: 18),
                        const SizedBox(width: 4),
                        Text(
                          isUrdu ? 'ثبت شدہ (رجسٹرڈ)' : 'Enrolled',
                          style: const TextStyle(
                            color: Colors.green,
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ] else if (isRegistered) ...[
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
                    TextButton.icon(
                      onPressed: () => _withdraw(sectionId, courseName),
                      icon: const Icon(Icons.delete_outline_rounded, size: 16, color: Colors.red),
                      label: Text(
                        isUrdu ? 'خارج کریں' : 'Unregister',
                        style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                    ),
                  ] else ...[
                    ElevatedButton.icon(
                      onPressed: () => _register(sectionId, courseName),
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
  }
}

