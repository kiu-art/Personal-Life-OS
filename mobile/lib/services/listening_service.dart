import 'package:flutter_foreground_task/flutter_foreground_task.dart';

// NOTE (build-time verification needed): written against the
// flutter_foreground_task 8.x API (init / startService / updateService /
// stopService / isRunningService + TaskHandler). Confirm against the
// resolved pub-cache source on the first build. No notification action
// buttons in v1 on purpose — pause/resume lives in the app shade screen.

@pragma('vm:entry-point')
void bixyForegroundCallback() {
  FlutterForegroundTask.setTaskHandler(BixyTaskHandler());
}

class BixyTaskHandler extends TaskHandler {
  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {}

  @override
  void onRepeatEvent(DateTime timestamp) async {
    // Heartbeat only — the 10s record/transcribe loop runs in the UI
    // isolate (AmbientListener) while this service keeps the process
    // alive with the microphone foreground-service type.
    await FlutterForegroundTask.updateService(
      notificationText: 'Capturing ambient audio…',
    );
  }

  @override
  Future<void> onDestroy(DateTime timestamp) async {}
}

/// Persistent "Bixy is listening" notification + keep-alive for the mic.
class ListeningService {
  static bool _initialised = false;

  static void init() {
    if (_initialised) return;
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'bixy_listening',
        channelName: 'Bixy listening',
        channelDescription: 'Shows while Bixy captures ambient audio.',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: true,
        playSound: false,
      ),
      foregroundTaskOptions: ForegroundTaskOptions(
        eventAction: ForegroundTaskEventAction.repeat(10000),
        autoRunOnBoot: false,
        allowWakeLock: true,
        allowWifiLock: false,
      ),
    );
    _initialised = true;
  }

  static Future<bool> get isRunning =>
      FlutterForegroundTask.isRunningService;

  static Future<void> start() async {
    init();
    if (await isRunning) return;
    await FlutterForegroundTask.startService(
      notificationTitle: 'Bixy is listening',
      notificationText: 'Say "Bixy…" any time — tap to open.',
      callback: bixyForegroundCallback,
    );
  }

  static Future<void> update({required bool listening}) async {
    if (!await isRunning) return;
    await FlutterForegroundTask.updateService(
      notificationTitle:
          listening ? 'Bixy is listening' : 'Bixy paused',
      notificationText: listening
          ? 'Capturing ambient audio…'
          : 'Tap to resume listening.',
    );
  }

  static Future<void> stop() async {
    if (!await isRunning) return;
    await FlutterForegroundTask.stopService();
  }
}
