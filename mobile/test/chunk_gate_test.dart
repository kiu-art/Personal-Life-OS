import 'package:flutter_test/flutter_test.dart';
import 'package:personality_life_os/services/chunk_gate.dart';
import 'package:personality_life_os/services/notification_ingest.dart';

void main() {
  group('ChunkGate.shouldIngest', () {
    test('drops blanks and one-word noise', () {
      expect(ChunkGate.shouldIngest('', null), isFalse);
      expect(ChunkGate.shouldIngest('   ', null), isFalse);
      expect(ChunkGate.shouldIngest('hmm', null), isFalse);
      expect(ChunkGate.shouldIngest('yes ok', null), isFalse);
    });

    test('drops exact repeats of the previous chunk', () {
      const text = 'standup moved to eleven thirty tomorrow morning';
      expect(ChunkGate.shouldIngest(text, text), isFalse);
      expect(
          ChunkGate.shouldIngest(text, 'something else entirely here'),
          isTrue);
    });

    test('drops stock whisper hallucinations', () {
      expect(
          ChunkGate.shouldIngest(
              'Thanks for watching this video now', null),
          isFalse);
    });

    test('keeps real multilingual utterances', () {
      expect(
          ChunkGate.shouldIngest(
              'Bixy main thoda late ho gaya aaj', null),
          isTrue);
      expect(
          ChunkGate.shouldIngest('mala ushir zhala ahe khup kaam aahe',
              null),
          isTrue);
      expect(
          ChunkGate.shouldIngest(
              'Dev standup thoda delay kardo thirty minutes', null),
          isTrue);
    });

    test('normalize collapses whitespace', () {
      expect(ChunkGate.normalize('  a   b\nc '), 'a b c');
    });
  });

  group('NotificationIngest.channelFor', () {
    test('maps known packages', () {
      expect(NotificationIngest.channelFor('com.whatsapp'), 'WhatsApp');
      expect(
          NotificationIngest.channelFor('com.whatsapp.w4b'), 'WhatsApp');
      expect(NotificationIngest.channelFor('com.google.android.gm'),
          'Gmail');
      expect(NotificationIngest.channelFor('com.other.app'), 'System');
      expect(NotificationIngest.channelFor(null), 'System');
    });
  });
}
