// ╔══════════════════════════════════════════════════════════════════╗
// ║              LEARNING PROVIDER                                    ║
// ║  BKT-powered Student Learning Profile state management            ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';

// ── Learning Profile State ───────────────────────────────────────────────────

class LearningProfileState {
  final bool isLoading;
  final String? error;
  final LearningProfile? profile;

  const LearningProfileState({
    this.isLoading = false,
    this.error,
    this.profile,
  });

  LearningProfileState copyWith({
    bool? isLoading,
    String? error,
    LearningProfile? profile,
    bool clearError = false,
  }) {
    return LearningProfileState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      profile: profile ?? this.profile,
    );
  }
}

class LearningProfileNotifier extends StateNotifier<LearningProfileState> {
  final ApiService _api;

  LearningProfileNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const LearningProfileState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final data = await _api.getLearningProfile();
      state = state.copyWith(isLoading: false, profile: data);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  void refresh() => load();
}

final learningProfileProvider =
    StateNotifierProvider<LearningProfileNotifier, LearningProfileState>(
  (ref) => LearningProfileNotifier(),
);

// ── Post-Quiz Feedback State ─────────────────────────────────────────────────

class PostQuizFeedbackState {
  final bool isLoading;
  final String? error;
  final PostQuizFeedback? feedback;

  const PostQuizFeedbackState({
    this.isLoading = false,
    this.error,
    this.feedback,
  });

  PostQuizFeedbackState copyWith({
    bool? isLoading,
    String? error,
    PostQuizFeedback? feedback,
    bool clearFeedback = false,
    bool clearError = false,
  }) {
    return PostQuizFeedbackState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      feedback: clearFeedback ? null : (feedback ?? this.feedback),
    );
  }
}

class PostQuizFeedbackNotifier extends StateNotifier<PostQuizFeedbackState> {
  final ApiService _api;

  PostQuizFeedbackNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const PostQuizFeedbackState());

  Future<void> loadFeedback(int quizId) async {
    state = state.copyWith(isLoading: true, clearError: true, clearFeedback: true);
    try {
      // Small delay to allow background BKT recalculation to complete
      await Future.delayed(const Duration(milliseconds: 600));
      final data = await _api.getPostQuizFeedback(quizId);
      state = state.copyWith(isLoading: false, feedback: data);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  void clear() {
    state = const PostQuizFeedbackState();
  }
}

final postQuizFeedbackProvider =
    StateNotifierProvider<PostQuizFeedbackNotifier, PostQuizFeedbackState>(
  (ref) => PostQuizFeedbackNotifier(),
);
