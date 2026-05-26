// ╔══════════════════════════════════════════════════════════════════╗
// ║              STORAGE SERVICE — SECURE VAULT                      ║
// ║  JWT token ko phone ke encrypted storage mein save karta hai     ║
// ║  Android: Keystore  |  iOS: Keychain                             ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:io';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../core/constants.dart';
import '../core/router.dart'; // AppAuthNotifier ke liye

/// ──────────────────────────────────────────────────────────────────
/// StorageService
/// ──────────────────────────────────────────────────────────────────
/// Yeh class phone ke encrypted storage ko access karti hai.
///
/// Kyun secure storage?
///   → JWT token bohot sensitive hota hai
///   → Normal SharedPreferences plain-text mein store karti hai
///   → flutter_secure_storage hardware-level encryption use karta hai
///
/// Usage (kaise use karein):
/// ```dart
///   final storage = StorageService();
///   await storage.saveToken('eyJhbGci...');
///   final token = await storage.getToken();
/// ```
/// ──────────────────────────────────────────────────────────────────
class StorageService {
  // Static in-memory fallback cache to allow the app to work seamlessly
  // and avoid annoying macOS Keychain password dialogs during local execution.
  static final Map<String, String> _fallbackStorage = {};

  /// Router ke liye synchronous token access — no async needed.
  /// GoRouter redirect function mein use hota hai.
  static String? get fallbackToken => _fallbackStorage[AppConstants.keyAuthToken];

  // Check if target platform is macOS desktop
  bool get _isMac => Platform.isMacOS;

  // ── Private instance — flutter_secure_storage ka object ────────────
  // Yeh Android Options aur iOS Options configure karta hai
  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    // Android: EncryptedSharedPreferences use karo (more secure)
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    // iOS: Keychain mein save karo, device unlock hone par accessible ho
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
    // macOS: File-based storage use karo (Keychain needs Apple Developer signing)
    mOptions: MacOsOptions(useDataProtectionKeyChain: false),
  );

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 1: saveToken
  //  Token ko encrypted storage mein save karo
  // ══════════════════════════════════════════════════════════════════

  /// Login ke baad backend se mila JWT token save karta hai.
  ///
  /// [token] — Backend se aaya hua JWT string
  ///           Example: "eyJhbGciOiJIUzI1NiIs..."
  ///
  /// Kab call hota hai: Login successful hone par
  Future<void> saveToken(String token) async {
    _fallbackStorage[AppConstants.keyAuthToken] = token;
    // Auth notifier ko batao — GoRouter logged-in state update karega
    AppAuthNotifier.instance.setLoggedIn(true);
    if (_isMac) {
      // macOS par dialog bypass karne ke liye local memory storage use karte hain
      return;
    }
    try {
      await _storage.write(key: AppConstants.keyAuthToken, value: token);
    } catch (e) {
      print('StorageService.saveToken error: $e');
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 2: getToken
  //  Stored token wapas lao
  // ══════════════════════════════════════════════════════════════════

  /// Encrypted storage se JWT token nikalta hai.
  ///
  /// Returns: token string — agar stored hai
  ///          null — agar koi token nahi mila (user logged out ya pehli baar)
  ///
  /// Kab call hota hai: Har API request se pehle (interceptor use karta hai)
  Future<String?> getToken() async {
    if (_isMac) {
      return _fallbackStorage[AppConstants.keyAuthToken];
    }
    try {
      return await _storage.read(key: AppConstants.keyAuthToken);
    } catch (e) {
      print('StorageService.getToken error: $e');
      return _fallbackStorage[AppConstants.keyAuthToken];
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 3: deleteToken
  //  Logout par token delete karo
  // ══════════════════════════════════════════════════════════════════

  /// Logout karte waqt JWT token ko permanently delete karta hai.
  ///
  /// Iske baad:
  ///   → getToken() null return karega
  ///   → hasToken() false return karega
  ///   → User ko login screen par redirect kiya jaega
  ///
  /// Kab call hota hai: Logout button press karne par
  Future<void> deleteToken() async {
    _fallbackStorage.remove(AppConstants.keyAuthToken);
    // Auth notifier ko batao — GoRouter redirect karega login par
    AppAuthNotifier.instance.setLoggedIn(false);
    if (_isMac) {
      return;
    }
    try {
      await _storage.delete(key: AppConstants.keyAuthToken);
    } catch (e) {
      print('StorageService.deleteToken error: $e');
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  METHOD 4: hasToken
  //  Check karo — kya phone mein token hai?
  // ══════════════════════════════════════════════════════════════════

  /// Phone mein pehle se JWT token hai ya nahi — check karta hai.
  ///
  /// Returns: true  — token mila, user logged in hai
  ///          false — token nahi mila, user ko login karna hoga
  ///
  /// Kab call hota hai: Splash screen par
  ///   → true  → Dashboard screen
  ///   → false → Login screen
  Future<bool> hasToken() async {
    // Token nikalo
    final token = await getToken();
    // null nahi hai to token hai = true
    // null hai to token nahi = false
    return token != null && token.isNotEmpty;
  }

  // ══════════════════════════════════════════════════════════════════
  //  BONUS: saveUserRole & getUserRole
  //  Role bhi store karo (student / instructor)
  // ══════════════════════════════════════════════════════════════════

  /// User role save karo (e.g., 'student', 'instructor')
  Future<void> saveUserRole(String role) async {
    _fallbackStorage['user_role'] = role;
    if (_isMac) {
      return;
    }
    try {
      await _storage.write(key: 'user_role', value: role);
    } catch (e) {
      print('StorageService.saveUserRole error: $e');
    }
  }

  /// Stored user role wapas lao
  Future<String?> getUserRole() async {
    if (_isMac) {
      return _fallbackStorage['user_role'];
    }
    try {
      return await _storage.read(key: 'user_role');
    } catch (e) {
      print('StorageService.getUserRole error: $e');
      return _fallbackStorage['user_role'];
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  BONUS: saveUserName & getUserName
  //  Full name bhi store karo
  // ══════════════════════════════════════════════════════════════════

  /// User ka full name save karo
  Future<void> saveUserName(String name) async {
    _fallbackStorage['user_name'] = name;
    if (_isMac) {
      return;
    }
    try {
      await _storage.write(key: 'user_name', value: name);
    } catch (e) {
      print('StorageService.saveUserName error: $e');
    }
  }

  /// Stored full name wapas lao
  Future<String?> getUserName() async {
    if (_isMac) {
      return _fallbackStorage['user_name'];
    }
    try {
      return await _storage.read(key: 'user_name');
    } catch (e) {
      print('StorageService.getUserName error: $e');
      return _fallbackStorage['user_name'];
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  GENERIC KEY-VALUE METHODS FOR PREFERENCES
  // ══════════════════════════════════════════════════════════════════

  /// Generic write method to save local settings preferences.
  Future<void> write(String key, String value) async {
    _fallbackStorage[key] = value;
    if (_isMac) {
      return;
    }
    try {
      await _storage.write(key: key, value: value);
    } catch (e) {
      print('StorageService.write error: $e');
    }
  }

  /// Generic read method to retrieve stored preferences.
  Future<String?> read(String key) async {
    if (_isMac) {
      return _fallbackStorage[key];
    }
    try {
      return await _storage.read(key: key);
    } catch (e) {
      print('StorageService.read error: $e');
      return _fallbackStorage[key];
    }
  }

  /// Generic delete method to remove stored preference.
  Future<void> delete(String key) async {
    _fallbackStorage.remove(key);
    if (_isMac) {
      return;
    }
    try {
      await _storage.delete(key: key);
    } catch (e) {
      print('StorageService.delete error: $e');
    }
  }

  // ══════════════════════════════════════════════════════════════════
  //  VIDEO PLAYER AUTO-RESUME CACHE
  // ══════════════════════════════════════════════════════════════════

  Future<void> saveVideoPosition(int lectureId, int seconds) async {
    await write('video_pos_$lectureId', seconds.toString());
  }

  Future<int> getVideoPosition(int lectureId) async {
    final posStr = await read('video_pos_$lectureId');
    return posStr != null ? (int.tryParse(posStr) ?? 0) : 0;
  }

  // ══════════════════════════════════════════════════════════════════
  //  Q&A DYNAMIC BOOKMARKS
  // ══════════════════════════════════════════════════════════════════

  Future<List<Map<String, dynamic>>> getBookmarkedQnAs() async {
    final raw = await read('bookmarked_qnas');
    if (raw == null) return [];
    try {
      final List<dynamic> decoded = json.decode(raw);
      return decoded.map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> toggleQnABookmark(Map<String, dynamic> qnaMap) async {
    final bookmarks = await getBookmarkedQnAs();
    final questionText = qnaMap['question'] as String;
    
    final index = bookmarks.indexWhere((b) => b['question'] == questionText);
    if (index >= 0) {
      bookmarks.removeAt(index);
    } else {
      bookmarks.add(qnaMap);
    }
    
    await write('bookmarked_qnas', json.encode(bookmarks));
  }

  Future<bool> isQnABookmarked(String questionText) async {
    final bookmarks = await getBookmarkedQnAs();
    return bookmarks.any((b) => b['question'] == questionText);
  }

  // ══════════════════════════════════════════════════════════════════
  //  NOTIFICATION HUB HISTORY
  // ══════════════════════════════════════════════════════════════════

  Future<List<Map<String, dynamic>>> getNotificationLogs() async {
    final raw = await read('notification_logs');
    if (raw == null) {
      final defaultAlerts = [
        {
          'id': '1',
          'title': 'Welcome to SmartStudy 🎓',
          'content': 'Check your Course tab to view newly published lectures.',
          'timestamp': DateTime.now().subtract(const Duration(hours: 3)).toIso8601String(),
          'read': false
        },
        {
          'id': '2',
          'title': 'New Announcement Posted',
          'content': 'Teacher posted: DSA Quiz is scheduled next Monday. Practice wrong questions from Question Bank.',
          'timestamp': DateTime.now().subtract(const Duration(days: 1)).toIso8601String(),
          'read': false
        }
      ];
      await write('notification_logs', json.encode(defaultAlerts));
      return defaultAlerts;
    }
    try {
      final List<dynamic> decoded = json.decode(raw);
      return decoded.map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> addNotificationLog(String title, String content) async {
    final logs = await getNotificationLogs();
    logs.insert(0, {
      'id': DateTime.now().millisecondsSinceEpoch.toString(),
      'title': title,
      'content': content,
      'timestamp': DateTime.now().toIso8601String(),
      'read': false
    });
    await write('notification_logs', json.encode(logs));
  }

  Future<void> markNotificationRead(String id) async {
    final logs = await getNotificationLogs();
    for (var log in logs) {
      if (log['id'] == id) {
        log['read'] = true;
      }
    }
    await write('notification_logs', json.encode(logs));
  }

  Future<void> clearNotificationLogs() async {
    await write('notification_logs', json.encode(<Map<String, dynamic>>[]));
  }

  // ══════════════════════════════════════════════════════════════════
  //  clearAll — Sab data delete (nuclear option)
  // ══════════════════════════════════════════════════════════════════

  /// Storage ka sara data delete karo.
  /// Complete logout / account switch ke liye use karo.
  Future<void> clearAll() async {
    _fallbackStorage.clear();
    if (_isMac) {
      return;
    }
    try {
      await _storage.deleteAll();
    } catch (e) {
      print('StorageService.clearAll error: $e');
    }
  }
}

