// ╔══════════════════════════════════════════════════════════════════╗
// ║              Q&A HISTORY SEARCH DELEGATE                         ║
// ║  Search overlay that queries all saved doubts and RAG citations.║
// ║  Supports instant filter and starring toggle.                   ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/qa_history_provider.dart';
import '../../providers/settings_provider.dart';

class QaSearchDelegate extends SearchDelegate {
  final WidgetRef ref;

  QaSearchDelegate({required this.ref});

  @override
  String get searchFieldLabel {
    final language = ref.read(settingsProvider).language;
    return language == 'Urdu' ? 'سوال تلاش کریں...' : 'Search doubts...';
  }

  @override
  ThemeData appBarTheme(BuildContext context) {
    final theme = Theme.of(context);
    return theme.copyWith(
      appBarTheme: theme.appBarTheme.copyWith(
        elevation: 0,
        backgroundColor: theme.colorScheme.surface,
      ),
      inputDecorationTheme: const InputDecorationTheme(
        border: InputBorder.none,
      ),
    );
  }

  @override
  List<Widget>? buildActions(BuildContext context) {
    return [
      if (query.isNotEmpty)
        IconButton(
          icon: const Icon(Icons.clear_rounded),
          onPressed: () {
            query = '';
            showSuggestions(context);
          },
        ),
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.arrow_back_rounded),
      onPressed: () {
        close(context, null);
      },
    );
  }

  @override
  Widget buildResults(BuildContext context) {
    return _buildSearchResults(context);
  }

  @override
  Widget buildSuggestions(BuildContext context) {
    return _buildSearchResults(context);
  }

  Widget _buildSearchResults(BuildContext context) {
    final state = ref.watch(qaHistoryProvider);
    final theme = Theme.of(context);
    final isUrdu = ref.watch(settingsProvider).language == 'Urdu';

    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    final allHistory = state.bookmarks;
    final filtered = allHistory.where((item) {
      final q = (item['question'] as String? ?? '').toLowerCase();
      final a = (item['answer'] as String? ?? '').toLowerCase();
      final term = query.toLowerCase();
      return q.contains(term) || a.contains(term);
    }).toList();

    if (filtered.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.search_off_rounded,
                size: 64,
                color: theme.colorScheme.primary.withOpacity(0.2),
              ),
              const SizedBox(height: 16),
              Text(
                isUrdu ? 'کوئی نتائج نہیں ملے' : 'No matches found',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                isUrdu
                    ? 'آپ کے تلاش کردہ لفظ کے مطابق کوئی سوال نہیں ملا۔'
                    : 'Try checking spelling or bookmark more AI questions.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12.5,
                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: filtered.length,
        itemBuilder: (context, index) {
          final item = filtered[index];
          final question = item['question'] as String? ?? '';
          final answer = item['answer'] as String? ?? '';
          final source = item['source'] as String?;

          return Card(
            margin: const EdgeInsets.only(bottom: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            elevation: 0,
            color: theme.colorScheme.surface,
            borderOnForeground: false,
            child: ExpansionTile(
              initiallyExpanded: query.isNotEmpty,
              shape: Border.all(color: theme.colorScheme.outline.withOpacity(0.08)),
              collapsedShape: Border.all(color: theme.colorScheme.outline.withOpacity(0.08)),
              leading: Icon(Icons.psychology_rounded, color: theme.colorScheme.primary),
              title: Text(
                question,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
              ),
              trailing: IconButton(
                icon: const Icon(Icons.star_rounded, color: Colors.amber),
                onPressed: () async {
                  await ref.read(qaHistoryProvider.notifier).toggleBookmark(item);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(isUrdu ? 'بک مارک ہٹا دیا گیا' : 'Bookmark removed successfully'),
                      duration: const Duration(seconds: 1),
                    ),
                  );
                },
              ),
              childrenPadding: const EdgeInsets.all(16),
              children: [
                Align(
                  alignment: isUrdu ? Alignment.centerRight : Alignment.centerLeft,
                  child: Text(
                    answer,
                    style: TextStyle(
                      fontSize: 13,
                      height: 1.45,
                      color: theme.colorScheme.onSurfaceVariant.withOpacity(0.9),
                    ),
                  ),
                ),
                if (source != null && source.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Align(
                    alignment: isUrdu ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00BFA5).withOpacity(0.08),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.link_rounded, size: 12, color: Color(0xFF00BFA5)),
                          const SizedBox(width: 4),
                          Text(
                            'Source: $source',
                            style: const TextStyle(
                              fontSize: 10.5,
                              color: Color(0xFF00BFA5),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}
