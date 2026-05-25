// ╔══════════════════════════════════════════════════════════════════╗
// ║              ONBOARDING SCREEN                                   ║
// ║  App ki pehli baar use karne par 4 instruction pages             ║
// ║  Next / Skip / Get Started buttons ke saath                      ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';

// ════════════════════════════════════════════════════════════════════
//
//  Onboarding Flow:
//
//  Page 1: Welcome → "Smart Learning Starts Here"
//  Page 2: Features → "Watch Lectures Anytime"
//  Page 3: Features → "AI-Powered Q&A"
//  Page 4: Get Started → "Ready to Excel?"
//
//  Navigation:
//    Next → agle page par
//    Skip → seedha login par
//    Get Started (last page) → login par
//
// ════════════════════════════════════════════════════════════════════

// ── Onboarding page ka data ──────────────────────────────────────────
class _OnboardingPageData {
  final String title;       // Bold heading
  final String description; // Detail text
  final IconData icon;      // Illustration icon
  final Color bgColor;      // Page background color
  final Color iconColor;    // Icon color
  final String emoji;       // Fun emoji accent

  const _OnboardingPageData({
    required this.title,
    required this.description,
    required this.icon,
    required this.bgColor,
    required this.iconColor,
    required this.emoji,
  });
}

// ── 4 pages ka data ──────────────────────────────────────────────────
const List<_OnboardingPageData> _pages = [
  // ── Page 1: Welcome ──────────────────────────────────────────────
  _OnboardingPageData(
    title: 'Smart Learning\nStarts Here',
    description:
        'SmartStudy Instructeer aapka digital classroom hai.\n'
        'Lectures dekho, quizzes do, aur apni progress track karo — '
        'sab kuch ek jagah par.',
    icon: Icons.school_rounded,
    bgColor: Color(0xFF0D7A5F),
    iconColor: Color(0xFF2DC08A),
    emoji: '🎓',
  ),
  // ── Page 2: Lectures ─────────────────────────────────────────────
  _OnboardingPageData(
    title: 'Watch Lectures\nAnywhere',
    description:
        'Recorded video lectures apni speed par dekho.\n'
        'AI automatically track karta hai — kitna dekha, '
        'kahan ruke, aur attendance automatically update hoti hai.',
    icon: Icons.play_circle_filled_rounded,
    bgColor: Color(0xFF1A3A6B),
    iconColor: Color(0xFF5B8DEF),
    emoji: '📺',
  ),
  // ── Page 3: Q&A ──────────────────────────────────────────────────
  _OnboardingPageData(
    title: 'AI-Powered\nQ&A System',
    description:
        'Koi bhi question pocho — AI tutor instantly jawab dega.\n'
        'Course material se related accurate answers, '
        'bilkul teacher ki tarah!',
    icon: Icons.psychology_rounded,
    bgColor: Color(0xFF5B1D9E),
    iconColor: Color(0xFFB47DFF),
    emoji: '🤖',
  ),
  // ── Page 4: Get Started ──────────────────────────────────────────
  _OnboardingPageData(
    title: 'Ready to\nExcel? 🚀',
    description:
        'Apna academic journey shuru karo.\n'
        'Login karo, lectures dekho, quizzes do — '
        'aur apni performance ko naye level par le jao!',
    icon: Icons.rocket_launch_rounded,
    bgColor: Color(0xFF7A2D0D),
    iconColor: Color(0xFFEF9F27),
    emoji: '⭐',
  ),
];

/// Onboarding/Welcome screen — pehli baar app open karne par.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen>
    with TickerProviderStateMixin {
  // ── PageController for swiping ────────────────────────────────────
  late PageController _pageController;

  // ── Current page track karo ───────────────────────────────────────
  int _currentPage = 0;

  // ── Page change animation ─────────────────────────────────────────
  late AnimationController _iconAnimController;
  late Animation<double> _iconScale;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();

    _iconAnimController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );

    _iconScale = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(parent: _iconAnimController, curve: Curves.elasticOut),
    );

    _iconAnimController.forward();
  }

  @override
  void dispose() {
    _pageController.dispose();
    _iconAnimController.dispose();
    super.dispose();
  }

  // ══════════════════════════════════════════════════════════════════
  //  Navigation Methods
  // ══════════════════════════════════════════════════════════════════

  /// Agle page par jao
  void _nextPage() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOutCubic,
      );
    } else {
      _goToLogin();
    }
  }

  /// Skip — seedha login par
  void _goToLogin() {
    context.go(AppConstants.routeLogin);
  }

  /// Page changed
  void _onPageChanged(int index) {
    setState(() => _currentPage = index);
    // Icon animate karo
    _iconAnimController.reset();
    _iconAnimController.forward();
  }

  bool get _isLastPage => _currentPage == _pages.length - 1;

  // ══════════════════════════════════════════════════════════════════
  //  Build
  // ══════════════════════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    final currentData = _pages[_currentPage];
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: AnimatedContainer(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              currentData.bgColor,
              currentData.bgColor.withOpacity(0.85),
              Colors.black.withOpacity(0.4),
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // ── Top Bar (Skip button + Page indicator) ──────────────
              _buildTopBar(currentData),

              // ── PageView (swipeable) ────────────────────────────────
              Expanded(
                child: PageView.builder(
                  controller: _pageController,
                  onPageChanged: _onPageChanged,
                  itemCount: _pages.length,
                  itemBuilder: (context, index) {
                    return _buildPage(_pages[index], size);
                  },
                ),
              ),

              // ── Bottom Navigation Bar ───────────────────────────────
              _buildBottomBar(currentData),

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Top Bar — Page Dots + Skip Button
  // ──────────────────────────────────────────────────────────────────
  Widget _buildTopBar(_OnboardingPageData data) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Page dots
          Row(
            children: List.generate(_pages.length, (i) {
              final isActive = i == _currentPage;
              return AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                margin: const EdgeInsets.only(right: 6),
                width: isActive ? 24 : 8,
                height: 8,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(4),
                  color: isActive
                      ? Colors.white
                      : Colors.white.withOpacity(0.35),
                ),
              );
            }),
          ),

          // Skip button (sirf last page par nahi dikhaega)
          if (!_isLastPage)
            TextButton(
              onPressed: _goToLogin,
              style: TextButton.styleFrom(
                foregroundColor: Colors.white70,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Skip',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                  ),
                  SizedBox(width: 4),
                  Icon(Icons.skip_next_rounded, size: 18),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Page Content
  // ──────────────────────────────────────────────────────────────────
  Widget _buildPage(_OnboardingPageData data, Size size) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // ── Illustration Circle ──────────────────────────────────
          AnimatedBuilder(
            animation: _iconAnimController,
            builder: (context, child) {
              return Transform.scale(
                scale: _iconScale.value,
                child: child,
              );
            },
            child: Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withOpacity(0.12),
                border: Border.all(
                  color: data.iconColor.withOpacity(0.5),
                  width: 2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: data.iconColor.withOpacity(0.3),
                    blurRadius: 40,
                    spreadRadius: 5,
                  ),
                ],
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Icon(
                    data.icon,
                    size: 90,
                    color: data.iconColor,
                  ),
                  // Emoji overlay
                  Positioned(
                    right: 20,
                    top: 20,
                    child: Text(
                      data.emoji,
                      style: const TextStyle(fontSize: 32),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 48),

          // ── Title ─────────────────────────────────────────────────
          Text(
            data.title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.w800,
              height: 1.2,
              letterSpacing: 0.3,
            ),
          ),

          const SizedBox(height: 20),

          // ── Description ───────────────────────────────────────────
          Text(
            data.description,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.82),
              fontSize: 15,
              height: 1.6,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Bottom Bar — Next / Get Started Button
  // ──────────────────────────────────────────────────────────────────
  Widget _buildBottomBar(_OnboardingPageData data) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 8),
      child: Column(
        children: [
          // ── Main Action Button ─────────────────────────────────────
          SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton(
              onPressed: _nextPage,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: data.bgColor,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _isLastPage ? 'Get Started' : 'Next',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: data.bgColor,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    _isLastPage
                        ? Icons.arrow_forward_rounded
                        : Icons.chevron_right_rounded,
                    color: data.bgColor,
                    size: 22,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
