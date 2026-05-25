import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class QuestionBankState {
  final bool isLoading;
  final String? error;
  final List<QuestionBankItem> wrongQuestions;
  final bool isSubmitting;
  final String? submitError;

  const QuestionBankState({
    this.isLoading = false,
    this.error,
    this.wrongQuestions = const [],
    this.isSubmitting = false,
    this.submitError,
  });

  QuestionBankState copyWith({
    bool? isLoading,
    String? error,
    List<QuestionBankItem>? wrongQuestions,
    bool? isSubmitting,
    String? submitError,
    bool clearError = false,
    bool clearSubmitError = false,
  }) {
    return QuestionBankState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      wrongQuestions: wrongQuestions ?? this.wrongQuestions,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      submitError: clearSubmitError ? null : (submitError ?? this.submitError),
    );
  }
}

class QuestionBankNotifier extends StateNotifier<QuestionBankState> {
  final ApiService _api;

  QuestionBankNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const QuestionBankState());

  Future<void> getQuestionBank() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final list = await _api.getMyQuestionBank();
      state = state.copyWith(isLoading: false, wrongQuestions: list);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString().replaceAll('Exception: ', ''));
    }
  }

  Future<bool> attemptQuestionAgain(int questionId, String answer) async {
    state = state.copyWith(isSubmitting: true, clearSubmitError: true);
    try {
      final result = await _api.attemptQuestionAgain(questionId, answer);
      final isCorrect = result['correct'] as bool? ?? false;
      
      state = state.copyWith(isSubmitting: false);
      
      // If correct, remove it from the local list
      if (isCorrect) {
        final updatedList = state.wrongQuestions.where((q) => q.id != questionId).toList();
        state = state.copyWith(wrongQuestions: updatedList);
      }
      return isCorrect;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, submitError: e.toString().replaceAll('Exception: ', ''));
      rethrow;
    }
  }
}

final questionBankProvider = StateNotifierProvider<QuestionBankNotifier, QuestionBankState>(
  (ref) => QuestionBankNotifier(),
);
