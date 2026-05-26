// ╔══════════════════════════════════════════════════════════════════╗
// ║         DASHBOARD SHELL — ShellRoute with BottomNavBar           ║
// ║  4 tabs: Home, Courses, Attendance, Profile                      ║
// ║  Bilingual support and RTL layout direction.                     ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../providers/settings_provider.dart';

class DashboardShell extends ConsumerWidget {
  /// Child widget — current tab ki screen
  final Widget child;

  const DashboardShell({super.key, required this.child});

  // ── Tab definitions ───────────────────────────────────────────────
  static const _tabs = [
    _TabInfo(
      path: AppConstants.routeDashboardHome,
      icon: Icons.home_rounded,
      activeIcon: Icons.home_rounded,
      key: 'home',
    ),
    _TabInfo(
      path: AppConstants.routeDashboardCourses,
      icon: Icons.menu_book_outlined,
      activeIcon: Icons.menu_book_rounded,
      key: 'my_courses',
    ),
    _TabInfo(
      path: AppConstants.routeDashboardAttendance,
      icon: Icons.fact_check_outlined,
      activeIcon: Icons.fact_check_rounded,
      key: 'attendance',
    ),
    _TabInfo(
      path: AppConstants.routeDashboardProfile,
      icon: Icons.person_outline_rounded,
      activeIcon: Icons.person_rounded,
      key: 'profile',
    ),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final settings = ref.watch(settingsProvider);
    final isUrdu = settings.language == 'Urdu';

    // ── Current location — GoRouterState se parhna ───────────────────
    // IMPORTANT: GoRouterState.of(context) aur context.go() same context
    // mein use karne se circular rebuild issue ho sakta hai.
    // Isliye hum GoRouter.of(context) se router nikaalte hain aur
    // location GoRouterState.of(context) se alag context mein padhte hain.
    final router = GoRouter.of(context);
    final currentLocation = GoRouterState.of(context).matchedLocation;

    // Current tab index detect karo
    int activeIndex = 0;
    for (int i = 0; i < _tabs.length; i++) {
      if (currentLocation.startsWith(_tabs[i].path)) {
        activeIndex = i;
        break;
      }
    }

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        body: child,
        bottomNavigationBar: Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.08),
                blurRadius: 20,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: SafeArea(
            child: SizedBox(
              height: 64,
              child: Row(
                children: List.generate(_tabs.length, (index) {
                  final tab = _tabs[index];
                  final isActive = index == activeIndex;
                  final color = isActive
                      ? theme.colorScheme.primary
                      : theme.colorScheme.onSurfaceVariant.withOpacity(0.6);
                  final label = settings.translate(tab.key);

                  return Expanded(
                    child: GestureDetector(
                      // GestureDetector use karo — InkWell ke bajaye
                      // Desktop par GestureDetector more reliable hai
                      // jab parent aur child contexts alag hoon
                      behavior: HitTestBehavior.opaque,
                      onTap: () {
                        // router.go() use karo — context.go() nahi
                        // Yeh same GoRouter instance use karta hai
                        // lekin context binding se bachata hai
                        router.go(tab.path);
                      },
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        curve: Curves.easeInOut,
                        color: isActive
                            ? theme.colorScheme.primary.withOpacity(0.06)
                            : Colors.transparent,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            // Active indicator pill
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              curve: Curves.easeInOut,
                              width: isActive ? 28 : 0,
                              height: 2,
                              decoration: BoxDecoration(
                                color: theme.colorScheme.primary,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                            const SizedBox(height: 2),
                            Icon(
                              isActive ? tab.activeIcon : tab.icon,
                              color: color,
                              size: 24,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              label,
                              style: TextStyle(
                                color: color,
                                fontSize: 11,
                                fontWeight: isActive
                                    ? FontWeight.w700
                                    : FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TabInfo {
  final String path;
  final IconData icon;
  final IconData activeIcon;
  final String key;

  const _TabInfo({
    required this.path,
    required this.icon,
    required this.activeIcon,
    required this.key,
  });
}
