// ╔══════════════════════════════════════════════════════════════════╗
// ║              CHANGE PASSWORD SCREEN                              ║
// ║  Pehli baar login par naya password set karo                     ║
// ║  mustChangePassword == true hone par dikhta hai                  ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../providers/auth_provider.dart';

// ════════════════════════════════════════════════════════════════════
//
//  Flow:
//    Login (mustChangePassword = true)
//      → ChangePasswordScreen
//        → Current password (from email)
//        → New password (choose your own)
//        → Confirm new password
//        → "Set Password" click
//          → AuthProvider.changePassword()
//            → Success: Dashboard
//            → Error: error message
//
// ════════════════════════════════════════════════════════════════════

/// Pehli login ke baad mandatory password change screen.
///
/// Password requirements:
///   ✅ 8+ characters
///   ✅ New ≠ Current
///   ✅ Confirm == New
class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  ConsumerState<ChangePasswordScreen> createState() =>
      _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen>
    with SingleTickerProviderStateMixin {
  // ── Form key ─────────────────────────────────────────────────────
  final _formKey = GlobalKey<FormState>();

  // ── Controllers ──────────────────────────────────────────────────
  final _currentPassController = TextEditingController();
  final _newPassController = TextEditingController();
  final _confirmPassController = TextEditingController();

  // ── Visibility toggles ────────────────────────────────────────────
  bool _currentVisible = false;
  bool _newVisible = false;
  bool _confirmVisible = false;

  // ── Password strength ─────────────────────────────────────────────
  double _passwordStrength = 0.0;
  String _strengthLabel = '';
  Color _strengthColor = AppColors.error;

  // ── Entry animation ───────────────────────────────────────────────
  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnim = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeIn),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.15),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeOutCubic),
    );
    _animController.forward();
  }

  @override
  void dispose() {
    _currentPassController.dispose();
    _newPassController.dispose();
    _confirmPassController.dispose();
    _animController.dispose();
    super.dispose();
  }

  // ══════════════════════════════════════════════════════════════════
  //  Password Strength Calculator
  // ══════════════════════════════════════════════════════════════════

  /// Password strength calculate karo (0.0 to 1.0)
  void _updatePasswordStrength(String value) {
    double strength = 0.0;

    if (value.length >= 8) strength += 0.25;
    if (value.length >= 12) strength += 0.15;
    if (value.contains(RegExp(r'[A-Z]'))) strength += 0.2;
    if (value.contains(RegExp(r'[a-z]'))) strength += 0.1;
    if (value.contains(RegExp(r'[0-9]'))) strength += 0.2;
    if (value.contains(RegExp(r'[!@#$%^&*(),.?":{}|<>]'))) strength += 0.1;

    strength = strength.clamp(0.0, 1.0);

    String label;
    Color color;
    if (strength < 0.35) {
      label = 'Weak';
      color = AppColors.error;
    } else if (strength < 0.65) {
      label = 'Fair';
      color = AppColors.warning;
    } else if (strength < 0.85) {
      label = 'Good';
      color = AppColors.info;
    } else {
      label = 'Strong ✓';
      color = AppColors.success;
    }

    setState(() {
      _passwordStrength = strength;
      _strengthLabel = label;
      _strengthColor = color;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  //  Submit — Password Change
  // ══════════════════════════════════════════════════════════════════
  Future<void> _onSetPassword() async {
    if (!_formKey.currentState!.validate()) return;

    await ref.read(authProvider.notifier).changePassword(
          currentPassword: _currentPassController.text,
          newPassword: _newPassController.text,
        );
    // Navigation auth state listener handle karega
  }

  // ══════════════════════════════════════════════════════════════════
  //  Auth State Listener
  // ══════════════════════════════════════════════════════════════════
  void _handleAuthState(AuthState? prev, AuthState next) {
    // mustChangePassword false ho gaya → Dashboard par jao
    if (prev?.mustChangePassword == true && !next.mustChangePassword) {
      context.go(AppConstants.routeDashboardHome);
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  Build
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
            colors: [
              Color(0xFF1D3A6B),
              Color(0xFF2E5BA8),
            ],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: FadeTransition(
              opacity: _fadeAnim,
              child: SlideTransition(
                position: _slideAnim,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 32),

                    // ── Header ────────────────────────────────────────
                    _buildHeader(),

                    const SizedBox(height: 32),

                    // ── Form Card ─────────────────────────────────────
                    _buildFormCard(authState),

                    const SizedBox(height: 24),

                    // ── Security Tips ─────────────────────────────────
                    _buildSecurityTips(),

                    const SizedBox(height: 32),
                  ],
                ),
              ),
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Lock icon
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
            Icons.lock_reset_rounded,
            color: Colors.white,
            size: 28,
          ),
        ),
        const SizedBox(height: 20),
        const Text(
          'Secure Your\nAccount 🔐',
          style: TextStyle(
            color: Colors.white,
            fontSize: 30,
            fontWeight: FontWeight.w800,
            height: 1.2,
            letterSpacing: 0.3,
          ),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.warning.withOpacity(0.2),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: AppColors.warning.withOpacity(0.5),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.warning_amber_rounded,
                  color: AppColors.warning, size: 16),
              const SizedBox(width: 8),
              Text(
                'Pehle email ka password use karo, phir naya set karo',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.9),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Form Card
  // ──────────────────────────────────────────────────────────────────
  Widget _buildFormCard(AuthState authState) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.15),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.all(28),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Set New Password',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AppColors.onBackground,
              ),
            ),

            const SizedBox(height: 24),

            // ── Current Password ──────────────────────────────────────
            _buildLabel('Current Password (from email)'),
            const SizedBox(height: 8),
            _buildPasswordField(
              controller: _currentPassController,
              hint: 'Email par jo password aaya tha',
              isVisible: _currentVisible,
              onToggle: () =>
                  setState(() => _currentVisible = !_currentVisible),
              validator: (v) {
                if (v == null || v.isEmpty) {
                  return 'Current password enter karo';
                }
                return null;
              },
            ),

            const SizedBox(height: 20),

            // ── New Password ──────────────────────────────────────────
            _buildLabel('New Password'),
            const SizedBox(height: 8),
            _buildPasswordField(
              controller: _newPassController,
              hint: 'Strong password choose karo',
              isVisible: _newVisible,
              onToggle: () => setState(() => _newVisible = !_newVisible),
              onChanged: _updatePasswordStrength,
              validator: (v) {
                if (v == null || v.isEmpty) return 'New password enter karo';
                if (v.length < 8) return '8+ characters hone chahiye';
                if (v == _currentPassController.text) {
                  return 'New password alag hona chahiye';
                }
                return null;
              },
            ),

            // Password strength bar
            if (_newPassController.text.isNotEmpty) ...[
              const SizedBox(height: 10),
              _buildStrengthBar(),
            ],

            const SizedBox(height: 20),

            // ── Confirm Password ──────────────────────────────────────
            _buildLabel('Confirm New Password'),
            const SizedBox(height: 8),
            _buildPasswordField(
              controller: _confirmPassController,
              hint: 'New password dobara enter karo',
              isVisible: _confirmVisible,
              onToggle: () =>
                  setState(() => _confirmVisible = !_confirmVisible),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _onSetPassword(),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Confirm password enter karo';
                if (v != _newPassController.text) {
                  return 'Passwords match nahi karte';
                }
                return null;
              },
            ),

            // ── Error ─────────────────────────────────────────────────
            if (authState.error != null) ...[
              const SizedBox(height: 16),
              _buildErrorBanner(authState.error!),
            ],

            const SizedBox(height: 28),

            // ── Submit Button ─────────────────────────────────────────
            _buildSubmitButton(authState.isLoading),
          ],
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Label Widget
  // ──────────────────────────────────────────────────────────────────
  Widget _buildLabel(String text) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.onBackground,
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Password Field Widget
  // ──────────────────────────────────────────────────────────────────
  Widget _buildPasswordField({
    required TextEditingController controller,
    required String hint,
    required bool isVisible,
    required VoidCallback onToggle,
    String? Function(String?)? validator,
    void Function(String)? onChanged,
    void Function(String)? onSubmitted,
    TextInputAction textInputAction = TextInputAction.next,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: !isVisible,
      keyboardType: TextInputType.visiblePassword,
      textInputAction: textInputAction,
      onChanged: onChanged,
      onFieldSubmitted: onSubmitted,
      validator: validator,
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: const Icon(Icons.lock_outline_rounded),
        suffixIcon: IconButton(
          icon: Icon(
            isVisible
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
          ),
          onPressed: onToggle,
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Password Strength Bar
  // ──────────────────────────────────────────────────────────────────
  Widget _buildStrengthBar() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: _passwordStrength,
            backgroundColor: AppColors.divider,
            valueColor: AlwaysStoppedAnimation<Color>(_strengthColor),
            minHeight: 6,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Password Strength: $_strengthLabel',
          style: TextStyle(
            fontSize: 12,
            color: _strengthColor,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Error Banner
  // ──────────────────────────────────────────────────────────────────
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

  // ──────────────────────────────────────────────────────────────────
  //  Submit Button
  // ──────────────────────────────────────────────────────────────────
  Widget _buildSubmitButton(bool isLoading) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: ElevatedButton(
        onPressed: isLoading ? null : _onSetPassword,
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF1D3A6B),
        ),
        child: isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  color: Colors.white,
                  strokeWidth: 2.5,
                ),
              )
            : const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_outline_rounded, size: 20),
                  SizedBox(width: 10),
                  Text(
                    'Set Password',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────
  //  Security Tips Card
  // ──────────────────────────────────────────────────────────────────
  Widget _buildSecurityTips() {
    const tips = [
      ('8+ characters use karo', Icons.check_circle_outline_rounded),
      ('Uppercase + lowercase mix karo', Icons.check_circle_outline_rounded),
      ('Numbers add karo (123)', Icons.check_circle_outline_rounded),
      ('Special characters (!@#\$)', Icons.check_circle_outline_rounded),
    ];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.tips_and_updates_rounded,
                  color: AppColors.accent, size: 18),
              const SizedBox(width: 8),
              Text(
                'Strong Password Tips',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.9),
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...tips.map((tip) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Icon(tip.$2,
                        color: AppColors.success.withOpacity(0.8), size: 16),
                    const SizedBox(width: 8),
                    Text(
                      tip.$1,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.75),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
