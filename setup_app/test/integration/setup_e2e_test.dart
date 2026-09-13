import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/deploy/data/deployment_engine.dart';
import 'package:setup_app/features/deploy/presentation/deploy_controller.dart';
import 'package:setup_app/features/ready/data/app_launcher.dart';
import 'package:setup_app/features/ready/presentation/ready_screen.dart';
import 'package:setup_app/features/validation/data/environment_validator.dart';
import 'package:setup_app/features/validation/presentation/server_check_controller.dart';
import 'package:setup_app/features/verify/data/health_verifier.dart';
import 'package:setup_app/features/verify/presentation/verify_controller.dart';

class MockAppLauncher extends AppLauncher {
  bool launched = false;
  @override
  Future<bool> launchEmployeeApp({String? serverUrl}) async {
    launched = true;
    return true;
  }
}

class FakeHealthVerifier extends HealthVerifier {
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
  group('Unotusk Server Setup Wizard E2E Integration Tests', () {
    testWidgets('Full End-to-End Wizard Flow completes successfully from Welcome to Ready', (tester) async {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockAppLauncher = MockAppLauncher();

      final mockValidator = EnvironmentValidator(
        processExecutor: (exec, args, {workingDirectory, environment}) async =>
            ProcessResult(1234, 0, 'Docker version 24.0.5', ''),
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
            healthVerifierProvider.overrideWithValue(FakeHealthVerifier()),
            appLauncherProvider.overrideWithValue(mockAppLauncher),
          ],
          child: const UnotuskSetupApp(),
        ),
      );
      await tester.pumpAndSettle();

      // --- 1. Welcome Screen ---
      expect(find.text('Unotusk Server Setup'), findsOneWidget);
      expect(find.text('Get Started'), findsOneWidget);

      await tester.tap(find.text('Get Started'));
      await tester.pumpAndSettle();

      // --- 2. Target Screen ---
      expect(find.text('Where should Unotusk run?'), findsOneWidget);
      expect(find.text('This computer'), findsOneWidget);
      expect(find.text('Remote Linux server'), findsOneWidget);

      // Tap Continue to proceed with Local host
      await tester.ensureVisible(find.text('Continue'));
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();

      // --- 3. Server Check Screen ---
      expect(find.text('Check Server'), findsWidgets);
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();

      final checkContinueBtn = find.widgetWithText(ElevatedButton, 'Continue');
      await tester.ensureVisible(checkContinueBtn);
      await tester.tap(checkContinueBtn);
      await tester.pumpAndSettle();

      // --- 4. Config Screen ---
      expect(find.text('Configuration'), findsWidgets);

      final textFields = find.byType(TextFormField);
      expect(textFields, findsNWidgets(5));

      // Enter valid config: email, password, api key
      await tester.enterText(textFields.at(2), 'admin@unotusk.internal');
      await tester.enterText(textFields.at(3), 'SecureP@ssw0rd2026!');
      await tester.enterText(textFields.at(4), 'gsk_test_api_key_1234567890');
      await tester.pumpAndSettle();

      final configContinueBtn = find.widgetWithText(ElevatedButton, 'Continue');
      await tester.ensureVisible(configContinueBtn);
      await tester.tap(configContinueBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 700));
      await tester.pumpAndSettle();

      // --- 5 & 6. Deploy & Verify Screen ---
      expect(find.text('Verifying Server Health'), findsWidgets);
      expect(find.text('Running'), findsOneWidget);

      // Tap Continue to Ready
      final verifyContinueBtn = find.widgetWithText(ElevatedButton, 'Continue');
      expect(tester.widget<ElevatedButton>(verifyContinueBtn).enabled, true);
      await tester.tap(verifyContinueBtn);
      await tester.pumpAndSettle();

      // --- 7. Ready Screen ---
      expect(find.text('Unotusk is ready.'), findsWidgets);
      expect(find.text('http://localhost:8000'), findsOneWidget);
      expect(find.text('Copy'), findsOneWidget);
      expect(find.text('Open Employee App'), findsOneWidget);

      // Test Open Employee App action
      await tester.tap(find.text('Open Employee App'));
      await tester.pump(const Duration(milliseconds: 100));

      expect(mockAppLauncher.launched, isTrue);
    });
  });
}
