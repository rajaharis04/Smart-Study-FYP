import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

/// App-wide constants for SmartStudyInstructor.
///
/// Usage:
/// ```dart
/// final url = AppConstants.baseUrl;
/// ```
class AppConstants {
  AppConstants._();

  /// Base URL for all API requests.
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8001/api';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8001/api';
    }
    return 'http://localhost:8001/api';
  }

  /// Human-readable application name.
  static const String appName = 'SmartStudy';

  /// Maximum time (in seconds) to wait while establishing a connection.
  static const int connectTimeout = 10;

  /// Maximum time (in seconds) to wait for a full response to be received.
  static const int receiveTimeout = 30;

  // ── Route paths (for GoRouter) ────────────────────────────────────────────

  // Auth routes (public)
  static const String routeSplash          = '/';
  static const String routeOnboarding      = '/onboarding';
  static const String routeLogin           = '/login';
  static const String routeChangePassword  = '/change-password';

  // Dashboard parent route
  static const String routeDashboard           = '/dashboard';

  // Dashboard tab sub-routes
  static const String routeDashboardHome       = '/dashboard/home';
  static const String routeDashboardCourses    = '/dashboard/courses';
  static const String routeDashboardAttendance = '/dashboard/attendance';
  static const String routeDashboardProfile    = '/dashboard/profile';
  static const String routeCourseRegistration   = '/dashboard/courses/registration';

  // Lecture player pipeline
  static const String routeLecture             = '/lecture';
  static const String routePreAssessment       = '/lecture-pre';
  static const String routeLecturePlayer       = '/lecture-player';

  // ── Secure storage keys ───────────────────────────────────────────────────
  static const String keyAuthToken    = 'auth_token';
  static const String keyRefreshToken = 'refresh_token';
  static const String keyUserId       = 'user_id';
}
