import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';

void main() {
  testWidgets('WizardShell renders WelcomeScreen and navigates on Get Started',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Verify Welcome Screen elements
    expect(find.text('Unotusk Server Setup'), findsOneWidget);
    expect(find.text('Unotusk Server'), findsOneWidget);
    expect(
        find.text('Install Unotusk inside your company infrastructure.'),
        findsOneWidget);
    expect(find.text('Get Started'), findsOneWidget);

    // Click Get Started
    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();

    // Verify transition to Target step
    expect(find.text('Where should Unotusk run?'), findsOneWidget);
    expect(find.text('Back'), findsOneWidget);

    // Click Back
    await tester.tap(find.text('Back'));
    await tester.pumpAndSettle();

    // Verify returned to Welcome
    expect(find.text('Get Started'), findsOneWidget);
  });
}
