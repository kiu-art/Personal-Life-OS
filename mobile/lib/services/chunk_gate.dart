/// Pure helpers for the ambient-listening pipeline.
///
/// Plugin-free on purpose: every function here is unit-testable without a
/// device, microphone, or model download.
class ChunkGate {
  /// Minimum words for a transcript to be worth sending upstream.
  static const int minWords = 3;

  /// Should this transcript be ingested? Drops blanks, mic noise
  /// one-liners, and exact repeats of the previous chunk.
  static bool shouldIngest(String transcript, String? previousSent) {
    final text = transcript.trim();
    if (text.isEmpty) return false;
    if (text == previousSent?.trim()) return false;
    if (_wordCount(text) < minWords) return false;
    if (_isKnownHallucination(text)) return false;
    return true;
  }

  /// Normalize a raw chunk transcript for transport.
  static String normalize(String transcript) {
    return transcript.trim().replaceAll(RegExp(r'\s+'), ' ');
  }

  static int _wordCount(String text) {
    return text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).length;
  }

  /// Whisper models emit stock phrases on silence/noise; never ingest those.
  static bool _isKnownHallucination(String text) {
    const stock = {
      'thanks for watching',
      'thank you for watching',
      'thanks for listening',
      'subtitle by',
      'subtitles by',
    };
    final lower = text.toLowerCase();
    return stock.any((s) => lower.contains(s));
  }
}
