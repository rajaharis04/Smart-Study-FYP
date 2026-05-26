// ╔══════════════════════════════════════════════════════════════════╗
// ║              LOGIN SCREEN — 2 MODES                              ║
// ║  Mode 1 (Default): Direct login — email + password + Login       ║
// ║  Mode 2 (First Time): 2-step — email → Send Password → Login     ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';

// ════════════════════════════════════════════════════════════════════
//
//  Flow A — Get Started (returning user):
//    Email field + Password field → Login button
//      → AuthProvider.login()
//        → Dashboard ya ChangePassword
//
//  Flow B — First Time Login:
//    Step 1: Email field → "Send Password" button
//      → Backend email par password bhejta hai
//    Step 2: Password field → "Login" button
//      → Dashboard ya ChangePassword
//
// ════════════════════════════════════════════════════════════════════

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with TickerProviderStateMixin {
  // ── Form ─────────────────────────────────────────────────────────
  final _formKey = GlobalKey<FormState>();
  final _emailController    = TextEditingController();
  final _passwordController = TextEditingController();
  final _otpController      = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  // ── UI State ──────────────────────────────────────────────────────
  bool _isFirstTimeMode = false; // false = direct login | true = multi-step wizard
  int _firstTimeStep    = 0;     // 0 = email check, 1 = success animation, 2 = OTP check, 3 = setup password
  bool _passwordVisible = false;
  bool _confirmPasswordVisible = false;

  // ── Slide animation (mode switch ke liye) ─────────────────────────
  late AnimationController _slideCtrl;
  late Animation<Offset>   _slideAnim;
  late Animation<double>   _fadeAnim;

  @override
  void initState() {
    super.initState();
    _slideCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 450),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.25),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideCtrl, curve: Curves.easeOutCubic));
    _fadeAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _slideCtrl, curve: Curves.easeIn),
    );
    _slideCtrl.forward();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _otpController.dispose();
    _confirmPasswordController.dispose();
    _slideCtrl.dispose();
    super.dispose();
  }

  // ══════════════════════════════════════════════════════════════════
  //  Switch Mode
  // ══════════════════════════════════════════════════════════════════

  /// "First time login?" card press → OTP wizard step 0
  void _switchToFirstTime() {
    setState(() {
      _isFirstTimeMode = true;
      _firstTimeStep    = 0;
      _emailController.clear();
      _passwordController.clear();
      _otpController.clear();
      _confirmPasswordController.clear();
    });
    ref.read(authProvider.notifier).clearError();
    _slideCtrl.reset();
    _slideCtrl.forward();
  }

  /// "← Back to login" → Direct login mode
  void _switchToDirectLogin() {
    setState(() {
      _isFirstTimeMode = false;
      _firstTimeStep    = 0;
      _emailController.clear();
      _passwordController.clear();
      _otpController.clear();
      _confirmPasswordController.clear();
    });
    ref.read(authProvider.notifier).clearError();
    _slideCtrl.reset();
    _slideCtrl.forward();
  }

  // ══════════════════════════════════════════════════════════════════
  //  ACTION A: Direct Login (Mode 1)
  // ══════════════════════════════════════════════════════════════════

  Future<void> _onDirectLogin() async {
    if (!_formKey.currentState!.validate()) return;
    await ref.read(authProvider.notifier).login(
          _emailController.text.trim(),
          _passwordController.text,
        );
  }

  // ══════════════════════════════════════════════════════════════════
  //  ACTION B1: Send OTP (Step 0)
  // ══════════════════════════════════════════════════════════════════

  Future<void> _onSendOtp() async {
    if (!_formKey.currentState!.validate()) return;
    final email = _emailController.text.trim();
    final success = await ref.read(authProvider.notifier).sendOtp(email);
    if (success && mounted) {
      setState(() => _firstTimeStep = 1);
      _slideCtrl.reset();
      _slideCtrl.forward();

      // Pulse screen for 2.5s, then auto-navigate to OTP entry screen
      Future.delayed(const Duration(milliseconds: 2500), () {
        if (mounted && _firstTimeStep == 1) {
          setState(() => _firstTimeStep = 2);
          _slideCtrl.reset();
          _slideCtrl.forward();
        }
      });
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  ACTION B2: Verify OTP (Step 2)
  // ══════════════════════════════════════════════════════════════════

  Future<void> _onVerifyOtp() async {
    if (!_formKey.currentState!.validate()) return;
    final email = _emailController.text.trim();
    final otp = _otpController.text.trim();
    final success = await ref.read(authProvider.notifier).verifyOtp(email, otp);
    if (success && mounted) {
      setState(() => _firstTimeStep = 3);
      _slideCtrl.reset();
      _slideCtrl.forward();
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  ACTION B3: Set Password & Log In (Step 3)
  // ══════════════════════════════════════════════════════════════════

  Future<void> _onSetupPassword() async {
    if (!_formKey.currentState!.validate()) return;
    final email = _emailController.text.trim();
    final otp = _otpController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (password != confirmPassword) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Passwords do not match!'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }

    final success = await ref.read(authProvider.notifier).setupPassword(
          email: email,
          otp: otp,
          password: password,
        );

    if (success && mounted) {
      // Immediately log in using the newly set password
      await ref.read(authProvider.notifier).login(email, password);
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  Auth State Listener — Navigation
  // ══════════════════════════════════════════════════════════════════

  void _handleAuthState(AuthState? prev, AuthState next) {
    if (!next.isAuthenticated) return;
    if (next.mustChangePassword) {
      context.go(AppConstants.routeChangePassword);
    } else {
      context.go(AppConstants.routeDashboardHome);
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  BUILD
  // ══════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    ref.listen<AuthState>(authProvider, _handleAuthState);
    final authState = ref.watch(authProvider);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0D7A5F), Color(0xFF1D9E75)],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 40),
                _buildHeader(),
                const SizedBox(height: 32),

                // ── Animated form card ───────────────────────────────
                SlideTransition(
                  position: _slideAnim,
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: _isFirstTimeMode
                        ? _buildFirstTimeCard(authState)
                        : _buildDirectLoginCard(authState),
                  ),
                ),

                const SizedBox(height: 20),

                // ── Footer ──────────────────────────────────────────
                _buildFooter(),

                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Header
  // ──────────────────────────────────────────────────────────────────
  Widget _buildHeader() {
    final title = _isFirstTimeMode ? 'First Time Login' : 'Welcome Back!';
    String subtitle;
    if (_isFirstTimeMode) {
      if (_firstTimeStep == 0) {
        subtitle = 'Email enter karo — verification code bheja jayega';
      } else if (_firstTimeStep == 1) {
        subtitle = 'Registered profile check kiye ja rahe hain...';
      } else if (_firstTimeStep == 2) {
        subtitle = 'Apna verification OTP code enter karo';
      } else {
        subtitle = 'Apna naya login password set karo';
      }
    } else {
      subtitle = 'Email aur password enter karke login karo';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Logo
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.white.withOpacity(0.2),
            border: Border.all(
              color: Colors.white.withOpacity(0.5),
              width: 2,
            ),
          ),
          child: const Icon(
            Icons.school_rounded,
            color: Colors.white,
            size: 28,
          ),
        ),
        const SizedBox(height: 20),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: Text(
            title,
            key: ValueKey(title),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 30,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.3,
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          subtitle,
          style: TextStyle(
            color: Colors.white.withOpacity(0.82),
            fontSize: 14,
            height: 1.4,
          ),
        ),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════════
  //  CARD A — Direct Login (email + password + Login button)
  // ══════════════════════════════════════════════════════════════════
  Widget _buildDirectLoginCard(AuthState authState) {
    return _buildCard(
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title
            Row(
              children: [
                const Icon(Icons.login_rounded,
                    color: AppColors.primary, size: 22),
                const SizedBox(width: 10),
                const Text(
                  'Login to your account',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: AppColors.onBackground,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            // Email field
            _buildEmailField(enabled: true),

            const SizedBox(height: 16),

            // Password field
            _buildPasswordField(),

            // Error
            if (authState.error != null) ...[
              const SizedBox(height: 14),
              _buildErrorBanner(authState.error!),
            ],

            const SizedBox(height: 24),

            // Login button
            _buildButton(
              label: 'Login',
              icon: Icons.login_rounded,
              isLoading: authState.isLoading,
              onPressed: _onDirectLogin,
            ),
          ],
        ),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════
  //  CARD B — First Time Login (multi-step wizard card)
  // ══════════════════════════════════════════════════════════════════
  Widget _buildFirstTimeCard(AuthState authState) {
    Widget stepContent;
    String buttonLabel;
    IconData buttonIcon;
    VoidCallback buttonAction;

    if (_firstTimeStep == 0) {
      stepContent = _buildEmailField(enabled: true);
      buttonLabel = 'Verify Email';
      buttonIcon = Icons.arrow_forward_rounded;
      buttonAction = _onSendOtp;
    } else if (_firstTimeStep == 1) {
      stepContent = _buildRegisteredSuccessAnimation();
      buttonLabel = 'Processing...';
      buttonIcon = Icons.hourglass_empty;
      buttonAction = () {};
    } else if (_firstTimeStep == 2) {
      stepContent = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildOtpField(),
          const SizedBox(height: 10),
          Center(
            child: TextButton(
              onPressed: _onSendOtp,
              child: const Text(
                'Resend OTP Code',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ),
          ),
        ],
      );
      buttonLabel = 'Verify OTP';
      buttonIcon = Icons.security_rounded;
      buttonAction = _onVerifyOtp;
    } else {
      // Step 3: Setup Password
      stepContent = _buildNewPasswordFields();
      buttonLabel = 'Create Password & Login';
      buttonIcon = Icons.check_circle_rounded;
      buttonAction = _onSetupPassword;
    }

    return _buildCard(
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Step Indicator (hidden during step 1 animation)
            if (_firstTimeStep != 1) ...[
              _buildStepIndicator(),
              const SizedBox(height: 24),
            ],

            stepContent,

            // Error
            if (authState.error != null && _firstTimeStep != 1) ...[
              const SizedBox(height: 14),
              _buildErrorBanner(authState.error!),
            ],

            const SizedBox(height: 24),

            // Submit Button (hidden during step 1 animation)
            if (_firstTimeStep != 1)
              _buildButton(
                label: buttonLabel,
                icon: buttonIcon,
                isLoading: authState.isLoading,
                onPressed: buttonAction,
              ),

            // Back/Previous Navigation
            if (_firstTimeStep != 1) ...[
              const SizedBox(height: 12),
              Center(
                child: TextButton.icon(
                  onPressed: () {
                    if (_firstTimeStep == 0) {
                      _switchToDirectLogin();
                    } else if (_firstTimeStep == 2) {
                      setState(() => _firstTimeStep = 0);
                      _slideCtrl.reset();
                      _slideCtrl.forward();
                    } else if (_firstTimeStep == 3) {
                      setState(() => _firstTimeStep = 2);
                      _slideCtrl.reset();
                      _slideCtrl.forward();
                    }
                    ref.read(authProvider.notifier).clearError();
                  },
                  icon: const Icon(Icons.arrow_back_rounded, size: 16),
                  label: Text(
                    _firstTimeStep == 0 ? 'Back to Login' : 'Previous Step',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════
  //  FOOTER — "First time login? Click here" card
  // ══════════════════════════════════════════════════════════════════
  Widget _buildFooter() {
    return Column(
      children: [
        if (!_isFirstTimeMode)
          GestureDetector(
            onTap: _switchToFirstTime,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.12),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withOpacity(0.3),
                  width: 1.5,
                ),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white.withOpacity(0.2),
                    ),
                    child: const Icon(
                      Icons.person_add_alt_1_rounded,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'First time login?',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Click here to setup your password',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.75),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: Colors.white.withOpacity(0.7),
                    size: 22,
                  ),
                ],
              ),
            ),
          ),

        const SizedBox(height: 14),

        // Copyright
        Text(
          'SmartStudy Instructeer © 2026  🔒',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withOpacity(0.45),
            fontSize: 11,
          ),
        ),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════════
  //  SHARED WIDGETS
  // ══════════════════════════════════════════════════════════════════

  // White card container
  Widget _buildCard({required Widget child}) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.14),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.all(28),
      child: child,
    );
  }

  // Wizard Step Indicator dots
  Widget _buildStepIndicator() {
    return Row(
      children: [
        _buildStepDot(
          number: '1',
          label: 'Email',
          isActive: _firstTimeStep <= 1,
          isDone: _firstTimeStep > 1,
        ),
        Expanded(
          child: Container(
            height: 2,
            margin: const EdgeInsets.symmetric(horizontal: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(1),
              color: _firstTimeStep > 1 ? AppColors.success : AppColors.divider,
            ),
          ),
        ),
        _buildStepDot(
          number: '2',
          label: 'OTP',
          isActive: _firstTimeStep == 2,
          isDone: _firstTimeStep > 2,
        ),
        Expanded(
          child: Container(
            height: 2,
            margin: const EdgeInsets.symmetric(horizontal: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(1),
              color: _firstTimeStep > 2 ? AppColors.success : AppColors.divider,
            ),
          ),
        ),
        _buildStepDot(
          number: '3',
          label: 'Password',
          isActive: _firstTimeStep == 3,
          isDone: false,
        ),
      ],
    );
  }

  Widget _buildStepDot({
    required String number,
    required String label,
    required bool isActive,
    required bool isDone,
  }) {
    final Color color = isDone
        ? AppColors.success
        : isActive
            ? AppColors.primary
            : AppColors.divider;

    final Widget inner = isDone
        ? const Icon(Icons.check_rounded, color: Colors.white, size: 16)
        : Text(
            number,
            style: TextStyle(
              color: isActive ? Colors.white : AppColors.textHint,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          );

    return Column(
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: 32,
          height: 32,
          decoration: BoxDecoration(shape: BoxShape.circle, color: color),
          child: Center(child: inner),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: isActive || isDone ? AppColors.onBackground : AppColors.textHint,
          ),
        ),
      ],
    );
  }

  // Animation checkmark scale transition for step 1
  Widget _buildRegisteredSuccessAnimation() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 20),
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.0, end: 1.0),
            duration: const Duration(milliseconds: 700),
            curve: Curves.elasticOut,
            builder: (context, val, child) {
              return Transform.scale(
                scale: val,
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: const BoxDecoration(
                    color: Color(0xFFE8F5E9),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check_circle_rounded,
                    color: Colors.green,
                    size: 64,
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 24),
          const Text(
            'Your email is registered!',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: Colors.green,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Generating and sending OTP code...',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // Email Field
  Widget _buildEmailField({required bool enabled}) {
    return TextFormField(
      controller: _emailController,
      enabled: enabled,
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: 'Email Address',
        hintText: 'ali@std.comsats.edu.pk',
        prefixIcon: const Icon(Icons.email_outlined),
        suffixIcon: (!enabled)
            ? const Icon(Icons.check_circle_rounded, color: AppColors.success)
            : null,
        fillColor: (!enabled)
            ? const Color(0xFFF5F5F5)
            : AppColors.surface,
      ),
      validator: (v) {
        if (v == null || v.trim().isEmpty) return 'Email zaroor enter karo';
        if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(v)) {
          return 'Valid email enter karo';
        }
        return null;
      },
    );
  }

  // OTP Field
  Widget _buildOtpField() {
    return TextFormField(
      controller: _otpController,
      keyboardType: TextInputType.number,
      maxLength: 6,
      textInputAction: TextInputAction.done,
      decoration: const InputDecoration(
        labelText: 'Enter OTP Code',
        hintText: '123456',
        prefixIcon: Icon(Icons.security_rounded),
        counterText: '',
      ),
      validator: (v) {
        if (v == null || v.trim().isEmpty) return 'OTP enter karo';
        if (v.trim().length < 6) return 'OTP 6 digits ka hona chahiye';
        return null;
      },
    );
  }

  // New Password input fields
  Widget _buildNewPasswordFields() {
    return Column(
      children: [
        TextFormField(
          controller: _passwordController,
          obscureText: !_passwordVisible,
          decoration: InputDecoration(
            labelText: 'New Password',
            hintText: 'Minimum 8 characters',
            prefixIcon: const Icon(Icons.lock_outline_rounded),
            suffixIcon: IconButton(
              icon: Icon(
                _passwordVisible
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
              ),
              onPressed: () => setState(() => _passwordVisible = !_passwordVisible),
            ),
          ),
          validator: (v) {
            if (v == null || v.isEmpty) return 'Password enter karo';
            if (v.length < 8) return 'Password key length minimum 8 chars honi chahiye';
            return null;
          },
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _confirmPasswordController,
          obscureText: !_confirmPasswordVisible,
          decoration: InputDecoration(
            labelText: 'Confirm Password',
            hintText: 'Apna password dobara likhain',
            prefixIcon: const Icon(Icons.lock_outline_rounded),
            suffixIcon: IconButton(
              icon: Icon(
                _confirmPasswordVisible
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
              ),
              onPressed: () => setState(() => _confirmPasswordVisible = !_confirmPasswordVisible),
            ),
          ),
          validator: (v) {
            if (v == null || v.isEmpty) return 'Password verify karo';
            if (v != _passwordController.text) return 'Passwords match nahi kar rahe';
            return null;
          },
        ),
      ],
    );
  }

  // Password Input for Direct Login
  Widget _buildPasswordField() {
    return TextFormField(
      controller: _passwordController,
      obscureText: !_passwordVisible,
      keyboardType: TextInputType.visiblePassword,
      textInputAction: TextInputAction.done,
      onFieldSubmitted: (_) => _onDirectLogin(),
      decoration: InputDecoration(
        labelText: 'Password',
        hintText: 'Apna password enter karo',
        prefixIcon: const Icon(Icons.lock_outline_rounded),
        suffixIcon: IconButton(
          icon: Icon(
            _passwordVisible
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
          ),
          onPressed: () =>
              setState(() => _passwordVisible = !_passwordVisible),
        ),
      ),
      validator: (v) {
        if (v == null || v.isEmpty) return 'Password zaroor enter karo';
        return null;
      },
    );
  }



  // Error banner
  Widget _buildErrorBanner(String error) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded,
              color: AppColors.error, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              error,
              style: const TextStyle(
                color: AppColors.error,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
          GestureDetector(
            onTap: () => ref.read(authProvider.notifier).clearError(),
            child: const Icon(Icons.close_rounded,
                color: AppColors.error, size: 18),
          ),
        ],
      ),
    );
  }

  // Primary action button
  Widget _buildButton({
    required String label,
    required IconData icon,
    required bool isLoading,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        child: isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  color: Colors.white,
                  strokeWidth: 2.5,
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 20),
                  const SizedBox(width: 10),
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
