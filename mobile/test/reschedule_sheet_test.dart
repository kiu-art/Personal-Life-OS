import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:personality_life_os/widgets/reschedule_sheet.dart';

void main() {
  group('RescheduleSheet', () {
    testWidgets('shows readout, presets apply on tap',
        (WidgetTester tester) async {
      int? applied;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RescheduleSheet(
              initialShiftMinutes: 0,
              onShiftApplied: (mins) => applied = mins,
            ),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('Move day'), findsOneWidget);
      expect(find.text('On time'), findsOneWidget);
      await tester.tap(find.text('+30'));
      await tester.pump();
      expect(find.text('+30 min'), findsOneWidget);
      await tester.tap(find.text('Apply'));
      await tester.pump();
      expect(applied, 30);
    });
  });
}
