import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/deploy/data/deployment_engine.dart';
import 'package:setup_app/features/deploy/presentation/deploy_controller.dart';
import 'package:setup_app/features/validation/data/environment_validator.dart';
import 'package:setup_app/features/validation/presentation/server_check_controller.dart';

void main() {
  testWidgets('DeployScreen shows stages and auto-transitions on success', (WidgetTester tester) async {
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
    await tester.pumpAndSettle();

    // Auto-advances to Verify step on mock completion
    expect(find.text('Verifying Server Health'), findsWidgets);
  });
}
