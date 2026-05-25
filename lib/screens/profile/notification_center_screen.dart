// ╔══════════════════════════════════════════════════════════════════╗
// ║              NOTIFICATION CENTER SCREEN                          ║
// ║  Displays history of system broadcasts, alerts, and notifications.║
// ║  Supports marking read, clearing logs, and bilingual layout.     ║
// ╚══════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/settings_provider.dart';
import '../../services/storage_service.dart';
import 'package:intl/intl.dart' hide TextDirection;

class NotificationCenterScreen extends ConsumerStatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  ConsumerState<NotificationCenterScreen> createState() => _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends ConsumerState<NotificationCenterScreen> {
  final StorageService _storage = StorageService();
  List<Map<String, dynamic>> _notifications = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() => _isLoading = true);
    final logs = await _storage.getNotificationLogs();
    setState(() {
      _notifications = logs;
      _isLoading = false;
    });
  }

  Future<void> _markAsRead(String id) async {
    await _storage.markNotificationRead(id);
    // Reload state locally
    final updated = _notifications.map((n) {
      if (n['id'] == id) {
        final newN = Map<String, dynamic>.from(n);
        newN['read'] = true;
        return newN;
      }
      return n;
    }).toList();
    setState(() {
      _notifications = updated;
    });
  }

  Future<void> _clearAll() async {
    final bool? confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear All'),
        content: const Text('Are you sure you want to clear your notification history?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Clear', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await _storage.clearNotificationLogs();
      setState(() {
        _notifications = [];
      });
    }
  }

  String _formatTimestamp(String isoString) {
    try {
      final date = DateTime.parse(isoString);
      return DateFormat('dd MMM yyyy, hh:mm a').format(date);
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUrdu = ref.watch(settingsProvider).language == 'Urdu';
    final title = ref.watch(settingsProvider).translate('recent_alerts');

    return Directionality(
      textDirection: isUrdu ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: theme.colorScheme.background,
        appBar: AppBar(
          title: Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
          ),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => Navigator.pop(context),
          ),
          actions: [
            if (_notifications.isNotEmpty)
              IconButton(
                icon: const Icon(Icons.delete_sweep_rounded, color: Colors.redAccent),
                tooltip: 'Clear All',
                onPressed: _clearAll,
              ),
          ],
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _notifications.isEmpty
                ? _buildEmptyState(theme, isUrdu)
                : ListView.separated(
                    padding: const EdgeInsets.all(16),
                    physics: const BouncingScrollPhysics(),
                    itemCount: _notifications.length,
                    separatorBuilder: (context, index) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final notif = _notifications[index];
                      final isRead = notif['read'] == true;

                      return InkWell(
                        onTap: () {
                          if (!isRead) {
                            _markAsRead(notif['id']);
                          }
                        },
                        borderRadius: BorderRadius.circular(16),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: isRead
                                ? theme.colorScheme.surface
                                : theme.colorScheme.primary.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: isRead
                                  ? theme.colorScheme.outline.withOpacity(0.08)
                                  : theme.colorScheme.primary.withOpacity(0.2),
                              width: isRead ? 1 : 1.5,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.01),
                                blurRadius: 8,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Indicator Dot / Icon
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: isRead
                                      ? theme.colorScheme.onSurface.withOpacity(0.05)
                                      : theme.colorScheme.primary.withOpacity(0.12),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  isRead ? Icons.notifications_none_rounded : Icons.notifications_active_rounded,
                                  color: isRead ? Colors.grey : theme.colorScheme.primary,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: 14),

                              // Text details
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Expanded(
                                          child: Text(
                                            notif['title'] ?? '',
                                            style: TextStyle(
                                              fontWeight: isRead ? FontWeight.w600 : FontWeight.w800,
                                              fontSize: 14,
                                              color: theme.colorScheme.onSurface,
                                            ),
                                          ),
                                        ),
                                        if (!isRead)
                                          Container(
                                            margin: const EdgeInsets.only(left: 8),
                                            width: 8,
                                            height: 8,
                                            decoration: BoxDecoration(
                                              color: theme.colorScheme.primary,
                                              shape: BoxShape.circle,
                                            ),
                                          ),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      notif['content'] ?? '',
                                      style: TextStyle(
                                        fontSize: 12.5,
                                        height: 1.4,
                                        color: theme.colorScheme.onSurfaceVariant.withOpacity(0.85),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      _formatTimestamp(notif['timestamp'] ?? ''),
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w600,
                                        color: theme.colorScheme.onSurfaceVariant.withOpacity(0.5),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme, bool isUrdu) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.notifications_off_rounded,
              size: 72,
              color: theme.colorScheme.primary.withOpacity(0.2),
            ),
            const SizedBox(height: 16),
            Text(
              isUrdu ? 'کوئی نوٹیفکیشن نہیں ہے' : 'All caught up!',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              isUrdu
                  ? 'آپ کی نوٹیفکیشن ہسٹری خالی ہے'
                  : 'You do not have any notification records inside your storage.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 12,
                color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
