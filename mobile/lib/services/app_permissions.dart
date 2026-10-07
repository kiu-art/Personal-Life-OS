import 'package:notification_listener_service/notification_listener_service.dart';
import 'package:permission_handler/permission_handler.dart';

/// One place for every always-on permission Bixy needs:
/// microphone (ambient chunks), notifications (foreground status),
/// and notification-listener access (WhatsApp/Gmail ingestion).
class AppPermissions {
  /// Microphone for the 10s ambient chunks.
  static Future<bool> ensureMicrophone() async {
    var status = await Permission.microphone.status;
    if (status.isGranted) return true;
    status = await Permission.microphone.request();
    return status.isGranted;
  }

  /// Post-notifications permission for the "Bixy is listening" status.
  static Future<bool> ensureNotifications() async {
    var status = await Permission.notification.status;
    if (status.isGranted) return true;
    status = await Permission.notification.request();
    return status.isGranted;
  }

  /// System notification-listener access (special access screen).
  static Future<bool> hasListenerAccess() {
    return NotificationListenerService.isPermissionGranted();
  }

  /// Opens the system listener-access screen; true once granted.
  static Future<bool> requestListenerAccess() {
    return NotificationListenerService.requestPermission();
  }

  static Future<void> openSettings() => openAppSettings();
}
