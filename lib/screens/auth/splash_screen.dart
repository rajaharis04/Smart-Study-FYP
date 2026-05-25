// ╔══════════════════════════════════════════════════════════════════╗
// ║              SPLASH SCREEN                                       ║
// ║  App open hone par pehla screen                                  ║
// ║  Logo + animation + JWT check + auto-navigate                    ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../providers/auth_provider.dart';

// ════════════════════════════════════════════════════════════════════
//
//  SplashScreen Flow:
//
//  App open ho →
//    Animation shuru ho (logo bounce + fade in) →
//      2.5 second wait →
//        AuthProvider.checkAuth() call →
//          Token mila? → Dashboard
//          No token?   → Onboarding (pehli baar) ya Login
//
// ════════════════════════════════════════════════════════════════════

/// App ka first screen — animated logo + auth check.
///
/// ConsumerStatefulWidget use karta hai — Riverpod + animation dono
/// ke liye state chahiye.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with TickerProviderStateMixin {
  // ── Animation Controllers ─────────────────────────────────────────
  late AnimationController _logoController;    // Logo ke liye
  late AnimationController _textController;    // Text ke liye
  late AnimationController _pulseController;   // Shimmer/pulse ke liye

  // ── Animations ───────────────────────────────────────────────────
  late Animation<double> _logoScale;      // Scale: 0.0 → 1.0
  late Animation<double> _logoOpacity;    // Opacity: 0.0 → 1.0
  late Animation<Offset> _textSlide;      // Slide: upar se neeche
  late Animation<double> _textOpacity;    // Text opacity
  late Animation<double> _pulseScale;     // Pulse effect

  // ── State ─────────────────────────────────────────────────────────
  bool _navigationDone = false;

  @override
  void initState() {
    super.initState();
    _setupAnimations();
    _startFlow();
  }

  // ══════════════════════════════════════════════════════════════════
  //  Animation Setup
  // ══════════════════════════════════════════════════════════════════
  void _setupAnimations() {
    // ── Logo Controller (800ms) ──────────────────────────────────────
    _logoController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    // Logo scale — 0.3 se 1.0 tak (elastic bounce)
    _logoScale = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.elasticOut),
    );

    // Logo opacity — 0.0 se 1.0 tak
    _logoOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.easeIn),
    );

    // ── Text Controller (600ms, delay ke baad) ──────────────────────
    _textController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );

    // Text upar se slide in karo
    _textSlide = Tween<Offset>(
      begin: const Offset(0, 0.5), // Neeche se
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _textController, curve: Curves.easeOutCubic),
    );

    _textOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _textController, curve: Curves.easeIn),
    );

    // ── Pulse Controller (1.5s, repeat) ─────────────────────────────
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _pulseScale = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _pulseController.repeat(reverse: true); // Back aur forth
  }

  // ══════════════════════════════════════════════════════════════════
  //  Main Flow — Animations + Auth Check + Navigate
  // ══════════════════════════════════════════════════════════════════
  Future<void> _startFlow() async {
    // ── Step 1: Logo animation shuru karo ───────────────────────────
    await _logoController.forward();

    // ── Step 2: Text animation (200ms delay ke baad) ─────────────────
    await Future.delayed(const Duration(milliseconds: 200));
    await _textController.forward();

    // ── Step 3: Thoda wait karo (user ko logo dikhe) ─────────────────
    await Future.delayed(const Duration(milliseconds: 1500));

    // ── Step 4: Auth check (token hai ya nahi?) ───────────────────────
    await ref.read(authProvider.notifier).checkAuth();

    // ── Step 5: Navigate karo ─────────────────────────────────────────
    if (mounted && !_navigationDone) {
      _navigationDone = true;
      final authState = ref.read(authProvider);

      if (authState.isAuthenticated) {
        // Token mila — seedha Dashboard
        context.go(AppConstants.routeDashboard);
      } else {
        // Pehli baar? Onboarding dikhao | Warna Login
        context.go(AppConstants.routeOnboarding);
      }
    }
  }

  @override
  void dispose() {
    // ── Controllers dispose karo — memory leak se bachao ─────────────
    _logoController.dispose();
    _textController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  // ══════════════════════════════════════════════════════════════════
  //  UI Build
  // ══════════════════════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Container(
        // ── Gradient background ─────────────────────────────────────
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF0D7A5F), // Deep teal
              Color(0xFF1D9E75), // Brand primary
              Color(0xFF2DC08A), // Light teal
            ],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // ── Top space ─────────────────────────────────────────
              SizedBox(height: size.height * 0.15),

              // ── Logo Section ──────────────────────────────────────
              AnimatedBuilder(
                animation: Listenable.merge([_logoController, _pulseController]),
                builder: (context, child) {
                  return Opacity(
                    opacity: _logoOpacity.value,
                    child: Transform.scale(
                      scale: _logoScale.value * _pulseScale.value,
                      child: child,
                    ),
                  );
                },
                child: _buildLogo(),
              ),

              const SizedBox(height: 32),

              // ── App Name ─────────────────────────────────────────
              SlideTransition(
                position: _textSlide,
                child: FadeTransition(
                  opacity: _textOpacity,
                  child: _buildAppTitle(),
                ),
              ),

              const SizedBox(height: 12),

              // ── Tagline ──────────────────────────────────────────
              FadeTransition(
                opacity: _textOpacity,
                child: _buildTagline(),
              ),

              const Spacer(),

              // ── Loading indicator ─────────────────────────────────
              FadeTransition(
                opacity: _textOpacity,
                child: _buildLoadingSection(),
              ),

              SizedBox(height: size.height * 0.08),
            ],
          ),
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Logo Widget
  // ──────────────────────────────────────────────────────────────────
  Widget _buildLogo() {
    return Container(
      width: 120,
      height: 120,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white.withOpacity(0.15),
        border: Border.all(
          color: Colors.white.withOpacity(0.4),
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: const Icon(
        Icons.school_rounded,
        size: 64,
        color: Colors.white,
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  App Title
  // ──────────────────────────────────────────────────────────────────
  Widget _buildAppTitle() {
    return Column(
      children: [
        const Text(
          'SmartStudy',
          style: TextStyle(
            color: Colors.white,
            fontSize: 36,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.2),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Text(
            'INSTRUCTEER',
            style: TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: 4,
            ),
          ),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Tagline
  // ──────────────────────────────────────────────────────────────────
  Widget _buildTagline() {
    return Text(
      'Your intelligent learning companion',
      style: TextStyle(
        color: Colors.white.withOpacity(0.8),
        fontSize: 15,
        fontWeight: FontWeight.w400,
        letterSpacing: 0.3,
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Loading Section
  // ──────────────────────────────────────────────────────────────────
  Widget _buildLoadingSection() {
    return Column(
      children: [
        // Dots loading animation
        _DotsLoadingIndicator(),
        const SizedBox(height: 16),
        Text(
          'Loading...',
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 13,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}

// ════════════════════════════════════════════════════════════════════
//  Animated Dots Loading Indicator
//  Teeno dots ek ek karke bounce karte hain
// ════════════════════════════════════════════════════════════════════
class _DotsLoadingIndicator extends StatefulWidget {
  @override
  State<_DotsLoadingIndicator> createState() => _DotsLoadingIndicatorState();
}

class _DotsLoadingIndicatorState extends State<_DotsLoadingIndicator>
    with TickerProviderStateMixin {
  late List<AnimationController> _controllers;
  late List<Animation<double>> _animations;

  @override
  void initState() {
    super.initState();
    // 3 dots ke liye 3 controllers
    _controllers = List.generate(3, (i) {
      return AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 600),
      );
    });

    _animations = _controllers.map((c) {
      return Tween<double>(begin: 0.0, end: -12.0).animate(
        CurvedAnimation(parent: c, curve: Curves.easeInOut),
      );
    }).toList();

    // Har dot ko 200ms delay ke saath start karo
    for (int i = 0; i < 3; i++) {
      Future.delayed(Duration(milliseconds: i * 200), () {
        if (mounted) _controllers[i].repeat(reverse: true);
      });
    }
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(3, (i) {
        return AnimatedBuilder(
          animation: _controllers[i],
          builder: (context, child) {
            return Transform.translate(
              offset: Offset(0, _animations[i].value),
              child: child,
            );
          },
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 5),
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withOpacity(0.85),
            ),
          ),
        );
      }),
    );
  }
}
