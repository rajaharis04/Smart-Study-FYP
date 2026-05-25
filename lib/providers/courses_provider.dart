import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

class CoursesState {
  final bool isLoading;
  final String? error;
  final List<Course> courses;
  final List<Lecture> courseLectures;
  final bool isLecturesLoading;
  final String? lecturesError;

  const CoursesState({
    this.isLoading = false,
    this.error,
    this.courses = const [],
    this.courseLectures = const [],
    this.isLecturesLoading = false,
    this.lecturesError,
  });

  CoursesState copyWith({
    bool? isLoading,
    String? error,
    List<Course>? courses,
    List<Lecture>? courseLectures,
    bool? isLecturesLoading,
    String? lecturesError,
    bool clearError = false,
    bool clearLecturesError = false,
  }) {
    return CoursesState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      courses: courses ?? this.courses,
      courseLectures: courseLectures ?? this.courseLectures,
      isLecturesLoading: isLecturesLoading ?? this.isLecturesLoading,
      lecturesError: clearLecturesError ? null : (lecturesError ?? this.lecturesError),
    );
  }
}

class CoursesNotifier extends StateNotifier<CoursesState> {
  final ApiService _api;
  final StorageService _storage;

  CoursesNotifier({ApiService? api, StorageService? storage})
      : _api = api ?? ApiService(),
        _storage = storage ?? StorageService(),
        super(const CoursesState());

  Future<void> getMyCourses() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final list = await _api.getMyCourses();
      state = state.copyWith(isLoading: false, courses: list);
      
      // Save courses to local cache
      final raw = list.map((c) => c.toJson()).toList();
      await _storage.write('cached_courses', json.encode(raw));
    } catch (e) {
      try {
        final cachedRaw = await _storage.read('cached_courses');
        if (cachedRaw != null) {
          final List<dynamic> decoded = json.decode(cachedRaw);
          final list = decoded.map((c) => Course.fromJson(c as Map<String, dynamic>)).toList();
          state = state.copyWith(
            isLoading: false,
            courses: list,
            error: 'Offline Mode (Cached Data)',
          );
          return;
        }
      } catch (_) {}
      
      state = state.copyWith(isLoading: false, error: e.toString().replaceAll('Exception: ', ''));
    }
  }

  Future<void> getCourseLectures(int sectionId) async {
    state = state.copyWith(isLecturesLoading: true, clearLecturesError: true);
    try {
      final list = await _api.getLecturesBySection(sectionId);
      state = state.copyWith(isLecturesLoading: false, courseLectures: list);
    } catch (e) {
      state = state.copyWith(isLecturesLoading: false, lecturesError: e.toString().replaceAll('Exception: ', ''));
    }
  }

  Future<String> downloadNotes(int lectureId) async {
    try {
      return await _api.downloadNotes(lectureId);
    } catch (e) {
      throw Exception(e.toString().replaceAll('Exception: ', ''));
    }
  }
}

final coursesProvider = StateNotifierProvider<CoursesNotifier, CoursesState>(
  (ref) => CoursesNotifier(),
);
