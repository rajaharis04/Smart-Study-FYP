// ╔══════════════════════════════════════════════════════════════════╗
// ║         LECTURE PROVIDER — Phase 5 State Management              ║
// ║  All data from real database — no dummy values                   ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/constants.dart';
import '../models/models.dart';
import '../services/api_service.dart';

// ════════════════════════════════════════════════════════════════════
//  Chapter model (from backend DB)
// ════════════════════════════════════════════════════════════════════

class LectureChapterData {
  final int id;
  final String title;
  final int startSeconds;

  const LectureChapterData({
    required this.id,
    required this.title,
    required this.startSeconds,
  });

  factory LectureChapterData.fromJson(Map<String, dynamic> j) =>
      LectureChapterData(
        id:           j['id']             as int,
        title:        j['title']          as String,
        startSeconds: j['start_seconds']  as int,
      );

  Duration get startDuration => Duration(seconds: startSeconds);
}

// ════════════════════════════════════════════════════════════════════
//  Q&A Message
// ════════════════════════════════════════════════════════════════════

class QnaMessage {
  final String text;
  final bool isUser;
  final String? source;
  final DateTime timestamp;

  const QnaMessage({
    required this.text,
    required this.isUser,
    this.source,
    required this.timestamp,
  });
}

// ════════════════════════════════════════════════════════════════════
//  LectureState
// ════════════════════════════════════════════════════════════════════

class LectureState {
  final bool isLoading;
  final String? error;

  // Lecture data from DB
  final String? videoUrl;
  final int? courseId;
  final List<LectureChapterData> chapters;

  // Pre-quiz (from DB)
  final int? preQuizId;
  final List<QuizQuestion> preQuestions;
  final Map<int, String?> preAnswers;
  final bool preSubmitted;

  // Session tracking (row in lecture_sessions)
  final int? sessionId;
  final double watchPercentage;
  final int pauseCount;
  final double playbackSpeed;

  // Mid-check (from DB)
  final int? midQuizId;
  final List<QuizQuestion> midQuestions;
  final Map<int, String?> midAnswers;
  final bool midCheckDone;
  final bool showMidCheck;

  // Q&A chat history
  final List<QnaMessage> qnaMessages;
  final bool isAskingQuestion;

  const LectureState({
    this.isLoading = false,
    this.error,
    this.videoUrl,
    this.courseId,
    this.chapters = const [],
    this.preQuizId,
    this.preQuestions = const [],
    this.preAnswers = const {},
    this.preSubmitted = false,
    this.sessionId,
    this.watchPercentage = 0,
    this.pauseCount = 0,
    this.playbackSpeed = 1.0,
    this.midQuizId,
    this.midQuestions = const [],
    this.midAnswers = const {},
    this.midCheckDone = false,
    this.showMidCheck = false,
    this.qnaMessages = const [],
    this.isAskingQuestion = false,
  });

  LectureState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    String? videoUrl,
    int? courseId,
    List<LectureChapterData>? chapters,
    int? preQuizId,
    List<QuizQuestion>? preQuestions,
    Map<int, String?>? preAnswers,
    bool? preSubmitted,
    int? sessionId,
    double? watchPercentage,
    int? pauseCount,
    double? playbackSpeed,
    int? midQuizId,
    List<QuizQuestion>? midQuestions,
    Map<int, String?>? midAnswers,
    bool? midCheckDone,
    bool? showMidCheck,
    List<QnaMessage>? qnaMessages,
    bool? isAskingQuestion,
  }) {
    return LectureState(
      isLoading:        isLoading        ?? this.isLoading,
      error:            clearError ? null : (error ?? this.error),
      videoUrl:         videoUrl         ?? this.videoUrl,
      courseId:         courseId         ?? this.courseId,
      chapters:         chapters         ?? this.chapters,
      preQuizId:        preQuizId        ?? this.preQuizId,
      preQuestions:     preQuestions     ?? this.preQuestions,
      preAnswers:       preAnswers       ?? this.preAnswers,
      preSubmitted:     preSubmitted     ?? this.preSubmitted,
      sessionId:        sessionId        ?? this.sessionId,
      watchPercentage:  watchPercentage  ?? this.watchPercentage,
      pauseCount:       pauseCount       ?? this.pauseCount,
      playbackSpeed:    playbackSpeed    ?? this.playbackSpeed,
      midQuizId:        midQuizId        ?? this.midQuizId,
      midQuestions:     midQuestions     ?? this.midQuestions,
      midAnswers:       midAnswers       ?? this.midAnswers,
      midCheckDone:     midCheckDone     ?? this.midCheckDone,
      showMidCheck:     showMidCheck     ?? this.showMidCheck,
      qnaMessages:      qnaMessages      ?? this.qnaMessages,
      isAskingQuestion: isAskingQuestion ?? this.isAskingQuestion,
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  LectureNotifier
// ════════════════════════════════════════════════════════════════════

class LectureNotifier extends StateNotifier<LectureState> {
  final ApiService _api;
  Timer? _trackingTimer;

  LectureNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const LectureState());

  void reset() {
    _trackingTimer?.cancel();
    _trackingTimer = null;
    state = const LectureState();
  }

  // ══════════════════════════════════════════════════════════════════
  //  LOAD LECTURE DETAIL (video URL + chapters from DB)
  // ══════════════════════════════════════════════════════════════════

  Future<void> loadLecture(int lectureId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final data = await _api.getLectureDetail(lectureId);
      final rawChapters = (data['chapters'] as List<dynamic>?) ?? [];
      final chapters = rawChapters
          .map((c) => LectureChapterData.fromJson(c as Map<String, dynamic>))
          .toList();
      
      String? videoUrl = data['video_url'] as String?;
      if (videoUrl != null && videoUrl.startsWith('/')) {
        final uri = Uri.parse(AppConstants.baseUrl);
        final host = '${uri.scheme}://${uri.host}:${uri.port}';
        videoUrl = '$host$videoUrl';
      }

      state = state.copyWith(
        isLoading: false,
        videoUrl:  videoUrl,
        courseId:  data['course_id'] as int?,
        chapters:  chapters,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _msg(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  PRE-QUIZ (fetched from DB, answers saved to DB)
  // ══════════════════════════════════════════════════════════════════

  Future<void> generatePreQuiz(int lectureId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _api.getQuiz(
          lectureId: lectureId, quizType: 'pre');
      state = state.copyWith(
        isLoading:    false,
        preQuizId:    result['quiz_id'] as int?,
        preQuestions: result['questions'] as List<QuizQuestion>,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _msg(e));
    }
  }

  void setPreAnswer(int questionId, String answer) {
    final updated = Map<int, String?>.from(state.preAnswers);
    updated[questionId] = answer;
    state = state.copyWith(preAnswers: updated);
  }

  Future<bool> submitPreQuiz() async {
    if (state.preQuizId == null) {
      state = state.copyWith(preSubmitted: true);
      return true;
    }
    state = state.copyWith(isLoading: true);
    try {
      await _api.submitQuiz(
        quizId:  state.preQuizId!,
        answers: state.preAnswers,
      );
      state = state.copyWith(isLoading: false, preSubmitted: true);
      return true;
    } catch (_) {
      // Pre-quiz submit failure is non-fatal
      state = state.copyWith(isLoading: false, preSubmitted: true);
      return true;
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  SESSION TRACKING (creates LectureSession row + 30s pings to DB)
  // ══════════════════════════════════════════════════════════════════

  Future<void> startSession(int lectureId) async {
    try {
      final result = await _api.startSession(lectureId);
      final sessionId = result['session_id'] as int?;
      state = state.copyWith(sessionId: sessionId);

      // Ping every 30 seconds — updates DB row
      _trackingTimer?.cancel();
      _trackingTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) => _pingSession(),
      );
    } catch (_) {
      // Non-fatal — video still plays
    }
  }

  void updateWatchState({
    required double watchPercentage,
    int? additionalPauses,
    double? playbackSpeed,
  }) {
    state = state.copyWith(
      watchPercentage: watchPercentage,
      pauseCount:      state.pauseCount + (additionalPauses ?? 0),
      playbackSpeed:   playbackSpeed ?? state.playbackSpeed,
    );
    if (watchPercentage >= 50 && !state.midCheckDone) {
      _triggerMidCheck();
    }
  }

  Future<void> _pingSession() async {
    if (state.sessionId == null) return;
    await _api.pingSession(
      sessionId:       state.sessionId!,
      watchPercentage: state.watchPercentage,
      pauseCount:      state.pauseCount,
      playbackSpeed:   state.playbackSpeed,
      foregroundRatio: 1.0, // App lifecycle tracking future enhancement
    );
  }

  Future<void> endSession() async {
    _trackingTimer?.cancel();
    _trackingTimer = null;
    if (state.sessionId == null) return;
    try {
      await _api.endSession(
        sessionId:    state.sessionId!,
        totalWatched: state.watchPercentage,
      );
    } catch (_) {}
  }

  // ══════════════════════════════════════════════════════════════════
  //  MID-CHECK (fetched from DB at 50% trigger)
  // ══════════════════════════════════════════════════════════════════

  void _triggerMidCheck() {
    state = state.copyWith(midCheckDone: true, showMidCheck: true);
    // Questions are fetched from DB in _loadMidQuiz below
    // lectureId must be passed — called via updateWatchState context
    // For now overlay shows with empty list → _buildEmpty handles it gracefully
  }

  Future<void> loadMidQuiz(int lectureId) async {
    try {
      final result = await _api.getQuiz(
          lectureId: lectureId, quizType: 'mid');
      state = state.copyWith(
        midQuizId:    result['quiz_id'] as int?,
        midQuestions: result['questions'] as List<QuizQuestion>,
      );
    } catch (_) {}
  }

  void setMidAnswer(int questionId, String answer) {
    final updated = Map<int, String?>.from(state.midAnswers);
    updated[questionId] = answer;
    state = state.copyWith(midAnswers: updated);
  }

  Future<void> submitMidQuiz() async {
    state = state.copyWith(showMidCheck: false);
    if (state.midQuizId == null) return;
    try {
      await _api.submitQuiz(
        quizId:  state.midQuizId!,
        answers: state.midAnswers,
      );
    } catch (_) {}
  }

  void dismissMidCheck() {
    state = state.copyWith(showMidCheck: false);
  }

  // ══════════════════════════════════════════════════════════════════
  //  Q&A (answers from RAG backend)
  // ══════════════════════════════════════════════════════════════════

  Future<void> askQuestion(String question, int courseId) async {
    final userMsg = QnaMessage(
      text:      question,
      isUser:    true,
      timestamp: DateTime.now(),
    );
    state = state.copyWith(
      qnaMessages:      [...state.qnaMessages, userMsg],
      isAskingQuestion: true,
    );
    try {
      final response = await _api.askQuestion(
          question: question, courseId: courseId);
      final assistantMsg = QnaMessage(
        text:      response.answer,
        isUser:    false,
        source:    response.sources.isNotEmpty ? response.sources.first : null,
        timestamp: DateTime.now(),
      );
      state = state.copyWith(
        qnaMessages:      [...state.qnaMessages, assistantMsg],
        isAskingQuestion: false,
      );
    } catch (e) {
      final errMsg = QnaMessage(
        text:      'Sorry, could not get an answer. Please try again.',
        isUser:    false,
        timestamp: DateTime.now(),
      );
      state = state.copyWith(
        qnaMessages:      [...state.qnaMessages, errMsg],
        isAskingQuestion: false,
      );
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  Engagement (real values from tracked state)
  // ══════════════════════════════════════════════════════════════════

  /// Engagement score computed from real tracked data (pauses, Q&A count).
  /// foreground_ratio is approximated as 1.0 until app lifecycle tracking added.
  double get engagementScore {
    const foregroundRatio = 1.0;
    final pauseScore = 1.0 / (1.0 + state.pauseCount);
    final qnaCount =
        state.qnaMessages.where((m) => m.isUser).length;
    final qnaScore = (qnaCount / 5.0).clamp(0.0, 1.0);
    return foregroundRatio * 0.40 + pauseScore * 0.30 + qnaScore * 0.30;
  }

  String _msg(Object e) {
    final s = e.toString();
    return s.startsWith('Exception: ') ? s.replaceFirst('Exception: ', '') : s;
  }

  @override
  void dispose() {
    _trackingTimer?.cancel();
    super.dispose();
  }
}

// ════════════════════════════════════════════════════════════════════
//  Provider
// ════════════════════════════════════════════════════════════════════

final lectureProvider =
    StateNotifierProvider<LectureNotifier, LectureState>(
  (ref) => LectureNotifier(),
);
