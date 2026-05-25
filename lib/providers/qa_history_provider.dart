// ╔══════════════════════════════════════════════════════════════════╗
// ║              Q&A HISTORY PROVIDER                                ║
// ║  Manages state, loading, and deletion of bookmarked AI Q&As       ║
// ║  stored locally in secure/fallback storage.                      ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/storage_service.dart';

class QaHistoryState {
  final List<Map<String, dynamic>> bookmarks;
  final bool isLoading;

  const QaHistoryState({
    this.bookmarks = const [],
    this.isLoading = false,
  });

  QaHistoryState copyWith({
    List<Map<String, dynamic>>? bookmarks,
    bool? isLoading,
  }) {
    return QaHistoryState(
      bookmarks: bookmarks ?? this.bookmarks,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class QaHistoryNotifier extends StateNotifier<QaHistoryState> {
  final StorageService _storage = StorageService();

  QaHistoryNotifier() : super(const QaHistoryState()) {
    loadBookmarks();
  }

  Future<void> loadBookmarks() async {
    state = state.copyWith(isLoading: true);
    final list = await _storage.getBookmarkedQnAs();
    state = state.copyWith(bookmarks: list, isLoading: false);
  }

  Future<void> toggleBookmark(Map<String, dynamic> qnaMap) async {
    await _storage.toggleQnABookmark(qnaMap);
    await loadBookmarks();
  }
}

final qaHistoryProvider = StateNotifierProvider<QaHistoryNotifier, QaHistoryState>((ref) {
  return QaHistoryNotifier();
});
