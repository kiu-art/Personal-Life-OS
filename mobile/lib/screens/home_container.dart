import 'dart:async';

import 'package:flutter/material.dart';
import '../models/ambient_state.dart';
import '../services/ambient_listener.dart';
import '../services/app_permissions.dart';
import '../services/backend_service.dart';
import '../services/listening_service.dart';
import '../services/notification_ingest.dart';
import '../services/stt_engine.dart';
import 'today_screen.dart';

class HomeContainer extends StatefulWidget {
  const HomeContainer({super.key});

  @override
  State<HomeContainer> createState() => _HomeContainerState();
}

class _HomeContainerState extends State<HomeContainer> {
  AmbientState _ambientState = const AmbientState();

  late final AmbientListener _ambient;
  late final NotificationIngest _ingest;
  StreamSubscription<AmbientStatus>? _ambientSub;
  bool _modelBusy = false;

  @override
  void initState() {
    super.initState();
    final backend = BackendService(baseUrl: _ambientState.backendBaseUrl);
    _ambient = AmbientListener(backend: backend);
    _ingest = NotificationIngest(backend: backend);
    // Consent-first: mic stays off until the user explicitly enables it,
    // even though the persisted default state reads "listening".
    _ambientState = _ambientState.copyWith(
      isListeningActive: false,
      activeModeDescription: 'Tap the mic to start ambient capture',
    );
    _ambientSub = _ambient.status.listen(_onAmbientStatus);
  }

  @override
  void dispose() {
    _ambientSub?.cancel();
    _ambient.dispose();
    _ingest.stop();
    super.dispose();
  }

  void _updateState(AmbientState newState) {
    if (newState.backendBaseUrl != _ambientState.backendBaseUrl) {
      _ambient.backend.baseUrl = newState.backendBaseUrl;
      _ingest.backend.baseUrl = newState.backendBaseUrl;
    }
    setState(() {
      _ambientState = newState;
    });
  }

  void _onAmbientStatus(AmbientStatus s) {
    if (!mounted) return;
    final langs = _ambientState.activeLanguages;
    setState(() {
      _ambientState = _ambientState.copyWith(
        isListeningActive: s.running,
        activeModeDescription: s.running
            ? 'Transcribing ambient audio (${langs.join('–')} mix) • ${s.chunksSent} sent'
            : 'Ambient audio capture paused',
      );
    });
    ListeningService.update(listening: s.running);
  }

  void _deny(String what) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
            '$what permission denied — enable it in system settings.'),
        action: const SnackBarAction(
          label: 'Open',
          onPressed: AppPermissions.openSettings,
        ),
      ),
    );
  }

  /// First-run voice-model download (~75 MB, one time, on Wi-Fi ideally).
  Future<bool> _ensureModel() async {
    final manager = WhisperModelManager();
    if (await manager.isReady) return true;
    if (!mounted || _modelBusy) return false;
    _modelBusy = true;
    double progress = 0;
    String? error;
    if (mounted) {
      await showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setDlg) => AlertDialog(
            title: const Text('Voice model'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                    'One-time ~75 MB download for offline Hindi / English / Marathi transcription.'),
                const SizedBox(height: 12),
                LinearProgressIndicator(value: progress),
                if (error != null) ...[
                  const SizedBox(height: 8),
                  Text(error!,
                      style: TextStyle(
                          color: Theme.of(ctx).colorScheme.error)),
                ],
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('Later'),
              ),
              FilledButton(
                onPressed: error != null
                    ? null
                    : () async {
                        try {
                          await manager.download(
                            onProgress: (p) =>
                                setDlg(() => progress = p),
                          );
                          if (ctx.mounted) Navigator.of(ctx).pop();
                        } catch (e) {
                          setDlg(() => error = e.toString());
                        }
                      },
                child: const Text('Download'),
              ),
            ],
          ),
        ),
      );
    }
    _modelBusy = false;
    return manager.isReady;
  }

  Future<void> _toggleListening() async {
    if (_ambientState.isListeningActive || _ambient.isRunning) {
      await _ambient.stop();
      await ListeningService.stop();
      return; // status stream flips the icon to paused
    }
    if (!await AppPermissions.ensureMicrophone()) {
      _deny('Microphone');
      return;
    }
    await AppPermissions.ensureNotifications();
    if (!await _ensureModel()) return;
    try {
      await ListeningService.start();
      await _ambient.start();
    } catch (e) {
      await ListeningService.stop();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not start listening: $e')),
      );
      return;
    }
    if (await AppPermissions.hasListenerAccess()) {
      await _ingest.start();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0908),
      body: TodayScreen(
        ambientState: _ambientState,
        onStateChanged: _updateState,
        onToggleListening: _toggleListening,
      ),
    );
  }
}
