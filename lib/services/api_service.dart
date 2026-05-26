// ╔══════════════════════════════════════════════════════════════════╗
// ║              API SERVICE — HTTP CLIENT                           ║
// ║  Flutter app aur FastAPI backend ke beech communication          ║
// ║  Dio library use karta hai (JavaScript ka axios jaisa)           ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:dio/dio.dart';
import '../core/constants.dart';
import '../models/models.dart';
import 'storage_service.dart';

// ════════════════════════════════════════════════════════════════════
//
//  CONCEPT: ApiService kaise kaam karta hai?
//
//  UI Button Press
//      ↓
//  Provider → ApiService.login(email, password)
//      ↓
//  Dio → HTTP POST request banta hai
//      ↓
//  Interceptor → Authorization header lagata hai (agar token hai)
//      ↓
//  FastAPI Backend → Response bhejta hai
//      ↓
//  Interceptor → Error check karta hai
//      ↓
//  Model.fromJson() → JSON → Dart Object
//      ↓
//  Provider → State update → UI rebuild
//
// ════════════════════════════════════════════════════════════════════

/// HTTP requests handle karta hai — backend se communication ka zariya.
///
/// Usage:
/// ```dart
///   final api = ApiService();
///   final response = await api.login('ali@school.edu', 'password123');
///   print(response.fullName); // "Ali Hassan"
/// ```
class ApiService {
  // ══════════════════════════════════════════════════════════════════
  //  PART A: Dio Instance Setup
  //  Yeh ek configured HTTP client hai
  // ══════════════════════════════════════════════════════════════════

  late final Dio _dio;                  // Late = baad mein initialize hoga
  final StorageService _storage;        // Token lene ke liye

  // ── Constructor — Dio setup karo ─────────────────────────────────
  ApiService({StorageService? storage})
      : _storage = storage ?? StorageService() {
    // ── Step 1: Dio ka base configuration ───────────────────────────
    _dio = Dio(
      BaseOptions(
        // Base URL — har request is se shuru hogi
        // 10.0.2.2 = Android emulator mein host machine ka localhost
        baseUrl: AppConstants.baseUrl,

        // Default headers — har request mein yeh headers jayenge
        headers: {
          'Content-Type': 'application/json',  // Hum JSON bhej rahe hain
          'Accept':       'application/json',  // JSON chahiye response mein
        },

        // Timeout settings — agar backend 10 sec mein connect na kare to error
        connectTimeout: Duration(seconds: AppConstants.connectTimeout),
        // Agar response 30 sec mein na aaye to error
        receiveTimeout: Duration(seconds: AppConstants.receiveTimeout),
      ),
    );

    // ── Step 2: Interceptor add karo ────────────────────────────────
    _dio.interceptors.add(_buildInterceptor());
  }

  // ══════════════════════════════════════════════════════════════════
  //  PART B: Interceptor
  //  Har request/response ke beech middleware
  // ══════════════════════════════════════════════════════════════════

  /// Interceptor banao — request aur response dono handle karo.
  ///
  /// Outgoing request:  Token attach karo (Authorization header)
  /// Incoming response: Success → data pass karo | Error → handle karo
  InterceptorsWrapper _buildInterceptor() {
    return InterceptorsWrapper(
      // ── onRequest — har request bhejne se PEHLE ──────────────────
      onRequest: (RequestOptions options, RequestInterceptorHandler handler) async {
        // Storage se token lo
        final token = await _storage.getToken();

        // Agar token mila to Authorization header mein lagao
        if (token != null) {
          // "Bearer eyJhbGciOiJIUzI1NiIs..." — yeh format chahiye
          options.headers['Authorization'] = 'Bearer $token';
        }

        // Request aage bhejo (next step)
        handler.next(options);
      },

      // ── onResponse — response aane par ───────────────────────────
      onResponse: (Response response, ResponseInterceptorHandler handler) {
        // Success response — aage pass karo (koi kaam nahi karna)
        handler.next(response);
      },

      // ── onError — koi error aaya ─────────────────────────────────
      onError: (DioException error, ErrorInterceptorHandler handler) async {
        // ── Case 1: 401 Unauthorized — Token expire ho gaya ────────
        if (error.response?.statusCode == 401) {
          // Token delete karo (logout effect)
          await _storage.deleteToken();
          // Custom error message ke saath reject karo
          handler.reject(
            DioException(
              requestOptions: error.requestOptions,
              error: 'Session expired. Please login again.',
              type: DioExceptionType.badResponse,
              response: error.response,
            ),
          );
          return;
        }

        // ── Case 2: Network error — internet nahi ──────────────────
        if (error.type == DioExceptionType.connectionError ||
            error.type == DioExceptionType.unknown) {
          handler.reject(
            DioException(
              requestOptions: error.requestOptions,
              error: 'No internet connection. Please check your network.',
              type: error.type,
            ),
          );
          return;
        }

        // ── Case 3: Timeout — backend slow hai ─────────────────────
        if (error.type == DioExceptionType.connectionTimeout ||
            error.type == DioExceptionType.receiveTimeout) {
          handler.reject(
            DioException(
              requestOptions: error.requestOptions,
              error: 'Connection timed out. Please try again.',
              type: error.type,
            ),
          );
          return;
        }

        // ── Default: Error aage pass karo ──────────────────────────
        handler.next(error);
      },
    );
  }

  // ══════════════════════════════════════════════════════════════════
  //  HELPER: Error message nikalna
  // ══════════════════════════════════════════════════════════════════

  /// DioException se user-friendly message extract karo.
  String _extractError(DioException e) {
    // Agar backend ne message bheja ho
    if (e.response?.data is Map) {
      final data = e.response!.data as Map;
      return data['detail']?.toString() ??
             data['message']?.toString() ??
             'Server error occurred.';
    }
    // Interceptor ne set kiya custom message
    return e.error?.toString() ?? 'Something went wrong.';
  }

  // ══════════════════════════════════════════════════════════════════
  //  AUTHENTICATION METHODS — Login / Password
  // ══════════════════════════════════════════════════════════════════

  // ── METHOD 1: sendOtp ──────────────────────────────────────────
  /// Backend se request karo OTP bhejne ke liye.
  Future<Map<String, dynamic>> sendOtp(String email) async {
    try {
      final response = await _dio.post(
        '/auth/send-otp',
        data: {'email': email},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ── METHOD 1.2: verifyOtp ──────────────────────────────────────
  /// User ka input kiya hua OTP check karo.
  Future<Map<String, dynamic>> verifyOtp(String email, String otp) async {
    try {
      final response = await _dio.post(
        '/auth/verify-otp',
        data: {
          'email': email,
          'otp': otp,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ── METHOD 1.3: setupPassword ──────────────────────────────────
  /// Verification complete hone par naya password store karo.
  Future<Map<String, dynamic>> setupPassword({
    required String email,
    required String otp,
    required String password,
  }) async {
    try {
      final response = await _dio.post(
        '/auth/setup-password',
        data: {
          'email': email,
          'otp': otp,
          'password': password,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ── METHOD 2: login ────────────────────────────────────────────
  /// Email aur password se login karo, JWT token wapas aata hai.
  ///
  /// [email]    — Student ka email
  /// [password] — Backend se mila ya user ka naya password
  ///
  /// Returns: [LoginResponse] — token, role, naam, mustChangePassword
  ///
  /// Kab use karo: Login button press karne par
  Future<LoginResponse> login(String email, String password) async {
    try {
      final response = await _dio.post(
        '/auth/login',
        data: {
          'email':    email,
          'password': password,
        },
      );
      // JSON → LoginResponse object
      return LoginResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ── METHOD 3: changePassword ───────────────────────────────────
  /// Pehle login par ya manually password change karo.
  ///
  /// [currentPassword] — Purana password
  /// [newPassword]     — Naya password jo set karna hai
  ///
  /// Kab use karo: Change Password screen par
  Future<Map<String, dynamic>> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      final response = await _dio.post(
        '/auth/change-password',
        data: {
          'current_password': currentPassword,
          'new_password':     newPassword,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  DASHBOARD METHODS — Stats & Overview
  // ══════════════════════════════════════════════════════════════════

  // ── METHOD 4: getDashboard ────────────────────────────────────
  /// Student ka overall progress aur stats lo.
  ///
  /// Returns: [Dashboard] — progress, courses, attendance, quizzes
  ///
  /// Kab use karo: Dashboard screen load hone par
  Future<Dashboard> getDashboard() async {
    try {
      final response = await _dio.get('/dashboard');
      return Dashboard.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ── METHOD 5: getTodayLectures ────────────────────────────────
  /// Aaj ki scheduled lectures ki list lo.
  ///
  /// Returns: List of [TodayLecture]
  ///
  /// Kab use karo: Dashboard mein "Today's Schedule" section
  Future<List<TodayLecture>> getTodayLectures() async {
    try {
      final response = await _dio.get('/dashboard/today-lectures');
      // Backend list bhejta hai — har item ko TodayLecture mein convert karo
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => TodayLecture.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ── METHOD 6: getActiveQuizzes ────────────────────────────────
  /// Abhi available quizzes ki list lo.
  ///
  /// Returns: List of [ActiveQuiz]
  ///
  /// Kab use karo: Dashboard mein "Active Quizzes" section
  Future<List<ActiveQuiz>> getActiveQuizzes() async {
    try {
      final response = await _dio.get('/dashboard/active-quizzes');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => ActiveQuiz.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  LECTURE SESSION METHODS — Watch Tracking
  // ══════════════════════════════════════════════════════════════════


  // ══════════════════════════════════════════════════════════════════
  //  BONUS: Lectures List
  // ══════════════════════════════════════════════════════════════════

  /// Courses ki lectures list lo.
  ///
  /// [courseId] — Kaunse course ki lectures chahiye
  ///
  /// Returns: List of [Lecture]
  Future<List<Lecture>> getLectures(int courseId) async {
    try {
      final response = await _dio.get(
        '/lectures/',
        queryParameters: {'course_id': courseId},
      );
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => Lecture.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Student ka profile lo.
  Future<Student> getStudentProfile() async {
    try {
      final response = await _dio.get('/students/me/');
      return Student.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Enrolled courses ki list lo.
  Future<List<Course>> getCourses() async {
    try {
      final response = await _dio.get('/courses');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => Course.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }
  // ══════════════════════════════════════════════════════════════════
  //  LECTURE DETAIL — video URL, chapters from real DB
  // ══════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> getLectureDetail(int lectureId) async {
    try {
      final response = await _dio.get('/lectures/$lectureId');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  SESSION TRACKING — stored in lecture_sessions table
  // ══════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> startSession(int lectureId) async {
    try {
      final response = await _dio.post('/lectures/$lectureId/session/start');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  Future<void> pingSession({
    required int sessionId,
    required double watchPercentage,
    required int pauseCount,
    required double playbackSpeed,
    double foregroundRatio = 1.0,
  }) async {
    try {
      await _dio.post('/lectures/session/$sessionId/ping', data: {
        'watch_percentage': watchPercentage,
        'pause_count':      pauseCount,
        'playback_speed':   playbackSpeed,
        'foreground_ratio': foregroundRatio,
      });
    } on DioException catch (_) {}
  }

  Future<Map<String, dynamic>> endSession({
    required int sessionId,
    required double totalWatched,
  }) async {
    try {
      final response = await _dio.post('/lectures/session/$sessionId/end', data: {
        'total_watched': totalWatched,
      });
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  QUIZ — fetch questions from DB, save answers to DB
  // ══════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> getQuiz({
    required int lectureId,
    required String quizType,
  }) async {
    try {
      final response = await _dio.get('/lectures/$lectureId/quiz/$quizType');
      final data = response.data as Map<String, dynamic>;
      final rawQ = (data['questions'] as List<dynamic>?) ?? [];
      return {
        'quiz_id': data['quiz_id'] as int?,
        'questions': rawQ
            .map((q) => QuizQuestion.fromJson(q as Map<String, dynamic>))
            .toList(),
      };
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  Future<void> submitQuiz({
    required int quizId,
    required Map<int, String?> answers,
  }) async {
    try {
      final items = answers.entries
          .map((e) => {'question_id': e.key, 'answer': e.value})
          .toList();
      await _dio.post('/lectures/quiz/$quizId/submit', data: {'answers': items});
    } on DioException catch (_) {}
  }

  // ══════════════════════════════════════════════════════════════════
  //  Q&A — RAG-powered answers (saved server-side in Q&A logs)
  // ══════════════════════════════════════════════════════════════════

  Future<QaResponse> askQuestion({
    required String question,
    required int courseId,
  }) async {
    try {
      final response = await _dio.post('/qa/ask', data: {
        'question':  question,
        'course_id': courseId,
      });
      return QaResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  PHASE 7 STUDENT PORTAL EXTENSIONS
  // ══════════════════════════════════════════════════════════════════

  /// Enrolled courses with credit hours and progress
  Future<List<Course>> getMyCourses() async {
    try {
      final response = await _dio.get('/courses/my');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => Course.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Student attendance summary and lecture log list
  Future<MyAttendanceResponse> getMyAttendance() async {
    try {
      final response = await _dio.get('/attendance/my');
      return MyAttendanceResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Student topic mastery and learning profiles progress
  Future<ProfileProgressResponse> getMyProgress() async {
    try {
      final response = await _dio.get('/profile/progress');
      return ProfileProgressResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Student wrong-answer history list (Question Bank)
  Future<List<QuestionBankItem>> getMyQuestionBank() async {
    try {
      final response = await _dio.get('/questionbank/my');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => QuestionBankItem.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Student re-attempt wrong question grading
  Future<Map<String, dynamic>> attemptQuestionAgain(int questionId, String answer) async {
    try {
      final response = await _dio.post('/questionbank/attempt', data: {
        'question_id': questionId,
        'answer': answer,
      });
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// List lectures for a section
  Future<List<Lecture>> getLecturesBySection(int sectionId) async {
    try {
      final response = await _dio.get('/lectures/section/$sectionId');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((item) => Lecture.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Download notes path
  Future<String> downloadNotes(int lectureId) async {
    // Return standard dummy pdf url for demo download
    return "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf";
  }

  /// Get notifications for logged-in student
  Future<List<Map<String, dynamic>>> getMyNotifications() async {
    try {
      final response = await _dio.get('/profile/notifications');
      final List<dynamic> data = response.data as List<dynamic>;
      return data.map((item) => Map<String, dynamic>.from(item as Map)).toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  /// Mark student notification as read
  Future<void> markNotificationAsRead(String id) async {
    try {
      await _dio.post('/profile/notifications/$id/read');
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }
}
