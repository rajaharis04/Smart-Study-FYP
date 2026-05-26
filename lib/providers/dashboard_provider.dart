// ╔══════════════════════════════════════════════════════════════════╗
// ║              DASHBOARD PROVIDER — RIVERPOD STATE                 ║
// ║  3 parallel API calls: stats, today's lectures, active quizzes   ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';

// ════════════════════════════════════════════════════════════════════
//  DashboardState — All dashboard data in one immutable object
// ════════════════════════════════════════════════════════════════════

class DashboardState {
  final bool isLoading;
  final String? error;
  final Dashboard? dashboardData;       // Overall stats
  final List<TodayLecture>? todayLectures;
  final List<ActiveQuiz>? activeQuizzes;
  final List<Course>? courses;
  final List<Map<String, dynamic>>? announcements;

  const DashboardState({
    this.isLoading = false,
    this.error,
    this.dashboardData,
    this.todayLectures,
    this.activeQuizzes,
    this.courses,
    this.announcements,
  });

  bool get hasData =>
      dashboardData != null &&
      todayLectures != null &&
      activeQuizzes != null;

  DashboardState copyWith({
    bool? isLoading,
    String? error,
    Dashboard? dashboardData,
    List<TodayLecture>? todayLectures,
    List<ActiveQuiz>? activeQuizzes,
    List<Course>? courses,
    List<Map<String, dynamic>>? announcements,
    bool clearError = false,
  }) {
    return DashboardState(
      isLoading:      isLoading      ?? this.isLoading,
      error:          clearError ? null : (error ?? this.error),
      dashboardData:  dashboardData  ?? this.dashboardData,
      todayLectures:  todayLectures  ?? this.todayLectures,
      activeQuizzes:  activeQuizzes  ?? this.activeQuizzes,
      courses:        courses        ?? this.courses,
      announcements:  announcements  ?? this.announcements,
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  DashboardNotifier — Fetches data from API
// ════════════════════════════════════════════════════════════════════

class DashboardNotifier extends StateNotifier<DashboardState> {
  final ApiService _api;

  DashboardNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const DashboardState());

  /// Sab data ek saath parallel fetch karo (Future.wait = faster)
  Future<void> fetchDashboard() async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      // ── Parallel API calls — ek saath chalte hain ───────────
      final results = await Future.wait([
        _api.getDashboard(),          // Call 1: overall stats
        _api.getTodayLectures(),      // Call 2: today's lectures
        _api.getActiveQuizzes(),      // Call 3: active quizzes
        _api.getCourses(),            // Call 4: enrolled courses
        _getNotificationsSafe(),      // Call 5: announcements
      ]);

      state = state.copyWith(
        isLoading:     false,
        dashboardData: results[0] as Dashboard,
        todayLectures: results[1] as List<TodayLecture>,
        activeQuizzes: results[2] as List<ActiveQuiz>,
        courses:       results[3] as List<Course>,
        announcements: results[4] as List<Map<String, dynamic>>,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _parseError(e),
      );
    }
  }

  Future<List<Map<String, dynamic>>> _getNotificationsSafe() async {
    try {
      return await _api.getMyNotifications();
    } catch (_) {
      return [];
    }
  }

  /// Pull-to-refresh
  Future<void> refresh() => fetchDashboard();

  void clearError() => state = state.copyWith(clearError: true);

  String _parseError(Object e) {
    final msg = e.toString();
    if (msg.startsWith('Exception: ')) return msg.replaceFirst('Exception: ', '');
    return 'Failed to load dashboard. Please retry.';
  }
}

// ════════════════════════════════════════════════════════════════════
//  Provider — Global access
// ════════════════════════════════════════════════════════════════════

final dashboardProvider =
    StateNotifierProvider<DashboardNotifier, DashboardState>(
  (ref) => DashboardNotifier(),
);
