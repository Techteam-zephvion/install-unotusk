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
  testWidgets('ConfigScreen validates inputs and proceeds on valid entry', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final mockValidator = EnvironmentValidator(
      processExecutor: (exec, args, {workingDirectory, environment}) async {
        return ProcessResult(1234, 0, 'ok', '');
      },
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

    expect(find.text('Configuration'), findsWidgets);
    expect(find.text('General Settings'), findsOneWidget);
    expect(find.text('Initial Admin User'), findsOneWidget);
    expect(find.text('Intelligence & LLM Engine'), findsOneWidget);

    // Tap continue with empty required fields -> shows errors
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Please enter a valid admin email address.'), findsOneWidget);

    // Enter valid credentials into fields
    final textFields = find.byType(TextFormField);
    expect(textFields, findsNWidgets(5));

    // Field 2 is Email
    await tester.enterText(textFields.at(2), 'admin@unotusk.internal');
    // Field 3 is Password
    await tester.enterText(textFields.at(3), 'adminpass123');
    // Field 4 is API Key
    await tester.enterText(textFields.at(4), 'gsk_test_api_key_123');

    await tester.pumpAndSettle();

    // Tap continue -> proceeds to Install step
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Continue'));
    await tester.pump();

    expect(find.text('Installing Unotusk'), findsWidgets);

    // Drain all pending timers
    await tester.pumpAndSettle(const Duration(seconds: 1));
  });
}
