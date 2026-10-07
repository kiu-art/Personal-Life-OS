import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'backend_service.dart';
import 'chunk_gate.dart';
import 'stt_engine.dart';

/// Status snapshots for UI (listening pill, shade metrics).
class AmbientStatus {
  final bool running;
  final bool modelReady;
  final int chunksSent;
  final String? lastTranscript;

  const AmbientStatus({
    required this.running,
    required this.modelReady,
    required this.chunksSent,
    this.lastTranscript,
  });
}

/// Records the mic in ~10s WAV chunks, transcribes each chunk fully
/// on-device, and ships surviving transcripts to the backend raw-text
/// buffer (POST /api/observations/, source=audio).
///
/// Runs in the main isolate while the mic-type foreground service keeps
/// the process alive in the background.
class AmbientListener {
  static const chunkSeconds = 10;

  final BackendService backend;
  final SttEngine engine;
  final Future<Directory> Function() chunkDir;

  final _status = StreamController<AmbientStatus>.broadcast();
  Stream<AmbientStatus> get status => _status.stream;

  Timer? _timer;
  bool _busy = false;
  bool _running = false;
  int _chunksSent = 0;
  String? _lastSent;
  String? _lastTranscript;
  late final AudioRecorder _recorder;

  AmbientListener({
    BackendService? backend,
    SttEngine? engine,
    Future<Directory> Function()? chunkDir,
  })  : backend = backend ?? BackendService(),
        engine = engine ?? SherpaWhisperEngine(),
        chunkDir = chunkDir ?? _defaultChunkDir {
    _recorder = AudioRecorder();
  }

  static Future<Directory> _defaultChunkDir() async {
    final cache = await getApplicationCacheDirectory();
    final dir = Directory('${cache.path}/bixy_chunks');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  bool get isRunning => _running;

  Future<bool> get isModelReady => engine.ready;

  /// Starts the loop. Throws [StateError] when the Whisper model has not
  /// been downloaded yet — the UI should route to model download first.
  Future<void> start() async {
    if (_running) return;
    if (!await engine.ready) {
      await engine.init(); // throws StateError when no model on disk
    }
    _running = true;
    _emit();
    _timer = Timer.periodic(
      const Duration(seconds: chunkSeconds),
      (_) => _recordAndShip(),
    );
    // Start the first chunk immediately instead of waiting 10s.
    unawaited(_recordAndShip());
  }

  Future<void> stop() async {
    _timer?.cancel();
    _timer = null;
    _running = false;
    try {
      if (await _recorder.isRecording()) await _recorder.stop();
    } catch (_) {}
    _emit();
  }

  Future<void> _recordAndShip() async {
    if (!_running || _busy) return;
    _busy = true;
    try {
      final dir = await chunkDir();
      final path =
          '${dir.path}/chunk_${DateTime.now().millisecondsSinceEpoch}.wav';
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        ),
        path: path,
      );
      await Future.delayed(const Duration(seconds: chunkSeconds));
      if (!_running) {
        try {
          await _recorder.stop();
        } catch (_) {}
        return;
      }
      await _recorder.stop();
      final raw = await engine.transcribeFile(path);
      await File(path).delete().catchError((_) => File(path));
      final text = ChunkGate.normalize(raw);
      _lastTranscript = text.isEmpty ? null : text;
      if (ChunkGate.shouldIngest(text, _lastSent)) {
        await backend.sendNotificationObservation(
          source: 'audio',
          channel: 'VoiceNote',
          sender: 'Self',
          rawText: text,
          metadata: const {'source_device': 'ambient_mic'},
        );
        _lastSent = text;
        _chunksSent++;
        debugPrint('[Bixy] chunk sent (${text.length} chars)');
      } else {
        debugPrint('[Bixy] chunk skipped (empty/noise/repeat)');
      }
      _emit();
    } catch (e) {
      // A failed chunk must never kill the loop; the next tick retries.
      debugPrint('[Bixy] chunk error: $e');
    } finally {
      _busy = false;
    }
  }

  void _emit() {
    if (_status.isClosed) return;
    engine.ready.then((modelReady) {
      if (_status.isClosed) return;
      _status.add(AmbientStatus(
        running: _running,
        modelReady: modelReady,
        chunksSent: _chunksSent,
        lastTranscript: _lastTranscript,
      ));
    });
  }

  Future<void> dispose() async {
    await stop();
    await _status.close();
    _recorder.dispose();
    engine.dispose();
  }
}
