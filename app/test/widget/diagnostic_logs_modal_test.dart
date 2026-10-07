import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/core/logging/app_logger.dart';
import 'package:app/core/logging/diagnostic_logs_modal.dart';

void main() {
  testWidgets('DiagnosticLogsModal renders empty state and logs when available', (tester) async {
    final logger = AppLogger(osName: 'linux');
    logger.info(
      AppLogEvent.serverConnectionSuccess,
      message: 'Connected to http://10.0.0.59:8000',
      metadata: {'ping_ms': 12},
    );
    logger.error(
      AppLogEvent.serverConnectionFailure,
      message: 'Failed to reach http://10.0.0.99:8000',
      metadata: {'error': 'Connection timed out'},
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appLoggerProvider.overrideWithValue(logger),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: DiagnosticLogsModal(),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Diagnostic Event Logs'), findsOneWidget);
    expect(find.text('2 / 500 EVENTS'), findsOneWidget);
    expect(find.text('SERVER_CONNECTION_SUCCESS'), findsOneWidget);
    expect(find.text('SERVER_CONNECTION_FAILURE'), findsOneWidget);
    expect(find.text('Connected to http://10.0.0.59:8000'), findsOneWidget);
    expect(find.text('Copy All Logs'), findsOneWidget);
    expect(find.text('Clear'), findsOneWidget);
  });
}
