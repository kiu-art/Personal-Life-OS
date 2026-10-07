import 'dart:async';

import 'package:notification_listener_service/notification_event.dart';
import 'package:notification_listener_service/notification_listener_service.dart';

import 'backend_service.dart';
import 'chunk_gate.dart';

/// Forwards Android notifications (WhatsApp, Gmail, …) into the backend
/// raw-text buffer (POST /api/observations/, source=chat).
///
/// Mapping mirrors the WhatsApp bridge contract: channel + sender +
/// raw_text + metadata. Own-app and removed notifications are skipped.
class NotificationIngest {
  final BackendService backend;

  StreamSubscription<ServiceNotificationEvent>? _sub;
  bool _running = false;

  NotificationIngest({BackendService? backend})
      : backend = backend ?? BackendService();

  bool get isRunning => _running;

  static const _ownPackages = {
    'com.example.personality_life_os',
  };

  /// Maps a package name to the ingestion channel Bixy expects.
  static String channelFor(String? packageName) {
    switch (packageName) {
      case 'com.whatsapp':
      case 'com.whatsapp.w4b':
        return 'WhatsApp';
      case 'com.google.android.gm':
        return 'Gmail';
      default:
        return 'System';
    }
  }

  Future<bool> start() async {
    if (_running) return true;
    _sub = NotificationListenerService.notificationsStream.listen(
      _onEvent,
      onError: (_) {},
    );
    _running = true;
    return true;
  }

  Future<void> _onEvent(ServiceNotificationEvent event) async {
    try {
      if (event.hasRemoved) return;
      final text = event.content.trim();
      if (text.isEmpty) return;
      if (_ownPackages.contains(event.packageName)) return;
      final clean = ChunkGate.normalize(text);
      if (!ChunkGate.shouldIngest(clean, null)) return;
      await backend.sendNotificationObservation(
        channel: channelFor(event.packageName),
        sender: event.title.trim().isEmpty
            ? (event.packageName.isEmpty ? 'unknown' : event.packageName)
            : event.title.trim(),
        rawText: clean,
        metadata: {
          'package': event.packageName,
          'notification_id': event.id,
          'client': 'Bixy_Mobile',
        },
      );
    } catch (_) {}
  }

  Future<void> stop() async {
    await _sub?.cancel();
    _sub = null;
    _running = false;
  }
}
