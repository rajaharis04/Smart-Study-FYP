import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class ProgressState {
  final bool isLoading;
  final String? error;
  final ProfileProgressResponse? progressData;

  const ProgressState({
    this.isLoading = false,
    this.error,
    this.progressData,
  });

  ProgressState copyWith({
    bool? isLoading,
    String? error,
    ProfileProgressResponse? progressData,
    bool clearError = false,
  }) {
    return ProgressState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      progressData: progressData ?? this.progressData,
    );
  }
}

class ProgressNotifier extends StateNotifier<ProgressState> {
  final ApiService _api;

  ProgressNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const ProgressState());

  Future<void> getProgress() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final data = await _api.getMyProgress();
      state = state.copyWith(isLoading: false, progressData: data);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString().replaceAll('Exception: ', ''));
    }
  }
}

final progressProvider = StateNotifierProvider<ProgressNotifier, ProgressState>(
  (ref) => ProgressNotifier(),
);
