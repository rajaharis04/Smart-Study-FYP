import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class AttendanceState {
  final bool isLoading;
  final String? error;
  final MyAttendanceResponse? attendanceData;

  const AttendanceState({
    this.isLoading = false,
    this.error,
    this.attendanceData,
  });

  AttendanceState copyWith({
    bool? isLoading,
    String? error,
    MyAttendanceResponse? attendanceData,
    bool clearError = false,
  }) {
    return AttendanceState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      attendanceData: attendanceData ?? this.attendanceData,
    );
  }
}

class AttendanceNotifier extends StateNotifier<AttendanceState> {
  final ApiService _api;

  AttendanceNotifier({ApiService? api})
      : _api = api ?? ApiService(),
        super(const AttendanceState());

  Future<void> getAttendance() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final data = await _api.getMyAttendance();
      state = state.copyWith(isLoading: false, attendanceData: data);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString().replaceAll('Exception: ', ''));
    }
  }
}

final attendanceProvider = StateNotifierProvider<AttendanceNotifier, AttendanceState>(
  (ref) => AttendanceNotifier(),
);
