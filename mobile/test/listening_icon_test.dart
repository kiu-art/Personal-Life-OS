import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:personality_life_os/widgets/listening_icon.dart';

void main() {
  group('ListeningIcon', () {
    testWidgets('shows live mic with pulse when listening',
        (WidgetTester tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListeningIcon(
              listening: true,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );
      await tester.pump();
      expect(find.byIcon(Icons.mic_rounded), findsOneWidget);
      expect(find.byIcon(Icons.mic_none_rounded), findsNothing);
      await tester.tap(find.byType(ListeningIcon));
      expect(tapped, isTrue);
    });

    testWidgets('shows quiet mic when paused', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListeningIcon(listening: false, onTap: () {}),
          ),
        ),
      );
      await tester.pump();
      expect(find.byIcon(Icons.mic_none_rounded), findsOneWidget);
      expect(find.byIcon(Icons.mic_rounded), findsNothing);
    });
  });
}
