// ╔══════════════════════════════════════════════════════════════════╗
// ║         LECTURE PLAYER SCREEN — Phase 5                          ║
// ║  Video streaming, chapter markers, controls, tracking, Q&A       ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:video_player/video_player.dart';
import '../../providers/lecture_provider.dart';
import 'mid_check_overlay.dart';
import 'qna_overlay.dart';
import '../../services/storage_service.dart';

// ════════════════════════════════════════════════════════════════════
//  Chapter definition
// ════════════════════════════════════════════════════════════════════

class _Chapter {
  final String title;
  final Duration start;
  const _Chapter({required this.title, required this.start});
}

// ════════════════════════════════════════════════════════════════════
//  LecturePlayerScreen
// ════════════════════════════════════════════════════════════════════

class LecturePlayerScreen extends ConsumerStatefulWidget {
  final String lectureId;

  const LecturePlayerScreen({super.key, required this.lectureId});

  @override
  ConsumerState<LecturePlayerScreen> createState() =>
      _LecturePlayerScreenState();
}

class _LecturePlayerScreenState extends ConsumerState<LecturePlayerScreen>
    with WidgetsBindingObserver {

  VideoPlayerController? _controller;
  bool _showControls = true;
  bool _showQna = false;
  bool _isFullScreen = false;
  Timer? _controlsHideTimer;
  bool _wasPlayingBeforeMidCheck = false;

  static const _speeds = [0.5, 1.0, 1.25, 1.5, 2.0];

  // Chapters loaded from real DB via lectureProvider
  List<_Chapter> get _chapters =>
      ref.read(lectureProvider).chapters
          .map((c) => _Chapter(title: c.title, start: c.startDuration))
          .toList();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Load real lecture data (videoUrl, chapters, courseId) from DB
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final notifier = ref.read(lectureProvider.notifier);
      await notifier.loadLecture(int.parse(widget.lectureId));
      final videoUrl = ref.read(lectureProvider).videoUrl;
      if (videoUrl != null && mounted) {
        await _initVideo(videoUrl);
      }
      await _startSession();
      // Load mid-quiz from DB (ready when 50% triggers)
      await notifier.loadMidQuiz(int.parse(widget.lectureId));
    });
  }

  Future<void> _initVideo(String videoUrl) async {
    _controller = VideoPlayerController.networkUrl(
      Uri.parse(videoUrl),
    );
    await _controller!.initialize();

    // Auto-seek to saved position if exists
    final savedSeconds = await StorageService().getVideoPosition(int.parse(widget.lectureId));
    if (savedSeconds > 0) {
      await _controller!.seekTo(Duration(seconds: savedSeconds));
    }

    _controller!.addListener(_onVideoUpdate);
    if (mounted) {
      setState(() {});
      _controller!.play();
      _scheduleHideControls();
    }
  }

  Future<void> _startSession() async {
    await ref
        .read(lectureProvider.notifier)
        .startSession(int.parse(widget.lectureId));
  }

  void _onVideoUpdate() {
    if (_controller == null || !_controller!.value.isInitialized) return;

    final total = _controller!.value.duration.inMilliseconds;
    final current = _controller!.value.position.inMilliseconds;
    final watchPct = total > 0 ? (current / total) * 100.0 : 0.0;

    ref.read(lectureProvider.notifier).updateWatchState(
          watchPercentage: watchPct,
        );

    // Save current playback position
    final currentSeconds = _controller!.value.position.inSeconds;
    StorageService().saveVideoPosition(int.parse(widget.lectureId), currentSeconds);

    // End of video
    if (_controller!.value.position >= _controller!.value.duration &&
        !_controller!.value.isPlaying) {
      _onVideoEnd();
    }

    if (mounted) setState(() {});
  }

  Future<void> _onVideoEnd() async {
    // Reset video position to 0 when ended
    await StorageService().saveVideoPosition(int.parse(widget.lectureId), 0);
    await ref.read(lectureProvider.notifier).endSession();
    if (mounted) {
      // Navigate to PostQuiz (Phase 6) — for now just pop
      context.pop();
    }
  }

  void _togglePlay() {
    if (_controller == null) return;
    setState(() {
      if (_controller!.value.isPlaying) {
        _controller!.pause();
        ref.read(lectureProvider.notifier).updateWatchState(
              watchPercentage: _watchPct,
              additionalPauses: 1,
            );
      } else {
        _controller!.play();
        _scheduleHideControls();
      }
    });
  }

  void _seekRelative(Duration delta) {
    if (_controller == null) return;
    final newPos = _controller!.value.position + delta;
    // Duration has no .clamp — manually clamp between zero and total
    final minDur = Duration.zero;
    final maxDur = _controller!.value.duration;
    final clamped = newPos < minDur ? minDur : (newPos > maxDur ? maxDur : newPos);
    _controller!.seekTo(clamped);
  }

  void _seekToChapter(_Chapter chapter) {
    _controller?.seekTo(chapter.start);
    _showControlsTemporarily();
  }

  void _setSpeed(double speed) {
    _controller?.setPlaybackSpeed(speed);
    ref.read(lectureProvider.notifier).updateWatchState(
          watchPercentage: _watchPct,
          playbackSpeed: speed,
        );
    setState(() {});
  }

  void _scheduleHideControls() {
    _controlsHideTimer?.cancel();
    _controlsHideTimer = Timer(const Duration(seconds: 3), () {
      if (mounted && (_controller?.value.isPlaying ?? false)) {
        setState(() => _showControls = false);
      }
    });
  }

  void _showControlsTemporarily() {
    setState(() => _showControls = true);
    _scheduleHideControls();
  }

  double get _watchPct {
    if (_controller == null || !_controller!.value.isInitialized) return 0;
    final total = _controller!.value.duration.inMilliseconds;
    final current = _controller!.value.position.inMilliseconds;
    return total > 0 ? (current / total) * 100 : 0;
  }

  String _formatDuration(Duration d) {
    final h = d.inHours;
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return h > 0 ? '$h:$m:$s' : '$m:$s';
  }

  _Chapter? get _currentChapter {
    if (_controller == null) return null;
    final pos = _controller!.value.position;
    _Chapter? current;
    for (final ch in _chapters) {
      if (pos >= ch.start) current = ch;
    }
    return current;
  }

  void _onMidCheckComplete() {
    ref.read(lectureProvider.notifier).dismissMidCheck();
    if (_wasPlayingBeforeMidCheck) {
      _controller?.play();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      _controller?.pause();
    }
  }

  @override
  void dispose() {
    _controlsHideTimer?.cancel();
    _controller?.removeListener(_onVideoUpdate);
    _controller?.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lectureState = ref.watch(lectureProvider);
    final theme = Theme.of(context);
    final isInitialized = _controller?.value.isInitialized ?? false;

    // Pause video when mid-check appears
    if (lectureState.showMidCheck && (_controller?.value.isPlaying ?? false)) {
      _wasPlayingBeforeMidCheck = true;
      _controller?.pause();
    }

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          children: [
            // ── Main content ───────────────────────────────────────
            Column(
              children: [
                // Video area
                _buildVideoArea(theme, isInitialized),

                // Info + chapters panel
                if (!_isFullScreen)
                  Expanded(
                    child: _buildInfoPanel(theme, lectureState),
                  ),
              ],
            ),

            // ── Mid-check overlay ──────────────────────────────────
            if (lectureState.showMidCheck)
              Positioned.fill(
                child: MidCheckOverlay(
                  questions: lectureState.midQuestions,
                  onComplete: _onMidCheckComplete,
                ),
              ),

            // ── Q&A overlay ────────────────────────────────────────
            if (_showQna)
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: GestureDetector(
                  onTap: () {}, // Prevent tap-through
                  child: QnaOverlay(
                    courseId: ref.read(lectureProvider).courseId ?? 0,
                    onClose: () => setState(() => _showQna = false),
                  ),
                ),
              ),

            // ── Q&A floating button (only when Q&A is closed) ──────
            if (!_showQna && !lectureState.showMidCheck)
              Positioned(
                right: 20,
                bottom: 100,
                child: FloatingActionButton(
                  onPressed: () => setState(() => _showQna = true),
                  mini: true,
                  backgroundColor: theme.colorScheme.primary,
                  child: const Icon(Icons.chat_bubble_rounded,
                      color: Colors.white, size: 20),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ── Video area with controls overlay ──────────────────────────────

  Widget _buildVideoArea(ThemeData theme, bool isInitialized) {
    return GestureDetector(
      onTap: _showControlsTemporarily,
      child: Container(
        color: Colors.black,
        height: _isFullScreen
            ? MediaQuery.of(context).size.height
            : MediaQuery.of(context).size.width * 9 / 16 + 44, // 16:9 + appbar
        child: Stack(
          children: [
            // Video
            Center(
              child: isInitialized
                  ? AspectRatio(
                      aspectRatio: _controller!.value.aspectRatio,
                      child: VideoPlayer(_controller!),
                    )
                  : _buildVideoPlaceholder(),
            ),

            // Top bar (always visible)
            _buildTopBar(theme),

            // Controls overlay
            if (_showControls || !(_controller?.value.isPlaying ?? false))
              _buildControlsOverlay(theme),

            // Progress bar (always at bottom of video)
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: _buildProgressBar(theme),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVideoPlaceholder() {
    return Container(
      color: const Color(0xFF0A0A0A),
      child: const Center(
        child: SizedBox(
          width: 36,
          height: 36,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: Colors.white,
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar(ThemeData theme) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: EdgeInsets.only(
          top: MediaQuery.of(context).padding.top + 8,
          left: 8,
          right: 8,
          bottom: 8,
        ),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.black.withOpacity(0.7), Colors.transparent],
          ),
        ),
        child: Row(
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back_ios_new_rounded,
                  color: Colors.white, size: 20),
              onPressed: () async {
                await ref.read(lectureProvider.notifier).endSession();
                if (mounted) context.pop();
              },
            ),
            Expanded(
              child: Text(
                'Lecture #${widget.lectureId}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            IconButton(
              icon: Icon(
                _isFullScreen ? Icons.fullscreen_exit : Icons.fullscreen,
                color: Colors.white,
                size: 22,
              ),
              onPressed: () => setState(() => _isFullScreen = !_isFullScreen),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlsOverlay(ThemeData theme) {
    final isPlaying = _controller?.value.isPlaying ?? false;
    final lectureState = ref.watch(lectureProvider);
    final speed = lectureState.playbackSpeed;

    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.transparent,
              Colors.black.withOpacity(0.4),
              Colors.black.withOpacity(0.7),
            ],
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                // Rewind 10s
                IconButton(
                  onPressed: () => _seekRelative(const Duration(seconds: -10)),
                  icon: const Icon(Icons.replay_10_rounded,
                      color: Colors.white, size: 32),
                ),
                // Play/Pause
                GestureDetector(
                  onTap: _togglePlay,
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: Colors.white.withOpacity(0.4), width: 1.5),
                    ),
                    child: Icon(
                      isPlaying
                          ? Icons.pause_rounded
                          : Icons.play_arrow_rounded,
                      color: Colors.white,
                      size: 36,
                    ),
                  ),
                ),
                // Forward 10s
                IconButton(
                  onPressed: () => _seekRelative(const Duration(seconds: 10)),
                  icon: const Icon(Icons.forward_10_rounded,
                      color: Colors.white, size: 32),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // Speed selector
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  PopupMenuButton<double>(
                    onSelected: _setSpeed,
                    color: const Color(0xFF1A1A2E),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color: Colors.white.withOpacity(0.25)),
                      ),
                      child: Text(
                        '${speed}x',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    itemBuilder: (ctx) => _speeds
                        .map((s) => PopupMenuItem(
                              value: s,
                              child: Text(
                                '${s}x',
                                style: TextStyle(
                                  color: s == speed
                                      ? theme.colorScheme.primary
                                      : Colors.white,
                                  fontWeight: s == speed
                                      ? FontWeight.w700
                                      : FontWeight.normal,
                                ),
                              ),
                            ))
                        .toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 36), // Space for progress bar
          ],
        ),
      ),
    );
  }

  Widget _buildProgressBar(ThemeData theme) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const SizedBox.shrink();
    }

    final position = _controller!.value.position;
    final duration = _controller!.value.duration;
    final total = duration.inMilliseconds.toDouble();
    final current = position.inMilliseconds.toDouble();
    final value = total > 0 ? (current / total).clamp(0.0, 1.0) : 0.0;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Time labels
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _formatDuration(position),
                style: const TextStyle(
                    color: Colors.white70, fontSize: 11),
              ),
              Text(
                _formatDuration(duration),
                style: const TextStyle(
                    color: Colors.white70, fontSize: 11),
              ),
            ],
          ),
        ),
        // Slider
        SliderTheme(
          data: SliderThemeData(
            thumbShape:
                const RoundSliderThumbShape(enabledThumbRadius: 6),
            trackHeight: 3,
            activeTrackColor: theme.colorScheme.primary,
            inactiveTrackColor: Colors.white24,
            thumbColor: Colors.white,
            overlayColor: Colors.white12,
          ),
          child: Slider(
            value: value,
            onChanged: (v) {
              final seekTo =
                  Duration(milliseconds: (v * total).round());
              _controller?.seekTo(seekTo);
            },
          ),
        ),
      ],
    );
  }

  // ── Info panel below video ─────────────────────────────────────────

  Widget _buildInfoPanel(ThemeData theme, LectureState lectureState) {
    return Container(
      color: theme.scaffoldBackgroundColor,
      child: DefaultTabController(
        length: 2,
        child: Column(
          children: [
            TabBar(
              labelColor: theme.colorScheme.primary,
              unselectedLabelColor: theme.colorScheme.onSurfaceVariant,
              indicatorColor: theme.colorScheme.primary,
              indicatorWeight: 2,
              tabs: const [
                Tab(text: 'Chapters'),
                Tab(text: 'Progress'),
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  // Chapters
                  _buildChaptersList(theme),
                  // Progress
                  _buildProgressTab(theme, lectureState),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChaptersList(ThemeData theme) {
    final currentChapter = _currentChapter;

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _chapters.length,
      itemBuilder: (ctx, i) {
        final ch = _chapters[i];
        final isCurrent = ch == currentChapter;

        return GestureDetector(
          onTap: () => _seekToChapter(ch),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            margin: const EdgeInsets.only(bottom: 10),
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: isCurrent
                  ? theme.colorScheme.primary.withOpacity(0.1)
                  : theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isCurrent
                    ? theme.colorScheme.primary.withOpacity(0.4)
                    : theme.colorScheme.outline.withOpacity(0.15),
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isCurrent
                        ? theme.colorScheme.primary
                        : theme.colorScheme.primary.withOpacity(0.1),
                  ),
                  child: Center(
                    child: Icon(
                      isCurrent
                          ? Icons.play_arrow_rounded
                          : Icons.circle_outlined,
                      size: 18,
                      color: isCurrent
                          ? Colors.white
                          : theme.colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        ch.title,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: isCurrent
                              ? FontWeight.w700
                              : FontWeight.w500,
                          color: isCurrent
                              ? theme.colorScheme.primary
                              : theme.colorScheme.onSurface,
                        ),
                      ),
                      Text(
                        _formatDuration(ch.start),
                        style: TextStyle(
                          fontSize: 12,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                if (isCurrent)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Text(
                      'Now',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildProgressTab(ThemeData theme, LectureState lectureState) {
    final watchPct = lectureState.watchPercentage.clamp(0, 100);
    final engagement = ref.read(lectureProvider.notifier).engagementScore;
    final qnaCount =
        lectureState.qnaMessages.where((m) => m.isUser).length;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatCard(
            theme,
            icon: Icons.remove_red_eye_rounded,
            label: 'Watch Progress',
            value: '${watchPct.toInt()}%',
            color: theme.colorScheme.primary,
            progress: watchPct / 100,
          ),
          const SizedBox(height: 12),
          _buildStatCard(
            theme,
            icon: Icons.speed_rounded,
            label: 'Engagement Score',
            value: '${(engagement * 100).toInt()}%',
            color: const Color(0xFF00BFA5),
            progress: engagement,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildSmallStat(
                    theme, Icons.pause_rounded, 'Pauses',
                    '${lectureState.pauseCount}', const Color(0xFFFFB74D)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildSmallStat(
                    theme, Icons.chat_rounded, 'Questions',
                    '$qnaCount', const Color(0xFF6C63FF)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(
    ThemeData theme, {
    required IconData icon,
    required String label,
    required String value,
    required Color color,
    required double progress,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  fontSize: 13,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const Spacer(),
              Text(
                value,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 6,
              backgroundColor: color.withOpacity(0.12),
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSmallStat(ThemeData theme, IconData icon, String label,
      String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(value,
                  style: TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w800, color: color)),
              Text(label,
                  style: TextStyle(
                      fontSize: 11,
                      color: theme.colorScheme.onSurfaceVariant)),
            ],
          ),
        ],
      ),
    );
  }
}
