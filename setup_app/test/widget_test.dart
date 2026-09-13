import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';

void main() {
  testWidgets('UnotuskSetupApp boots and displays welcome view', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Unotusk Server Setup'), findsOneWidget);
    expect(find.text('Unotusk Server'), findsOneWidget);
    expect(find.text('Install Unotusk inside your company infrastructure.'), findsOneWidget);
    expect(find.text('Get Started'), findsOneWidget);
  });
}
