// ╔══════════════════════════════════════════════════════════════════╗
// ║              APP ROUTER — GoRouter Configuration                 ║
// ║  ShellRoute (bottom nav) + Auth Guard + all routes               ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'constants.dart';
import '../services/storage_service.dart';

// ── Auth screens ──────────────────────────────────────────────────────────
import '../screens/auth/splash_screen.dart';
import '../screens/auth/onboarding_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/change_password_screen.dart';

// ── Dashboard tabs ────────────────────────────────────────────────────────
import '../screens/dashboard/dashboard_shell.dart';
import '../screens/dashboard/dashboard_home_screen.dart';
import '../screens/courses/courses_screen.dart';
import '../screens/courses/course_lectures_screen.dart';
import '../screens/attendance/attendance_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/profile/notification_center_screen.dart';

// ── Other screens ─────────────────────────────────────────────────────────
import '../screens/lecture/pre_assessment_screen.dart';
import '../screens/lecture/lecture_player_screen.dart';

// ════════════════════════════════════════════════════════════════════
//  Auth Notifier — GoRouter ko batata hai jab auth state change ho
//  Yeh ChangeNotifier GoRouter ke refreshListenable se connected hai
// ════════════════════════════════════════════════════════════════════

/// GoRouter refreshListenable — Auth state change par router rebuild karta hai.
///
/// IMPORTANT: Sirf login/logout par use karo, navigation par nahi.
/// Async guard ki jagah synchronous check use karte hain.
class AppAuthNotifier extends ChangeNotifier {
  // ── Singleton ────────────────────────────────────────────────────
  static final AppAuthNotifier instance = AppAuthNotifier._();
  AppAuthNotifier._();

  // ── Internal state ───────────────────────────────────────────────
  bool _isLoggedIn = false;

  /// Kya user logged in hai?
  bool get isLoggedIn => _isLoggedIn;

  /// Login ke baad call karo — router rebuild hoga
  void setLoggedIn(bool value) {
    if (_isLoggedIn == value) return;
    _isLoggedIn = value;
    notifyListeners(); // GoRouter rebuild trigger hoga
  }
}

// ════════════════════════════════════════════════════════════════════
//  Auth Guard — SYNCHRONOUS (async nahi)
//  GoRouter 13.x mein async redirect navigation cancel kar sakta hai
//  Isliye in-memory token check use karte hain
// ════════════════════════════════════════════════════════════════════

/// Public routes — auth check nahi karna
const _publicPaths = [
  AppConstants.routeSplash,
  AppConstants.routeOnboarding,
  AppConstants.routeLogin,
];

/// Synchronous redirect — har navigation par token in-memory se check karo.
///
/// WHY SYNCHRONOUS? GoRouter 13.x mein `Future<String?> redirect` (async)
/// har navigation ke sath await karta hai. Agar async delay ho, navigation
/// cancel ho sakta hai — especially macOS desktop par.
///
/// SOLUTION: StorageService._fallbackStorage (static in-memory Map) se
/// synchronously token check karo — no await, no cancellation.
String? _authGuardSync(BuildContext context, GoRouterState state) {
  final path = state.matchedLocation;

  // Public routes — always allow karo
  if (_publicPaths.any((p) => p == '/' ? path == '/' : path.startsWith(p))) {
    return null;
  }

  // In-memory token check — synchronous, no await
  final token = StorageService.fallbackToken;
  if (token == null || token.isEmpty) {
    // Token nahi — login par bhejo
    return AppConstants.routeLogin;
  }

  // Token hai — route accessible
  return null;
}

// ════════════════════════════════════════════════════════════════════
//  Error screen
// ════════════════════════════════════════════════════════════════════

class _ErrorScreen extends StatelessWidget {
  final Exception? error;
  const _ErrorScreen({this.error});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Page Not Found')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Page not found',
                style: Theme.of(context).textTheme.titleMedium),
            if (error != null) ...[
              const SizedBox(height: 8),
              Text(error.toString(),
                  style: Theme.of(context).textTheme.bodySmall,
                  textAlign: TextAlign.center),
            ],
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(AppConstants.routeSplash),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  App Router — Single source of truth for all navigation
// ════════════════════════════════════════════════════════════════════

final GoRouter appRouter = GoRouter(
  initialLocation: AppConstants.routeSplash,

  // ── SYNCHRONOUS redirect ─────────────────────────────────────────
  // IMPORTANT: Async redirect (Future<String?>) use nahi kiya
  // kyunki GoRouter 13.x mein async redirect har navigation cancel
  // kar sakta hai, especially macOS desktop par.
  redirect: _authGuardSync,

  // ── Rebuild router jab auth state change ho ──────────────────────
  refreshListenable: AppAuthNotifier.instance,

  errorBuilder: (context, state) => _ErrorScreen(error: state.error),

  routes: [
    // ── Splash ────────────────────────────────────────────────────────
    GoRoute(
      path: AppConstants.routeSplash,
      name: 'splash',
      builder: (context, state) => const SplashScreen(),
    ),

    // ── Onboarding ────────────────────────────────────────────────────
    GoRoute(
      path: AppConstants.routeOnboarding,
      name: 'onboarding',
      builder: (context, state) => const OnboardingScreen(),
    ),

    // ── Login ─────────────────────────────────────────────────────────
    GoRoute(
      path: AppConstants.routeLogin,
      name: 'login',
      builder: (context, state) => const LoginScreen(),
    ),

    // ── Change Password ───────────────────────────────────────────────
    GoRoute(
      path: AppConstants.routeChangePassword,
      name: 'change-password',
      builder: (context, state) => const ChangePasswordScreen(),
    ),

    // ── Pre-Assessment (before lecture) ───────────────────────────────
    GoRoute(
      path: '${AppConstants.routePreAssessment}/:lectureId',
      name: 'pre-assessment',
      builder: (context, state) {
        final id = state.pathParameters['lectureId'] ?? '0';
        return PreAssessmentScreen(lectureId: id);
      },
    ),

    // ── Lecture Player ────────────────────────────────────────────────
    GoRoute(
      path: '${AppConstants.routeLecturePlayer}/:lectureId',
      name: 'lecture-player',
      builder: (context, state) {
        final id = state.pathParameters['lectureId'] ?? '0';
        return LecturePlayerScreen(lectureId: id);
      },
    ),

    // ── Lecture (old route → redirect to pre-assessment) ─────────────
    GoRoute(
      path: '${AppConstants.routeLecture}/:lectureId',
      name: 'lecture',
      redirect: (context, state) {
        final id = state.pathParameters['lectureId'] ?? '0';
        return '${AppConstants.routePreAssessment}/$id';
      },
    ),

    // ── Dashboard — ShellRoute with BottomNavBar ──────────────────────
    // ShellRoute: persistent bottom nav — child screens swap inside
    ShellRoute(
      builder: (context, state, child) =>
          DashboardShell(child: child),

      routes: [
        // Tab 1: Home
        GoRoute(
          path: AppConstants.routeDashboardHome,
          name: 'dashboard-home',
          builder: (context, state) => const DashboardHomeScreen(),
        ),

        // Tab 2: Courses
        GoRoute(
          path: AppConstants.routeDashboardCourses,
          name: 'dashboard-courses',
          builder: (context, state) => const CoursesScreen(),
          routes: [
            GoRoute(
              path: 'lectures/:sectionId',
              name: 'course-lectures',
              builder: (context, state) {
                final sectionId = int.tryParse(
                        state.pathParameters['sectionId'] ?? '0') ??
                    0;
                final courseName =
                    state.uri.queryParameters['courseName'] ??
                        'Lectures';
                return CourseLecturesScreen(
                    sectionId: sectionId, courseName: courseName);
              },
            ),
          ],
        ),

        // Tab 3: Attendance
        GoRoute(
          path: AppConstants.routeDashboardAttendance,
          name: 'dashboard-attendance',
          builder: (context, state) => const AttendanceScreen(),
        ),

        // Tab 4: Profile
        GoRoute(
          path: AppConstants.routeDashboardProfile,
          name: 'dashboard-profile',
          builder: (context, state) => const ProfileScreen(),
          routes: [
            GoRoute(
              path: 'notifications',
              name: 'notification-center',
              builder: (context, state) =>
                  const NotificationCenterScreen(),
            ),
          ],
        ),
      ],
    ),

    // ── /dashboard redirect ──────────────────────────────────────────
    GoRoute(
      path: AppConstants.routeDashboard,
      redirect: (context, state) => AppConstants.routeDashboardHome,
    ),
  ],
);
