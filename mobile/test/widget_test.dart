import 'package:flutter_test/flutter_test.dart';
import 'package:personality_life_os/main.dart';

void main() {
  testWidgets('Bixy App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const BixyApp());
    await tester.pump();
    expect(find.text('Today'), findsOneWidget);
    expect(find.text('Add task'), findsOneWidget);
    expect(find.text('Ask Bixy'), findsOneWidget);
  });
}
