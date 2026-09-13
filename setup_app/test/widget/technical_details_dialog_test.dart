import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/core/widgets/error_state_card.dart';

void main() {
  testWidgets('ErrorStateCard opens TechnicalDetailsDialog and redacts secrets in logs',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: ErrorStateCard(
              title: 'Container failed',
              message: 'Docker failed to bind port.',
              technicalLogs: 'Error on postgresql://postgres:SecretDbPassword123@db:5432 with gsk_99998888777766665555',
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Container failed'), findsOneWidget);
    expect(find.text('Docker failed to bind port.'), findsOneWidget);
    expect(find.text('View technical details'), findsOneWidget);

    // Open technical details dialog
    await tester.tap(find.text('View technical details'));
    await tester.pumpAndSettle();

    // Verify dialog header
    expect(find.text('Container failed — Diagnostics'), findsOneWidget);

    // Verify sensitive values are sanitized
    expect(find.textContaining('SecretDbPassword123'), findsNothing);
    expect(find.textContaining('gsk_99998888777766665555'), findsNothing);
    expect(find.textContaining('[REDACTED]'), findsOneWidget);

    // Close dialog
    await tester.tap(find.text('Close'));
    await tester.pumpAndSettle();

    expect(find.text('Container failed — Diagnostics'), findsNothing);
  });
}
