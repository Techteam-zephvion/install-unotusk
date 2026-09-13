import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/deploy/data/deployment_engine.dart';
import 'package:setup_app/features/deploy/presentation/deploy_controller.dart';
import 'package:setup_app/features/validation/data/environment_validator.dart';
import 'package:setup_app/features/validation/presentation/server_check_controller.dart';
import 'package:setup_app/features/verify/data/health_verifier.dart';
import 'package:setup_app/features/verify/presentation/verify_controller.dart';

class _FakeHealthVerifier extends HealthVerifier {
  @override
  Future<HealthStatus> pollUntilReady(
    String serverUrl, {
    int maxAttempts = 20,
    Duration interval = const Duration(seconds: 2),
    void Function(int attempt, HealthStatus status)? onPoll,
  }) async {
    return const HealthStatus(
      isHealthy: true,
      isReady: true,
      databaseStatus: 'connected',
      redisStatus: 'connected',
      version: '0.1.0',
    );
  }
}

void main() {
  testWidgets('VerifyScreen shows running state and enables Continue to Ready', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final mockValidator = EnvironmentValidator(
      processExecutor: (exec, args, {workingDirectory, environment}) async =>
          ProcessResult(1234, 0, 'ok', ''),
      socketTester: (host, port) async => true,
    );

    final mockEngine = DeploymentEngine(
      processExecutor: (exec, args, {workingDirectory, environment}) async =>
          ProcessResult(1234, 0, 'ok', ''),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          environmentValidatorProvider.overrideWithValue(mockValidator),
          deploymentEngineProvider.overrideWithValue(mockEngine),
          healthVerifierProvider.overrideWithValue(_FakeHealthVerifier()),
        ],
        child: const UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Welcome -> Target
    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();

    // Target -> Check Server
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    // Check Server -> Configure
    await tester.tap(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.pumpAndSettle();

    // Fill Configure form
    final textFields = find.byType(TextFormField);
    await tester.enterText(textFields.at(2), 'admin@unotusk.internal');
    await tester.enterText(textFields.at(3), 'adminpass123');
    await tester.enterText(textFields.at(4), 'gsk_test_api_key_123');
    await tester.pumpAndSettle();

    // Configure -> Install
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 700));
    await tester.pumpAndSettle();

    // Install auto-transitions to Verify
    expect(find.text('Verifying Server Health'), findsWidgets);
    expect(find.text('Running'), findsOneWidget);
    expect(find.text('Server Address'), findsOneWidget);
    expect(find.text('Database'), findsOneWidget);
    expect(find.text('Redis Cache & Queue'), findsOneWidget);

    // Tap Continue -> advances to Ready
    final continueBtn = find.widgetWithText(ElevatedButton, 'Continue');
    expect(tester.widget<ElevatedButton>(continueBtn).enabled, true);
    await tester.tap(continueBtn);
    await tester.pumpAndSettle();

    expect(find.text('Unotusk is ready.'), findsWidgets);
  });
}
