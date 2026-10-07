class AmbientState {
  final bool isListeningActive;
  final String sessionDuration;
  final List<String> activeLanguages;
  final String activeModeDescription;
  final int tasksSyncedCount;
  final int rescheduledTodayCount;
  final String? disruptionNotice;
  final int dayShiftMinutes;
  
  // Integrations
  final String? connectedGmail;
  final bool isGmailSyncEnabled;
  final bool isWhatsAppBridgeEnabled;
  final String whatsAppSyncStatus;

  // Raw text observation buffer (space for raw speech & notifications before backend ingestion)
  final List<RawObservationLog> rawLogs;
  final String backendBaseUrl;

  const AmbientState({
    this.isListeningActive = true,
    this.sessionDuration = '6h 12m',
    this.activeLanguages = const ['Hindi', 'English', 'Marathi'],
    this.activeModeDescription = 'Transcribing ambient audio (Hindi–English mix active) • 0 drops',
    this.tasksSyncedCount = 14,
    this.rescheduledTodayCount = 3,
    this.disruptionNotice = 'You said "I woke up late" at 8:15. Your day shifted +40 min.',
    this.dayShiftMinutes = 40,
    this.connectedGmail = 'ayush@gmail.com',
    this.isGmailSyncEnabled = true,
    this.isWhatsAppBridgeEnabled = true,
    this.whatsAppSyncStatus = 'Notification Listener ACTIVE • 4 chats connected',
    this.rawLogs = const [],
    this.backendBaseUrl = 'http://10.0.2.2:8000',
  });

  AmbientState copyWith({
    bool? isListeningActive,
    String? sessionDuration,
    List<String>? activeLanguages,
    String? activeModeDescription,
    int? tasksSyncedCount,
    int? rescheduledTodayCount,
    String? disruptionNotice,
    int? dayShiftMinutes,
    String? connectedGmail,
    bool? isGmailSyncEnabled,
    bool? isWhatsAppBridgeEnabled,
    String? whatsAppSyncStatus,
    List<RawObservationLog>? rawLogs,
    String? backendBaseUrl,
  }) {
    return AmbientState(
      isListeningActive: isListeningActive ?? this.isListeningActive,
      sessionDuration: sessionDuration ?? this.sessionDuration,
      activeLanguages: activeLanguages ?? this.activeLanguages,
      activeModeDescription: activeModeDescription ?? this.activeModeDescription,
      tasksSyncedCount: tasksSyncedCount ?? this.tasksSyncedCount,
      rescheduledTodayCount: rescheduledTodayCount ?? this.rescheduledTodayCount,
      disruptionNotice: disruptionNotice ?? this.disruptionNotice,
      dayShiftMinutes: dayShiftMinutes ?? this.dayShiftMinutes,
      connectedGmail: connectedGmail ?? this.connectedGmail,
      isGmailSyncEnabled: isGmailSyncEnabled ?? this.isGmailSyncEnabled,
      isWhatsAppBridgeEnabled: isWhatsAppBridgeEnabled ?? this.isWhatsAppBridgeEnabled,
      whatsAppSyncStatus: whatsAppSyncStatus ?? this.whatsAppSyncStatus,
      rawLogs: rawLogs ?? this.rawLogs,
      backendBaseUrl: backendBaseUrl ?? this.backendBaseUrl,
    );
  }
}

class RawObservationLog {
  final String id;
  final String source; // 'audio' | 'notification' | 'whatsapp' | 'email'
  final String channel;
  final String rawText;
  final DateTime timestamp;
  final bool syncedToBackend;
  final String? detectedLanguage;

  const RawObservationLog({
    required this.id,
    required this.source,
    required this.channel,
    required this.rawText,
    required this.timestamp,
    this.syncedToBackend = false,
    this.detectedLanguage,
  });
}
