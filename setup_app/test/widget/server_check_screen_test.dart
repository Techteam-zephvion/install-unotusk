import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/validation/data/environment_validator.dart';
import 'package:setup_app/features/validation/presentation/server_check_controller.dart';

void main() {
  testWidgets('ServerCheckScreen executes all prerequisite checks and enables Continue on pass',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final mockValidator = EnvironmentValidator(
      processExecutor: (exec, args, {workingDirectory, environment}) async {
        return ProcessResult(1234, 0, 'Docker version 27.0.0', '');
      },
      socketTester: (host, port) async => true,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          environmentValidatorProvider.overrideWithValue(mockValidator),
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

    // Verify Check Server UI
    expect(find.text('Check Server'), findsWidgets);
    expect(find.text('Machine reachable'), findsOneWidget);
    expect(find.text('Required runtime available'), findsOneWidget);
    expect(find.text('Docker Compose available'), findsOneWidget);
    expect(find.text('Storage available'), findsOneWidget);
    expect(find.text('Required ports available'), findsOneWidget);

    // Continue button is enabled
    final continueFinder = find.widgetWithText(ElevatedButton, 'Continue');
    expect(tester.widget<ElevatedButton>(continueFinder).enabled, true);

    // Tap continue to go to Configure step
    await tester.tap(continueFinder);
    await tester.pumpAndSettle();

    expect(find.text('Configuration'), findsWidgets);
  });

  testWidgets('ServerCheckScreen shows Use Existing Server and Configure Alternate Port when existing deployment detected',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final mockValidator = EnvironmentValidator(
      processExecutor: (exec, args, {workingDirectory, environment}) async {
        return ProcessResult(1234, 0, 'Docker version 27.0.0', '');
      },
      socketTester: (host, port) async => false, // Port 8000 is occupied
      httpHealthChecker: (host, port) async => true, // Existing Unotusk
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          environmentValidatorProvider.overrideWithValue(mockValidator),
        ],
        child: const UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Welcome -> Target -> Check Server
    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    // Verify Check Server UI identifies existing Unotusk and shows resolution buttons
    expect(find.text('Required ports available Failed'), findsOneWidget);
    expect(find.text('Use Existing Server'), findsOneWidget);
    expect(find.text('Configure Alternate Port'), findsOneWidget);

    // Tap Use Existing Server -> jumps to Verify step
    await tester.tap(find.text('Use Existing Server'));
    await tester.pumpAndSettle();

    expect(find.text('Verifying Server Health'), findsWidgets);
  });
}
