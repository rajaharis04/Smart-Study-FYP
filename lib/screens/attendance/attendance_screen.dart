// ╔══════════════════════════════════════════════════════════════════╗
// ║          ATTENDANCE SCREEN — Dynamic Attendance & Trend          ║
// ║  Student ki attendance detail, filters, aur line graph trend     ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart' hide TextDirection;
import '../../core/widgets/skeleton_shimmer.dart';
import '../../core/widgets/error_retry_widget.dart';
import '../../models/models.dart';
import '../../providers/attendance_provider.dart';
import '../../providers/settings_provider.dart';

class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({super.key});

  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> with SingleTickerProviderStateMixin {
  String _selectedCourseCode = 'ALL'; // ALL or specific course code
  bool _sortByDateDesc = true; // true = newest first, false = oldest first
  String _sortByField = 'DATE'; // DATE or STATUS
  
  // Animation for the line chart drawing
  late AnimationController _chartAnimController;
  late Animation<double> _chartAnimation;

  @override
  void initState() {
    super.initState();
    _chartAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _chartAnimation = CurvedAnimation(
      parent: _chartAnimController,
      curve: Curves.easeInOutCubic,
    );

    Future.microtask(() {
      ref.read(attendanceProvider.notifier).getAttendance().then((_) {
        _chartAnimController.forward(from: 0.0);
      });
    });
  }

  @override
  void dispose() {
    _chartAnimController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    await ref.read(attendanceProvider.notifier).getAttendance();
    _chartAnimController.forward(from: 0.0);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(attendanceProvider);
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);

    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(settings.translate('attendance')),
        backgroundColor: theme.colorScheme.surface,
        elevation: 0,
        centerTitle: false,
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: _buildBody(state, theme),
      ),
    );
  }

  Widget _buildBody(AttendanceState state, ThemeData theme) {
    if (state.isLoading) {
      return _buildSkeletonLoader();
    }

    if (state.error != null) {
      return ErrorRetryWidget(
        errorMessage: state.error!,
        onRetry: _refresh,
      );
    }

    final data = state.attendanceData;
    if (data == null) {
      return Center(
        child: ElevatedButton(
          onPressed: _refresh,
          child: const Text('Load Attendance'),
        ),
      );
    }

    // Filter attendance items based on course selection
    List<AttendanceItem> filteredItems = data.attendanceList;
    if (_selectedCourseCode != 'ALL') {
      filteredItems = data.attendanceList
          .where((item) => item.courseCode == _selectedCourseCode)
          .toList();
    }

    // Sort attendance items
    final sortedItems = List<AttendanceItem>.from(filteredItems);
    sortedItems.sort((a, b) {
      if (_sortByField == 'DATE') {
        final aDate = DateTime.tryParse(a.date) ?? DateTime.now();
        final bDate = DateTime.tryParse(b.date) ?? DateTime.now();
        return _sortByDateDesc ? bDate.compareTo(aDate) : aDate.compareTo(bDate);
      } else {
        // Status sort
        return _sortByDateDesc ? b.status.compareTo(a.status) : a.status.compareTo(b.status);
      }
    });

    // Calculate dynamic stats for selected course vs overall
    int present = 0;
    int absent = 0;
    int partial = 0;
    for (var item in filteredItems) {
      if (item.status == '✓') present++;
      if (item.status == '✗') absent++;
      if (item.status == 'P') partial++;
    }
    final total = filteredItems.length;
    double calculatedOverall = total > 0 ? (present / total) * 100 : 100.0;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── A. Summary Card ──────────────────────────────────────────
            _buildSummaryCard(theme, calculatedOverall, present, absent, partial, total),
            const SizedBox(height: 24),

            // ── B. Course Selection & Filters ────────────────────────────
            _buildFiltersRow(theme, data.courses),
            const SizedBox(height: 20),

            // ── C. Attendance Trend Line Chart ───────────────────────────
            _buildTrendChartSection(theme, filteredItems),
            const SizedBox(height: 24),

            // ── D. Detailed Attendance Log ───────────────────────────────
            _buildLogsHeader(theme),
            const SizedBox(height: 12),
            _buildLogsList(theme, sortedItems),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(
    ThemeData theme,
    double overallPct,
    int present,
    int absent,
    int partial,
    int total,
  ) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';
    final statusColor = overallPct >= 75
        ? const Color(0xFF00BFA5) // Green (safe)
        : const Color(0xFFFF6B6B); // Red (shortage danger)

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: statusColor.withOpacity(0.08),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                settings.translate('attendance_summary'),
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  overallPct >= 75 ? settings.translate('safe_status') : settings.translate('at_risk'),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Main percentage layout
          Row(
            children: [
              Text(
                '${overallPct.toStringAsFixed(1)}%',
                style: TextStyle(
                  fontSize: 48,
                  fontWeight: FontWeight.w900,
                  color: statusColor,
                  letterSpacing: -1,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: overallPct / 100,
                        backgroundColor: statusColor.withOpacity(0.12),
                        valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                        minHeight: 8,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      overallPct >= 75
                          ? (isUrdu ? '✅ حاضری کی شرح تسلی بخش ہے' : '✅ Attendance requirement met')
                          : (isUrdu ? '⚠️ حاضری 75 فیصد سے کم ہے' : '⚠️ Below 75% minimum criteria'),
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSurfaceVariant,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const Divider(height: 32),
          
          // Detailed counters
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildStatCounter(settings.translate('present'), present, const Color(0xFF00BFA5)),
              _buildStatCounter(settings.translate('absent'), absent, const Color(0xFFFF6B6B)),
              _buildStatCounter(settings.translate('partial'), partial, const Color(0xFFFFB74D)),
              _buildStatCounter(settings.translate('total_lectures'), total, const Color(0xFF6C63FF)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatCounter(String label, int value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(shape: BoxShape.circle, color: color),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: Colors.grey),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Padding(
          padding: const EdgeInsets.only(left: 14.0),
          child: Text(
            '$value',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: color),
          ),
        ),
      ],
    );
  }

  Widget _buildFiltersRow(ThemeData theme, List<Course> courses) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    return Row(
      children: [
        // Dropdown Course Selector
        Expanded(
          flex: 3,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: theme.colorScheme.outline.withOpacity(0.15)),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _selectedCourseCode,
                icon: const Icon(Icons.arrow_drop_down_rounded, size: 28),
                isExpanded: true,
                onChanged: (String? val) {
                  if (val != null) {
                    setState(() {
                      _selectedCourseCode = val;
                      _chartAnimController.forward(from: 0.0);
                    });
                  }
                },
                items: [
                  DropdownMenuItem(
                    value: 'ALL',
                    child: Text(isUrdu ? 'تمام کورسز' : 'All Courses', style: const TextStyle(fontWeight: FontWeight.w600)),
                  ),
                  ...courses.map((course) => DropdownMenuItem(
                        value: course.code,
                        child: Text(course.code, style: const TextStyle(fontWeight: FontWeight.w600)),
                      )),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        
        // Sorting triggers
        Expanded(
          flex: 2,
          child: InkWell(
            onTap: () {
              setState(() {
                if (_sortByField == 'DATE') {
                  _sortByDateDesc = !_sortByDateDesc;
                } else {
                  _sortByField = 'DATE';
                  _sortByDateDesc = true;
                }
              });
            },
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: theme.colorScheme.outline.withOpacity(0.15)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _sortByField == 'DATE'
                        ? (_sortByDateDesc ? (isUrdu ? 'تازہ ترین' : 'Newest') : (isUrdu ? 'قدیم ترین' : 'Oldest'))
                        : (isUrdu ? 'ترتیب تاریخ' : 'Sort Date'),
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _sortByField == 'DATE'
                        ? (_sortByDateDesc ? Icons.south_rounded : Icons.north_rounded)
                        : Icons.unfold_more_rounded,
                    size: 14,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTrendChartSection(ThemeData theme, List<AttendanceItem> items) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    // Collect chronological items for trend drawing (oldest first)
    final chronological = List<AttendanceItem>.from(items);
    chronological.sort((a, b) {
      final aD = DateTime.tryParse(a.date) ?? DateTime.now();
      final bD = DateTime.tryParse(b.date) ?? DateTime.now();
      return aD.compareTo(bD);
    });

    // Draw last 7 sessions for clean display
    final chartData = chronological.length > 7
        ? chronological.sublist(chronological.length - 7)
        : chronological;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 15,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            settings.translate('attendance_trend'),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: theme.colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: 16),
          chartData.isEmpty
              ? Container(
                  height: 150,
                  alignment: Alignment.center,
                  child: Text(isUrdu ? 'رجحان دکھانے کے لئے کوئی حاضری دستیاب نہیں ہے۔' : 'No attendance recorded to show trend.', style: const TextStyle(color: Colors.grey)),
                )
              : AnimatedBuilder(
                  animation: _chartAnimation,
                  builder: (context, child) {
                    return CustomPaint(
                      size: const Size(double.infinity, 160),
                      painter: _LineTrendChartPainter(
                        theme: theme,
                        dataPoints: chartData,
                        animProgress: _chartAnimation.value,
                      ),
                    );
                  },
                ),
        ],
      ),
    );
  }

  Widget _buildLogsHeader(ThemeData theme) {
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          settings.translate('logs'),
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            color: theme.colorScheme.onSurface,
          ),
        ),
        TextButton.icon(
          onPressed: () {
            setState(() {
              if (_sortByField == 'STATUS') {
                _sortByDateDesc = !_sortByDateDesc;
              } else {
                _sortByField = 'STATUS';
                _sortByDateDesc = true;
              }
            });
          },
          icon: const Icon(Icons.sort_rounded, size: 14),
          label: Text(
            _sortByField == 'STATUS'
                ? (isUrdu ? 'ترتیب بلحاظ صورتحال' : 'Filtered by Status')
                : (isUrdu ? 'صورتحال سے ترتیب دیں' : 'Sort Status'),
            style: const TextStyle(fontSize: 11),
          ),
          style: TextButton.styleFrom(
            padding: EdgeInsets.zero,
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
      ],
    );
  }

  Widget _buildLogsList(ThemeData theme, List<AttendanceItem> items) {
    if (items.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(vertical: 40),
        alignment: Alignment.center,
        child: Column(
          children: [
            Icon(Icons.assignment_turned_in_rounded, size: 48, color: Colors.grey.withOpacity(0.5)),
            const SizedBox(height: 12),
            const Text('No records found for selected filter.', style: TextStyle(color: Colors.grey, fontSize: 13)),
          ],
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];

        // Format dates beautifully
        String dateFormatted = item.date;
        try {
          final dt = DateTime.parse(item.date);
          dateFormatted = DateFormat('MMM dd, yyyy').format(dt);
        } catch (_) {}

        // Status Badge settings
        Color statusColor;
        String statusLabel;
        if (item.status == '✓') {
          statusColor = const Color(0xFF00BFA5); // Present Green
          statusLabel = 'Present';
        } else if (item.status == 'P') {
          statusColor = const Color(0xFFFFB74D); // Partial Yellow
          statusLabel = 'Partial';
        } else {
          statusColor = const Color(0xFFFF6B6B); // Absent Red
          statusLabel = 'Absent';
        }

        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.02),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
            border: Border.all(color: theme.colorScheme.outline.withOpacity(0.06)),
          ),
          child: Row(
            children: [
              // Watch % circle badge
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.08),
                  shape: BoxShape.circle,
                ),
                child: Center(
                  child: Text(
                    '${item.watchPercentage.toInt()}%',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: statusColor,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // Lecture details
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.lectureName,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.courseCode}  •  $dateFormatted',
                      style: TextStyle(
                        fontSize: 11,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),

              // Status Badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSkeletonLoader() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            const SkeletonShimmer(width: double.infinity, height: 170, borderRadius: 24),
            const SizedBox(height: 24),
            Row(
              children: const [
                Expanded(child: SkeletonShimmer(width: double.infinity, height: 50, borderRadius: 12)),
                SizedBox(width: 12),
                Expanded(child: SkeletonShimmer(width: double.infinity, height: 50, borderRadius: 12)),
              ],
            ),
            const SizedBox(height: 20),
            const SkeletonShimmer(width: double.infinity, height: 230, borderRadius: 20),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: const [
                SkeletonShimmer(width: 150, height: 16),
                SkeletonShimmer(width: 85, height: 16),
              ],
            ),
            const SizedBox(height: 12),
            ...List.generate(3, (_) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: SkeletonShimmer(width: double.infinity, height: 76, borderRadius: 16),
            )),
          ],
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  Vector Line Chart Custom Painter
//  Draws cubic bezier curve for watch percentage chronological history
// ════════════════════════════════════════════════════════════════════
class _LineTrendChartPainter extends CustomPainter {
  final ThemeData theme;
  final List<AttendanceItem> dataPoints;
  final double animProgress;

  _LineTrendChartPainter({
    required this.theme,
    required this.dataPoints,
    required this.animProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (dataPoints.isEmpty) return;

    final paintLine = Paint()
      ..color = theme.colorScheme.primary
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final paintLineGlow = Paint()
      ..color = theme.colorScheme.primary.withOpacity(0.18)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final paintFill = Paint()
      ..style = PaintingStyle.fill;

    final borderPaint = Paint()
      ..color = theme.colorScheme.outline.withOpacity(0.12)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    final double paddingLeft = 32.0;
    final double paddingRight = 16.0;
    final double paddingTop = 12.0;
    final double paddingBottom = 24.0;

    final chartWidth = size.width - paddingLeft - paddingRight;
    final chartHeight = size.height - paddingTop - paddingBottom;

    // Draw horizontal grid lines at 0%, 50%, 100%
    final gridLevels = [0.0, 0.5, 1.0];
    for (var level in gridLevels) {
      final y = paddingTop + chartHeight * (1.0 - level);
      
      // Draw grid line
      canvas.drawLine(
        Offset(paddingLeft, y),
        Offset(size.width - paddingRight, y),
        borderPaint,
      );

      // Draw grid text label (0, 50, 100)
      final textSpan = TextSpan(
        text: '${(level * 100).toInt()}%',
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w600,
          color: theme.colorScheme.onSurfaceVariant.withOpacity(0.5),
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(
        canvas,
        Offset(paddingLeft - textPainter.width - 6, y - textPainter.height / 2),
      );
    }

    // Map dataPoints to Coordinate offsets
    final List<Offset> points = [];
    final double stepX = dataPoints.length > 1 ? chartWidth / (dataPoints.length - 1) : chartWidth;

    for (int i = 0; i < dataPoints.length; i++) {
      final pct = dataPoints[i].watchPercentage;
      final x = paddingLeft + i * stepX;
      // Invert Y axes mapping (100% is top of graph, which is y=paddingTop)
      final targetY = paddingTop + chartHeight * (1.0 - (pct / 100.0));
      // Interpolate with animation progress
      final currentY = (size.height - paddingBottom) - ((size.height - paddingBottom) - targetY) * animProgress;
      points.add(Offset(x, currentY));
    }

    if (points.isEmpty) return;

    // Build line path (smooth cubic splines / bezier)
    final path = Path();
    path.moveTo(points[0].dx, points[0].dy);

    for (int i = 0; i < points.length - 1; i++) {
      final pStart = points[i];
      final pEnd = points[i + 1];
      final controlPoint1 = Offset(pStart.dx + (pEnd.dx - pStart.dx) / 2, pStart.dy);
      final controlPoint2 = Offset(pStart.dx + (pEnd.dx - pStart.dx) / 2, pEnd.dy);

      path.cubicTo(
        controlPoint1.dx, controlPoint1.dy,
        controlPoint2.dx, controlPoint2.dy,
        pEnd.dx, pEnd.dy,
      );
    }

    // Draw bottom gradient fill
    final fillPath = Path.from(path);
    // Line down to bottom right of chart
    fillPath.lineTo(points.last.dx, size.height - paddingBottom);
    // Line left to bottom left of chart
    fillPath.lineTo(points.first.dx, size.height - paddingBottom);
    fillPath.close();

    paintFill.shader = LinearGradient(
      colors: [
        theme.colorScheme.primary.withOpacity(0.20),
        theme.colorScheme.primary.withOpacity(0.00),
      ],
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
    ).createShader(Rect.fromLTRB(paddingLeft, paddingTop, size.width, size.height - paddingBottom));

    canvas.drawPath(fillPath, paintFill);

    // Draw vector lines
    canvas.drawPath(path, paintLineGlow);
    canvas.drawPath(path, paintLine);

    // Draw interactive nodes and date labels
    for (int i = 0; i < points.length; i++) {
      final p = points[i];
      
      // Draw outer circle nodes
      canvas.drawCircle(
        p,
        4.5,
        Paint()..color = theme.colorScheme.primary,
      );
      
      // Draw inner node dot
      canvas.drawCircle(
        p,
        2.0,
        Paint()..color = Colors.white,
      );

      // Date labels at bottom
      final dateItem = dataPoints[i];
      String dateLabel = '';
      try {
        final parsed = DateTime.parse(dateItem.date);
        dateLabel = DateFormat('dd/MM').format(parsed);
      } catch (_) {
        dateLabel = dateItem.date;
      }

      final dateSpan = TextSpan(
        text: dateLabel,
        style: TextStyle(
          fontSize: 8.5,
          fontWeight: FontWeight.w600,
          color: theme.colorScheme.onSurfaceVariant.withOpacity(0.6),
        ),
      );
      final datePainter = TextPainter(
        text: dateSpan,
        textDirection: TextDirection.ltr,
      )..layout();
      datePainter.paint(
        canvas,
        Offset(p.dx - datePainter.width / 2, size.height - paddingBottom + 6),
      );
    }
  }

  @override
  bool shouldRepaint(_LineTrendChartPainter old) =>
      old.animProgress != animProgress || old.dataPoints != dataPoints;
}
