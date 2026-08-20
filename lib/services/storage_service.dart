// ╔══════════════════════════════════════════════════════════════════╗
// ║              STORAGE SERVICE — CROSS PLATFORM                   ║
// ║  Android: Keystore | iOS/macOS: Keychain | Web: WebCrypto       ║
// ║  Windows/Linux: Platform secure storage                         ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/constants.dart';
import '../core/router.dart';

/// ──────────────────────────────────────────────────────────────────
/// StorageService
/// ──────────────────────────────────────────────────────────────────
///
/// Cross-platform secure storage service.
///
/// Supported platforms:
///   → Android
///   → iOS
///   → macOS
///   → Windows
///   → Linux
///   → Web
///
/// IMPORTANT:
/// We intentionally DO NOT use `dart:io` or `Platform.isMacOS`.
/// Those APIs are not supported by Flutter Web.
///
/// `flutter_secure_storage` automatically selects the appropriate
/// implementation for the current platform.
/// ──────────────────────────────────────────────────────────────────

class StorageService {
  // In-memory fallback.
  //
  // This is useful if secure storage temporarily fails.
  // It also allows the application to continue running instead of
  // completely crashing because of a storage exception.
  static final Map<String, String> _fallbackStorage =
      <String, String>{};

  /// Synchronous token access for router/auth logic.
  ///
  /// IMPORTANT:
  /// This is only the in-memory fallback.
  /// The real persistent token is stored asynchronously using
  /// FlutterSecureStorage.
  static String? get fallbackToken =>
      _fallbackStorage[AppConstants.keyAuthToken];

  // ─────────────────────────────────────────────────────────────────
  // SECURE STORAGE
  // ─────────────────────────────────────────────────────────────────

  final FlutterSecureStorage _storage =
      const FlutterSecureStorage(
    // Android
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),

    // iOS
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),

    // macOS
    mOptions: MacOsOptions(
      useDataProtectionKeyChain: false,
    ),

    // Web
    //
    // flutter_secure_storage provides its own WebCrypto-based
    // implementation.
    //
    // Do NOT use dart:io here.
    webOptions: WebOptions(),
    
  );

  // ══════════════════════════════════════════════════════════════════
  // AUTH TOKEN
  // ══════════════════════════════════════════════════════════════════

  /// Save JWT authentication token.
  Future<void> saveToken(String token) async {
    // Always update fallback first.
    _fallbackStorage[AppConstants.keyAuthToken] = token;

    // Tell router/auth system that user is logged in.
    AppAuthNotifier.instance.setLoggedIn(true);

    try {
      await _storage.write(
        key: AppConstants.keyAuthToken,
        value: token,
      );
    } catch (e) {
      print('StorageService.saveToken error: $e');

      // Keep fallback token so application can continue running.
      _fallbackStorage[AppConstants.keyAuthToken] = token;
    }
  }

  /// Get saved JWT token.
  Future<String?> getToken() async {
    try {
      final String? token = await _storage.read(
        key: AppConstants.keyAuthToken,
      );

      // If secure storage has token, use it.
      if (token != null && token.isNotEmpty) {
        // Keep fallback synchronized.
        _fallbackStorage[AppConstants.keyAuthToken] = token;
        return token;
      }

      // Otherwise use fallback.
      return _fallbackStorage[AppConstants.keyAuthToken];
    } catch (e) {
      print('StorageService.getToken error: $e');

      return _fallbackStorage[AppConstants.keyAuthToken];
    }
  }

  /// Delete JWT token during logout.
  Future<void> deleteToken() async {
    _fallbackStorage.remove(AppConstants.keyAuthToken);

    // Tell router/auth system that user is logged out.
    AppAuthNotifier.instance.setLoggedIn(false);

    try {
      await _storage.delete(
        key: AppConstants.keyAuthToken,
      );
    } catch (e) {
      print('StorageService.deleteToken error: $e');
    }
  }

  /// Check whether a JWT token exists.
  Future<bool> hasToken() async {
    final String? token = await getToken();

    return token != null && token.isNotEmpty;
  }

  // ══════════════════════════════════════════════════════════════════
  // USER ROLE
  // ══════════════════════════════════════════════════════════════════

  /// Save user role.
  ///
  /// Example:
  ///   student
  ///   instructor
  Future<void> saveUserRole(String role) async {
    _fallbackStorage['user_role'] = role;

    try {
      await _storage.write(
        key: 'user_role',
        value: role,
      );
    } catch (e) {
      print('StorageService.saveUserRole error: $e');
    }
  }

  /// Get saved user role.
  Future<String?> getUserRole() async {
    try {
      final String? role = await _storage.read(
        key: 'user_role',
      );

      if (role != null) {
        _fallbackStorage['user_role'] = role;
        return role;
      }

      return _fallbackStorage['user_role'];
    } catch (e) {
      print('StorageService.getUserRole error: $e');

      return _fallbackStorage['user_role'];
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // USER NAME
  // ══════════════════════════════════════════════════════════════════

  /// Save user's full name.
  Future<void> saveUserName(String name) async {
    _fallbackStorage['user_name'] = name;

    try {
      await _storage.write(
        key: 'user_name',
        value: name,
      );
    } catch (e) {
      print('StorageService.saveUserName error: $e');
    }
  }

  /// Get saved user's full name.
  Future<String?> getUserName() async {
    try {
      final String? name = await _storage.read(
        key: 'user_name',
      );

      if (name != null) {
        _fallbackStorage['user_name'] = name;
        return name;
      }

      return _fallbackStorage['user_name'];
    } catch (e) {
      print('StorageService.getUserName error: $e');

      return _fallbackStorage['user_name'];
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // GENERIC KEY-VALUE STORAGE
  // ══════════════════════════════════════════════════════════════════

  /// Generic write method.
  Future<void> write(
    String key,
    String value,
  ) async {
    _fallbackStorage[key] = value;

    try {
      await _storage.write(
        key: key,
        value: value,
      );
    } catch (e) {
      print('StorageService.write error: $e');
    }
  }

  /// Generic read method.
  Future<String?> read(String key) async {
    try {
      final String? value = await _storage.read(
        key: key,
      );

      if (value != null) {
        _fallbackStorage[key] = value;
        return value;
      }

      return _fallbackStorage[key];
    } catch (e) {
      print('StorageService.read error: $e');

      return _fallbackStorage[key];
    }
  }

  /// Generic delete method.
  Future<void> delete(String key) async {
    _fallbackStorage.remove(key);

    try {
      await _storage.delete(
        key: key,
      );
    } catch (e) {
      print('StorageService.delete error: $e');
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // VIDEO PLAYER AUTO-RESUME CACHE
  // ══════════════════════════════════════════════════════════════════

  /// Save video playback position.
  Future<void> saveVideoPosition(
    int lectureId,
    int seconds,
  ) async {
    await write(
      'video_pos_$lectureId',
      seconds.toString(),
    );
  }

  /// Get video playback position.
  Future<int> getVideoPosition(
    int lectureId,
  ) async {
    final String? posStr =
        await read('video_pos_$lectureId');

    if (posStr == null) {
      return 0;
    }

    return int.tryParse(posStr) ?? 0;
  }

  // ══════════════════════════════════════════════════════════════════
  // Q&A DYNAMIC BOOKMARKS
  // ══════════════════════════════════════════════════════════════════

  /// Get all bookmarked Q&As.
  Future<List<Map<String, dynamic>>> getBookmarkedQnAs() async {
    final String? raw = await read('bookmarked_qnas');

    if (raw == null || raw.isEmpty) {
      return <Map<String, dynamic>>[];
    }

    try {
      final List<dynamic> decoded =
          json.decode(raw) as List<dynamic>;

      return decoded
          .map(
            (dynamic e) =>
                Map<String, dynamic>.from(e as Map),
          )
          .toList();
    } catch (e) {
      print(
        'StorageService.getBookmarkedQnAs error: $e',
      );

      return <Map<String, dynamic>>[];
    }
  }

  /// Toggle Q&A bookmark.
  Future<void> toggleQnABookmark(
    Map<String, dynamic> qnaMap,
  ) async {
    final List<Map<String, dynamic>> bookmarks =
        await getBookmarkedQnAs();

    final String questionText =
        qnaMap['question'] as String;

    final int index = bookmarks.indexWhere(
      (Map<String, dynamic> bookmark) =>
          bookmark['question'] == questionText,
    );

    if (index >= 0) {
      bookmarks.removeAt(index);
    } else {
      bookmarks.add(qnaMap);
    }

    await write(
      'bookmarked_qnas',
      json.encode(bookmarks),
    );
  }

  /// Check whether Q&A is bookmarked.
  Future<bool> isQnABookmarked(
    String questionText,
  ) async {
    final List<Map<String, dynamic>> bookmarks =
        await getBookmarkedQnAs();

    return bookmarks.any(
      (Map<String, dynamic> bookmark) =>
          bookmark['question'] == questionText,
    );
  }

  // ══════════════════════════════════════════════════════════════════
  // NOTIFICATION HUB HISTORY
  // ══════════════════════════════════════════════════════════════════

  /// Get notification history.
  Future<List<Map<String, dynamic>>> getNotificationLogs() async {
    final String? raw =
        await read('notification_logs');

    // First run — create default notifications.
    if (raw == null || raw.isEmpty) {
      final List<Map<String, dynamic>> defaultAlerts =
          <Map<String, dynamic>>[
        <String, dynamic>{
          'id': '1',
          'title': 'Welcome to SmartStudy 🎓',
          'content':
              'Check your Course tab to view newly published lectures.',
          'timestamp': DateTime.now()
              .subtract(
                const Duration(hours: 3),
              )
              .toIso8601String(),
          'read': false,
        },
        <String, dynamic>{
          'id': '2',
          'title': 'New Announcement Posted',
          'content':
              'Teacher posted: DSA Quiz is scheduled next Monday. Practice wrong questions from Question Bank.',
          'timestamp': DateTime.now()
              .subtract(
                const Duration(days: 1),
              )
              .toIso8601String(),
          'read': false,
        },
      ];

      await write(
        'notification_logs',
        json.encode(defaultAlerts),
      );

      return defaultAlerts;
    }

    try {
      final List<dynamic> decoded =
          json.decode(raw) as List<dynamic>;

      return decoded
          .map(
            (dynamic e) =>
                Map<String, dynamic>.from(e as Map),
          )
          .toList();
    } catch (e) {
      print(
        'StorageService.getNotificationLogs error: $e',
      );

      return <Map<String, dynamic>>[];
    }
  }

  /// Add notification to history.
  Future<void> addNotificationLog(
    String title,
    String content,
  ) async {
    final List<Map<String, dynamic>> logs =
        await getNotificationLogs();

    logs.insert(
      0,
      <String, dynamic>{
        'id':
            DateTime.now().millisecondsSinceEpoch.toString(),
        'title': title,
        'content': content,
        'timestamp':
            DateTime.now().toIso8601String(),
        'read': false,
      },
    );

    await write(
      'notification_logs',
      json.encode(logs),
    );
  }

  /// Mark notification as read.
  Future<void> markNotificationRead(
    String id,
  ) async {
    final List<Map<String, dynamic>> logs =
        await getNotificationLogs();

    for (final Map<String, dynamic> log in logs) {
      if (log['id'] == id) {
        log['read'] = true;
      }
    }

    await write(
      'notification_logs',
      json.encode(logs),
    );
  }

  /// Clear notification history.
  Future<void> clearNotificationLogs() async {
    await write(
      'notification_logs',
      json.encode(
        <Map<String, dynamic>>[],
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════
  // CLEAR ALL
  // ══════════════════════════════════════════════════════════════════

  /// Delete all locally stored application data.
  Future<void> clearAll() async {
    _fallbackStorage.clear();

    try {
      await _storage.deleteAll();
    } catch (e) {
      print(
        'StorageService.clearAll error: $e',
      );
    }
  }
}