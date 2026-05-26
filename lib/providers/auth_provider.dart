// ╔══════════════════════════════════════════════════════════════════╗
// ║              AUTH PROVIDER — RIVERPOD STATE MANAGEMENT           ║
// ║  Authentication ka poora state yahan manage hota hai            ║
// ║  UI → Provider → ApiService → Backend                           ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../core/router.dart'; // AppAuthNotifier ke liye

// ════════════════════════════════════════════════════════════════════
//  AuthState — State ka structure
//  Har woh cheez jo LoginScreen ko dikhaai de sakti hai
// ════════════════════════════════════════════════════════════════════

/// Authentication ka poora state ek jagah par.
///
/// UI sirf yeh state read karta hai — seedha ApiService nahi bulata.
///
/// State changes flow:
///   Login button press → isLoading = true → API call →
///     Success: isAuthenticated = true, isLoading = false
///     Error:   error = message, isLoading = false
class AuthState {
  // ── Fields ──────────────────────────────────────────────────────
  final bool isLoading;          // API call chal raha hai? (spinner)
  final String? error;           // Koi error aaya? (message)
  final bool isAuthenticated;    // User logged in hai?
  final String? userRole;        // "student" / "instructor"
  final bool mustChangePassword; // Pehli baar login? Password change karna hai?
  final String? userName;        // User ka naam (dashboard mein dikhane ke liye)

  // ── Constructor ─────────────────────────────────────────────────
  const AuthState({
    this.isLoading = false,
    this.error,
    this.isAuthenticated = false,
    this.userRole,
    this.mustChangePassword = false,
    this.userName,
  });

  // ── copyWith — ek field badlo, baaki same rakho ─────────────────
  // Flutter mein state immutable (unchangeable) hoti hai
  // Isliye naya object banate hain changed fields ke saath
  AuthState copyWith({
    bool? isLoading,
    String? error,
    bool? isAuthenticated,
    String? userRole,
    bool? mustChangePassword,
    String? userName,
  }) {
    return AuthState(
      isLoading:          isLoading          ?? this.isLoading,
      error:              error,             // null allowed (error clear karne ke liye)
      isAuthenticated:    isAuthenticated    ?? this.isAuthenticated,
      userRole:           userRole           ?? this.userRole,
      mustChangePassword: mustChangePassword ?? this.mustChangePassword,
      userName:           userName           ?? this.userName,
    );
  }

  @override
  String toString() =>
      'AuthState(loading: $isLoading, auth: $isAuthenticated, '
      'role: $userRole, mustChange: $mustChangePassword)';
}

// ════════════════════════════════════════════════════════════════════
//  AuthNotifier — State ko badalne ka tarika (methods)
//  StateNotifier: state ko update karne ki class
// ════════════════════════════════════════════════════════════════════

/// Authentication actions handle karta hai.
///
/// Methods:
///   sendPassword() → email par password bhejo
///   login()        → JWT token lao, save karo
///   changePassword() → naya password set karo
///   logout()       → token delete, state reset
///   checkAuth()    → Splash mein token check karo
class AuthNotifier extends StateNotifier<AuthState> {
  // ── Dependencies inject karo ─────────────────────────────────────
  final ApiService _api;
  final StorageService _storage;

  // initial state = AuthState() → sab kuch default/empty
  AuthNotifier({ApiService? api, StorageService? storage})
      : _api = api ?? ApiService(),
        _storage = storage ?? StorageService(),
        super(const AuthState());

  // ══════════════════════════════════════════════════════════════════
  //  OTP ONBOARDING METHODS
  // ══════════════════════════════════════════════════════════════════

  /// Email verify karne ke liye backend se OTP request karo.
  Future<bool> sendOtp(String email) async {
    state = state.copyWith(isLoading: true);
    try {
      await _api.sendOtp(email);
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _parseError(e),
      );
      return false;
    }
  }

  /// Input kiya hua OTP verify karo.
  Future<bool> verifyOtp(String email, String otp) async {
    state = state.copyWith(isLoading: true);
    try {
      await _api.verifyOtp(email, otp);
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _parseError(e),
      );
      return false;
    }
  }

  /// OTP validation ke baad new password set karo.
  Future<bool> setupPassword({
    required String email,
    required String otp,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      await _api.setupPassword(
        email: email,
        otp: otp,
        password: password,
      );
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _parseError(e),
      );
      return false;
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 2: login
  //  Email + password se actual login karo
  // ══════════════════════════════════════════════════════════════════

  /// Login karo — JWT token generate hoga, local mein save hoga.
  ///
  /// [email]    — Student ka email
  /// [password] — Email par aaya hua temporary password
  ///
  /// State changes:
  ///   Loading: isLoading = true
  ///   Success: isAuthenticated = true, userRole set, token saved
  ///   Error:   error = message
  Future<void> login(String email, String password) async {
    // ── Loading shuru karo ───────────────────────────────────────────
    state = state.copyWith(isLoading: true);

    try {
      // ── Step 1: API se login response lo ─────────────────────────
      final loginResponse = await _api.login(email, password);

      // ── Step 2: Token ko encrypted storage mein save karo ────────
      await _storage.saveToken(loginResponse.accessToken);

      // ── Step 3: Role aur naam bhi save karo ──────────────────────
      await _storage.saveUserRole(loginResponse.role);
      await _storage.saveUserName(loginResponse.fullName);

      // ── Step 4: State update karo — UI rebuild hoga ──────────────
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        userRole: loginResponse.role,
        mustChangePassword: loginResponse.mustChangePassword,
        userName: loginResponse.fullName,
      );
    } catch (e) {
      // ── Error — state mein save karo ─────────────────────────────
      state = state.copyWith(
        isLoading: false,
        error: _parseError(e),
      );
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 3: changePassword
  //  Pehli login par naya password set karo
  // ══════════════════════════════════════════════════════════════════

  /// Current password verify karo, naya password set karo.
  ///
  /// [currentPassword] — Email par aaya hua purana password
  /// [newPassword]     — Student ka naya chosen password
  ///
  /// State changes:
  ///   Loading: isLoading = true
  ///   Success: mustChangePassword = false (Dashboard par ja sako)
  ///   Error:   error = message
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
      // ── Backend ko request bhejo ──────────────────────────────────
      await _api.changePassword(
        currentPassword: currentPassword,
        newPassword: newPassword,
      );

      // ── Success: ab password change required nahi ─────────────────
      state = state.copyWith(
        isLoading: false,
        mustChangePassword: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _parseError(e),
      );
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 4: logout
  //  Token delete karo, sab clear karo
  // ══════════════════════════════════════════════════════════════════

  /// Complete logout — token delete, state reset.
  ///
  /// Iske baad:
  ///   → StorageService mein koi token nahi
  ///   → AuthState fresh/empty ho jayega
  ///   → Router login screen par redirect karega
  Future<void> logout() async {
    // ── Storage se token aur sab kuch delete karo ────────────────────
    await _storage.clearAll();

    // ── State reset — sab default values par ─────────────────────────
    state = const AuthState();
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 5: checkAuth
  //  Splash screen mein token exist karta hai check karo
  // ══════════════════════════════════════════════════════════════════

  /// Phone mein stored token check karo.
  ///
  /// Kab use karo: App launch hone par (Splash screen mein)
  ///
  /// Result:
  ///   Token mila → isAuthenticated = true → Dashboard
  ///   No token   → isAuthenticated = false → Login
  Future<void> checkAuth() async {
    final hasToken = await _storage.hasToken();

    if (hasToken) {
      // ── Token mila — user logged in hai ──────────────────────────
      final role = await _storage.getUserRole();
      final name = await _storage.getUserName();
      // GoRouter ko batao ke user logged in hai (synchronous redirect ke liye)
      AppAuthNotifier.instance.setLoggedIn(true);
      state = state.copyWith(
        isAuthenticated: true,
        userRole: role,
        userName: name,
      );
    } else {
      // ── Token nahi — user ko login karna hoga ────────────────────
      AppAuthNotifier.instance.setLoggedIn(false);
      state = state.copyWith(isAuthenticated: false);
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  HELPER: Error message parse karo
  // ══════════════════════════════════════════════════════════════════

  /// Exception se user-friendly string nikalo.
  String _parseError(Object e) {
    final msg = e.toString();
    // "Exception: ..." format se sirf message lo
    if (msg.startsWith('Exception: ')) {
      return msg.replaceFirst('Exception: ', '');
    }
    return msg;
  }

  // ══════════════════════════════════════════════════════════════════
  //  clearError — Error dismiss karo (user ne X press kiya)
  // ══════════════════════════════════════════════════════════════════

  /// Error message clear karo.
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// ════════════════════════════════════════════════════════════════════
//  PROVIDER — Global access point
//  Koi bhi widget ref.watch(authProvider) se state sun sakta hai
// ════════════════════════════════════════════════════════════════════

/// Auth provider — poori app mein access hota hai.
///
/// Usage (kisi bhi widget mein):
/// ```dart
///   // State padhna:
///   final authState = ref.watch(authProvider);
///
///   // Method call karna:
///   ref.read(authProvider.notifier).login(email, password);
/// ```
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);
