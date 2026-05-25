import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import 'auth_provider.dart';

class SettingsState {
  final bool isDarkMode;
  final bool isNotificationsEnabled;
  final bool isAttentionModeEnabled;
  final String language;
  final bool isLoading;
  final String? error;
  final String? successMessage;

  const SettingsState({
    this.isDarkMode = false,
    this.isNotificationsEnabled = true,
    this.isAttentionModeEnabled = false,
    this.language = 'English',
    this.isLoading = false,
    this.error,
    this.successMessage,
  });

  static const Map<String, Map<String, String>> _localizedValues = {
    'English': {
      'my_courses': 'My Courses',
      'attendance': 'Attendance',
      'profile': 'Profile',
      'logout': 'Logout',
      'course_progress': 'Course Progress',
      'attempt_again': 'Attempt Again',
      'my_progress': 'My Progress',
      'question_bank': 'Question Bank',
      'settings': 'Settings',
      'overall_attendance': 'Overall Attendance',
      'change_password': 'Change Password',
      'theme_dark': 'Dark Mode',
      'notifications': 'Notifications',
      'attention_mode': 'Attention Mode',
      'language': 'Language',
      'clear_cache': 'Clear Cache',
      'recommendations': 'Focus Areas & Recommendations',
      'recent_alerts': 'Recent Alerts',
      'try_again': 'Try Again',
      'active_courses': 'Enrolled Courses',
      'courses_count': 'courses enrolled',
      'credit_hours': 'Credit Hours',
      'view_lectures': 'View Lectures',
      'notes_pdf': 'Notes PDF',
      'present': 'Present',
      'absent': 'Absent',
      'partial': 'Partial',
      'total_lectures': 'Total Lectures',
      'safe_status': 'Safe Status',
      'at_risk': 'At Risk',
      'attendance_summary': 'Attendance Summary',
      'attendance_trend': 'Attendance Trend (Watch % History)',
      'logs': 'Detailed Attendance Logs',
      'welcome': 'Welcome',
      'home': 'Home',
    },
    'Urdu': {
      'my_courses': 'میرے کورسز',
      'attendance': 'حاضری',
      'profile': 'پروفائل',
      'home': 'ہوم',
      'logout': 'لاگ آؤٹ',
      'course_progress': 'کورس کی کارکردگی',
      'attempt_again': 'دوبارہ کوشش کریں',
      'my_progress': 'میری ترقی',
      'question_bank': 'سوالات کی فہرست',
      'settings': 'ترتیبات',
      'overall_attendance': 'مجموعی حاضری',
      'change_password': 'پاس ورڈ تبدیل کریں',
      'theme_dark': 'ڈارک موڈ',
      'notifications': 'اطلاعات',
      'attention_mode': 'توجہ موڈ',
      'language': 'زبان',
      'clear_cache': 'کیشے صاف کریں',
      'recommendations': 'توجہ دینے والے عنوانات اور سفارشات',
      'recent_alerts': 'حالیہ الرٹس',
      'try_again': 'دوبارہ کوشش کریں',
      'active_courses': 'شامل کردہ کورسز',
      'courses_count': 'کورسز میں داخلہ',
      'credit_hours': 'کریڈٹ گھنٹے',
      'view_lectures': 'لیکچرز دیکھیں',
      'notes_pdf': 'لیکچر نوٹس پی ڈی ایف',
      'present': 'حاضر',
      'absent': 'غیر حاضر',
      'partial': 'جزوی',
      'total_lectures': 'کل لیکچرز',
      'safe_status': 'محفوظ کارکردگی',
      'at_risk': 'خطرے میں',
      'attendance_summary': 'حاضری کی تفصیلات',
      'attendance_trend': 'حاضری کا رجحان (لیکچر دیکھنے کی تاریخ)',
      'logs': 'تفصیلی حاضری کا لاگ',
      'welcome': 'خوش آمدید',
    }
  };

  String translate(String key) {
    return _localizedValues[language]?[key] ?? _localizedValues['English']?[key] ?? key;
  }

  SettingsState copyWith({
    bool? isDarkMode,
    bool? isNotificationsEnabled,
    bool? isAttentionModeEnabled,
    String? language,
    bool? isLoading,
    String? error,
    String? successMessage,
    bool clearError = false,
    bool clearSuccess = false,
  }) {
    return SettingsState(
      isDarkMode: isDarkMode ?? this.isDarkMode,
      isNotificationsEnabled: isNotificationsEnabled ?? this.isNotificationsEnabled,
      isAttentionModeEnabled: isAttentionModeEnabled ?? this.isAttentionModeEnabled,
      language: language ?? this.language,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      successMessage: clearSuccess ? null : (successMessage ?? this.successMessage),
    );
  }
}


class SettingsNotifier extends StateNotifier<SettingsState> {
  final ApiService _api;
  final StorageService _storage;
  final Ref _ref;

  SettingsNotifier(this._ref, {ApiService? api, StorageService? storage})
      : _api = api ?? ApiService(),
        _storage = storage ?? StorageService(),
        super(const SettingsState()) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final dark = await _storage.read('dark_mode_enabled');
    final notif = await _storage.read('notifications_enabled');
    final att = await _storage.read('attention_mode_enabled');
    final lang = await _storage.read('language');

    state = state.copyWith(
      isDarkMode: dark == 'true',
      isNotificationsEnabled: notif != 'false', // Default true
      isAttentionModeEnabled: att == 'true',
      language: lang ?? 'English',
    );
  }

  Future<void> toggleDarkMode() async {
    final newVal = !state.isDarkMode;
    state = state.copyWith(isDarkMode: newVal);
    await _storage.write('dark_mode_enabled', newVal.toString());
  }

  Future<void> toggleNotifications() async {
    final newVal = !state.isNotificationsEnabled;
    state = state.copyWith(isNotificationsEnabled: newVal);
    await _storage.write('notifications_enabled', newVal.toString());
  }

  Future<void> toggleAttentionMode() async {
    final newVal = !state.isAttentionModeEnabled;
    state = state.copyWith(isAttentionModeEnabled: newVal);
    await _storage.write('attention_mode_enabled', newVal.toString());
  }

  Future<void> setLanguage(String lang) async {
    state = state.copyWith(language: lang);
    await _storage.write('language', lang);
  }

  Future<void> changePassword(String currentPassword, String newPassword) async {
    state = state.copyWith(isLoading: true, clearError: true, clearSuccess: true);
    try {
      await _api.changePassword(
        currentPassword: currentPassword,
        newPassword: newPassword,
      );
      state = state.copyWith(
        isLoading: false,
        successMessage: 'Password changed successfully.',
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
      rethrow;
    }
  }

  Future<void> logout() async {
    await _ref.read(authProvider.notifier).logout();
  }
  
  void clearStatus() {
    state = state.copyWith(clearError: true, clearSuccess: true);
  }
}

final settingsProvider = StateNotifierProvider<SettingsNotifier, SettingsState>((ref) {
  return SettingsNotifier(ref);
});
