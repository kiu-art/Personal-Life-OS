import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

// NOTE (build-time verification needed): the sherpa_onnx Dart binding below
// follows the long-stable 1.x API (OfflineRecognizer / OfflineModelConfig /
// OfflineWhisperModelConfig / createStream / acceptWaveform / decode /
// getResult / free). Confirm exact constructor/field names against the
// resolved pub-cache source on the first `flutter pub get` + build.

/// Whisper model presets, downloaded once into app storage.
enum WhisperPreset {
  tiny(
    asset: 'sherpa-onnx-whisper-tiny.tar.bz2',
    bytes: 75000000,
    blurb: '~75 MB',
  ),
  base(
    asset: 'sherpa-onnx-whisper-base.tar.bz2',
    bytes: 145000000,
    blurb: '~145 MB',
  );

  const WhisperPreset({
    required this.asset,
    required this.bytes,
    required this.blurb,
  });

  final String asset;
  final int bytes;
  final String blurb;

  String get url =>
      'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$asset';
}

/// Downloads + extracts the Whisper bundle, then locates encoder/decoder/
/// tokens by scan (robust to upstream file renames inside the tarball).
class WhisperModelManager {
  WhisperPreset preset;

  WhisperModelManager({this.preset = WhisperPreset.tiny});

  Future<Directory> _baseDir() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/sherpa_models/${preset.name}');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  /// Resolved (encoder, decoder, tokens) paths, or null when not downloaded.
  Future<({String encoder, String decoder, String tokens})?> resolved() async {
    final dir = await _baseDir();
    final files = dir.listSync().whereType<File>().toList();
    final onnx =
        files.where((f) => f.path.endsWith('.onnx')).map((f) => f.path);
    final tok = files
        .where((f) => f.path.endsWith('tokens.txt'))
        .map((f) => f.path)
        .toList();
    final enc = onnx.where((p) => p.contains('encoder')).toList();
    final dec = onnx.where((p) => p.contains('decoder')).toList();
    if (enc.isEmpty || dec.isEmpty || tok.isEmpty) return null;
    return (encoder: enc.first, decoder: dec.first, tokens: tok.first);
  }

  Future<bool> get isReady async => await resolved() != null;

  /// Downloads the bundle with progress callbacks, then extracts it.
  Future<void> download({void Function(double progress)? onProgress}) async {
    final dir = await _baseDir();
    final client = http.Client();
    try {
      final req = http.Request('GET', Uri.parse(preset.url));
      final res = await client.send(req);
      if (res.statusCode != 200) {
        throw Exception('Model download failed: HTTP ${res.statusCode}');
      }
      final total = res.contentLength ?? preset.bytes;
      final bytes = <int>[];
      await for (final chunk in res.stream) {
        bytes.addAll(chunk);
        onProgress?.call(bytes.length / total);
      }
      final archive =
          TarDecoder().decodeBytes(BZip2Decoder().decodeBytes(bytes));
      for (final file in archive.files) {
        if (!file.isFile) continue;
        final name = file.name.split('/').last;
        if (name.isEmpty) continue;
        await File('${dir.path}/$name')
            .writeAsBytes(file.content as List<int>);
      }
    } finally {
      client.close();
    }
    if (await resolved() == null) {
      throw Exception('Model bundle extracted but encoder/decoder missing');
    }
  }
}

/// Minimal STT interface so the ambient loop never depends on one engine.
abstract class SttEngine {
  Future<void> init();
  Future<bool> get ready;
  Future<String> transcribeFile(String wavPath);
  void dispose();
}

/// Offline Whisper (multilingual: Hindi/English/Marathi + code-switch)
/// running fully on-device through sherpa-onnx.
class SherpaWhisperEngine implements SttEngine {
  final WhisperModelManager models;
  final String language;

  /// `language` biases Whisper decoding ('en' still transcribes Hindi/
  /// Hinglish words; the backend keyword gate already reads romanized
  /// Hindi/Marathi). Keep 'en' unless a single-language install is wanted.
  SherpaWhisperEngine({WhisperModelManager? models, this.language = 'en'})
      : models = models ?? WhisperModelManager();

  sherpa.OfflineRecognizer? _recognizer;
  static bool _bindingsReady = false;

  @override
  Future<bool> get ready async =>
      _recognizer != null && await models.isReady;

  @override
  Future<void> init() async {
    if (_recognizer != null) return;
    // Required once per isolate before any sherpa_onnx API is touched;
    // without it every call throws "Please initialize sherpa-onnx first".
    if (!_bindingsReady) {
      sherpa.initBindings();
      _bindingsReady = true;
    }
    final files = await models.resolved();
    if (files == null) {
      throw StateError('Whisper model not downloaded yet');
    }
    final modelConfig = sherpa.OfflineModelConfig(
      whisper: sherpa.OfflineWhisperModelConfig(
        encoder: files.encoder,
        decoder: files.decoder,
        language: language,
        task: 'transcribe',
      ),
      tokens: files.tokens,
      numThreads: 2,
      debug: false,
    );
    final config = sherpa.OfflineRecognizerConfig(
      model: modelConfig,
      decodingMethod: 'greedy_search',
      maxActivePaths: 4,
    );
    _recognizer = sherpa.OfflineRecognizer(config);
  }

  @override
  Future<String> transcribeFile(String wavPath) async {
    final rec = _recognizer;
    if (rec == null) throw StateError('Engine not initialised');
    final samples = await _readMono16k(wavPath);
    if (samples.isEmpty) return '';
    final stream = rec.createStream();
    stream.acceptWaveform(samples: samples, sampleRate: 16000);
    rec.decode(stream);
    final text = rec.getResult(stream).text;
    stream.free();
    return text.trim();
  }

  /// Reads a 16-bit PCM mono WAV (as written by `record`) into float samples.
  static Future<Float32List> _readMono16k(String path) async {
    final bytes = await File(path).readAsBytes();
    if (bytes.length < 44) return Float32List(0);
    final data = bytes.sublist(44);
    final count = data.length ~/ 2;
    final out = Float32List(count);
    final view = ByteData.sublistView(Uint8List.fromList(data));
    for (var i = 0; i < count; i++) {
      out[i] = view.getInt16(i * 2, Endian.little) / 32768.0;
    }
    return out;
  }

  @override
  void dispose() {
    _recognizer?.free();
    _recognizer = null;
  }
}
