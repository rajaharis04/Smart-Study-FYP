// ╔══════════════════════════════════════════════════════════════════╗
// ║         Q&A OVERLAY — Phase 5 Chat Interface                     ║
// ║  RAG-powered answers with citations, persistent chat history     ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/lecture_provider.dart';
import '../../services/storage_service.dart';

class QnaOverlay extends ConsumerStatefulWidget {
  final int courseId;
  final VoidCallback onClose;

  const QnaOverlay({
    super.key,
    required this.courseId,
    required this.onClose,
  });

  @override
  ConsumerState<QnaOverlay> createState() => _QnaOverlayState();
}

class _QnaOverlayState extends ConsumerState<QnaOverlay>
    with SingleTickerProviderStateMixin {
  final TextEditingController _textCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  late AnimationController _slideCtrl;
  late Animation<Offset> _slideAnim;
  Set<String> _bookmarkedQuestions = {};

  @override
  void initState() {
    super.initState();
    _loadBookmarks();
    _slideCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideCtrl, curve: Curves.easeOutCubic));
    _slideCtrl.forward();
  }

  Future<void> _loadBookmarks() async {
    final bookmarks = await StorageService().getBookmarkedQnAs();
    if (mounted) {
      setState(() {
        _bookmarkedQuestions = bookmarks.map((b) => b['question'] as String).toSet();
      });
    }
  }

  @override
  void dispose() {
    _textCtrl.dispose();
    _scrollCtrl.dispose();
    _slideCtrl.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendQuestion() async {
    final question = _textCtrl.text.trim();
    if (question.isEmpty) return;

    _textCtrl.clear();
    await ref
        .read(lectureProvider.notifier)
        .askQuestion(question, widget.courseId);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final lectureState = ref.watch(lectureProvider);
    final messages = lectureState.qnaMessages;
    final isLoading = lectureState.isAskingQuestion;

    // Scroll to bottom when new messages arrive
    if (messages.isNotEmpty) _scrollToBottom();

    return SlideTransition(
      position: _slideAnim,
      child: Container(
        height: MediaQuery.of(context).size.height * 0.65,
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 30,
              offset: const Offset(0, -8),
            ),
          ],
        ),
        child: Column(
          children: [
            // ── Handle ──────────────────────────────────────────────
            const SizedBox(height: 12),
            Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: theme.colorScheme.onSurface.withOpacity(0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),

            // ── Header ──────────────────────────────────────────────
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      Icons.smart_toy_rounded,
                      color: theme.colorScheme.primary,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Q&A Assistant',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: theme.colorScheme.onSurface,
                        ),
                      ),
                      Text(
                        'Powered by RAG • Ask anything',
                        style: TextStyle(
                          fontSize: 11,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: widget.onClose,
                    icon: const Icon(Icons.close_rounded),
                    style: IconButton.styleFrom(
                      backgroundColor:
                          theme.colorScheme.onSurface.withOpacity(0.06),
                    ),
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // ── Messages ────────────────────────────────────────────
            Expanded(
              child: messages.isEmpty
                  ? _buildEmptyState(theme)
                  : ListView.builder(
                      controller: _scrollCtrl,
                      padding: const EdgeInsets.all(16),
                      itemCount: messages.length,
                      itemBuilder: (ctx, i) =>
                          _buildMessage(theme, messages[i], i, messages),
                    ),
            ),

            // ── Typing indicator ─────────────────────────────────────
            if (isLoading) _buildTypingIndicator(theme),

            // ── Input area ──────────────────────────────────────────
            _buildInputArea(theme, isLoading),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.chat_bubble_outline_rounded,
            size: 52,
            color: theme.colorScheme.primary.withOpacity(0.3),
          ),
          const SizedBox(height: 12),
          Text(
            'Ask anything about this lecture',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Answers are based on your course content',
            style: TextStyle(
              fontSize: 12,
              color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 20),
          // Suggestion chips
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              'Explain this concept',
              'Give me an example',
              'Summarize so far',
            ]
                .map((s) => GestureDetector(
                      onTap: () {
                        _textCtrl.text = s;
                        _sendQuestion();
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color:
                                theme.colorScheme.primary.withOpacity(0.2),
                          ),
                        ),
                        child: Text(
                          s,
                          style: TextStyle(
                            fontSize: 13,
                            color: theme.colorScheme.primary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildMessage(ThemeData theme, QnaMessage message, int index, List<QnaMessage> messages) {
    final isUser = message.isUser;
    final timeStr =
        '${message.timestamp.hour.toString().padLeft(2, '0')}:${message.timestamp.minute.toString().padLeft(2, '0')}';

    final bool isBookmarked = !isUser && index > 0 && messages[index - 1].isUser && _bookmarkedQuestions.contains(messages[index - 1].text);

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment:
                isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isUser) ...[
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.smart_toy_rounded,
                    size: 16,
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: isUser
                        ? theme.colorScheme.primary
                        : theme.colorScheme.surface,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(18),
                      topRight: const Radius.circular(18),
                      bottomLeft: Radius.circular(isUser ? 18 : 4),
                      bottomRight: Radius.circular(isUser ? 4 : 18),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.06),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                    border: isUser
                        ? null
                        : Border.all(
                            color: theme.colorScheme.outline.withOpacity(0.15),
                          ),
                  ),
                  child: Text(
                    message.text,
                    style: TextStyle(
                      fontSize: 14,
                      color:
                          isUser ? Colors.white : theme.colorScheme.onSurface,
                      height: 1.45,
                    ),
                  ),
                ),
              ),
              if (isUser) const SizedBox(width: 8),
              if (!isUser && index > 0 && messages[index - 1].isUser) ...[
                const SizedBox(width: 4),
                IconButton(
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  icon: Icon(
                    isBookmarked ? Icons.star_rounded : Icons.star_outline_rounded,
                    color: isBookmarked ? Colors.amber : Colors.grey,
                    size: 20,
                  ),
                  onPressed: () async {
                    final questionText = messages[index - 1].text;
                    final qnaMap = {
                      'question': questionText,
                      'answer': message.text,
                      'timestamp': message.timestamp.toIso8601String(),
                      'source': message.source,
                    };
                    await StorageService().toggleQnABookmark(qnaMap);
                    setState(() {
                      if (isBookmarked) {
                        _bookmarkedQuestions.remove(questionText);
                      } else {
                        _bookmarkedQuestions.add(questionText);
                      }
                    });
                  },
                ),
              ],
            ],
          ),
          // Citation source
          if (!isUser && message.source != null) ...[
            const SizedBox(height: 4),
            Padding(
              padding: const EdgeInsets.only(left: 40),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF00BFA5).withOpacity(0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.link_rounded,
                        size: 12, color: Color(0xFF00BFA5)),
                    const SizedBox(width: 4),
                    Text(
                      'Source: ${message.source}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF00BFA5),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 3),
          Padding(
            padding: EdgeInsets.only(left: isUser ? 0 : 40),
            child: Text(
              timeStr,
              style: TextStyle(
                fontSize: 10,
                color: theme.colorScheme.onSurfaceVariant.withOpacity(0.5),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypingIndicator(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.only(left: 20, bottom: 4),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: theme.colorScheme.primary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.smart_toy_rounded,
                size: 16, color: theme.colorScheme.primary),
          ),
          const SizedBox(width: 10),
          _TypingDots(color: theme.colorScheme.primary),
        ],
      ),
    );
  }

  Widget _buildInputArea(ThemeData theme, bool isLoading) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outline.withOpacity(0.12),
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textCtrl,
              enabled: !isLoading,
              onSubmitted: (_) => _sendQuestion(),
              decoration: InputDecoration(
                hintText: 'Type your question...',
                hintStyle: TextStyle(
                  color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6),
                ),
                filled: true,
                fillColor: theme.colorScheme.onSurface.withOpacity(0.04),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(
                    horizontal: 18, vertical: 12),
              ),
              maxLines: 3,
              minLines: 1,
              textInputAction: TextInputAction.send,
            ),
          ),
          const SizedBox(width: 10),
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            child: FloatingActionButton.small(
              onPressed: isLoading ? null : _sendQuestion,
              backgroundColor: isLoading
                  ? theme.colorScheme.onSurface.withOpacity(0.1)
                  : theme.colorScheme.primary,
              elevation: 2,
              child: isLoading
                  ? SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: theme.colorScheme.primary,
                      ),
                    )
                  : const Icon(Icons.send_rounded,
                      size: 18, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  Typing dots animation
// ════════════════════════════════════════════════════════════════════

class _TypingDots extends StatefulWidget {
  final Color color;
  const _TypingDots({required this.color});

  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: widget.color.withOpacity(0.06),
        borderRadius: BorderRadius.circular(18),
      ),
      child: AnimatedBuilder(
        animation: _ctrl,
        builder: (_, __) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              final offset = ((_ctrl.value * 3) - i).clamp(0.0, 1.0);
              final bounce = offset < 0.5 ? offset * 2 : (1 - offset) * 2;
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: widget.color.withOpacity(0.4 + bounce * 0.6),
                ),
                transform: Matrix4.translationValues(0, -bounce * 6, 0),
              );
            }),
          );
        },
      ),
    );
  }
}
