import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/validation/data/environment_validator.dart';
import 'package:setup_app/features/validation/presentation/server_check_controller.dart';

void main() {
  testWidgets('TargetScreen allows selecting local and remote targets', (WidgetTester tester) async {
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

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          environmentValidatorProvider.overrideWithValue(mockValidator),
        ],
        child: const UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Click Get Started on Welcome Screen
    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();

    expect(find.text('Where should Unotusk run?'), findsOneWidget);
    expect(find.text('This computer'), findsOneWidget);
    expect(find.text('Remote Linux server'), findsOneWidget);

    // Switch to Remote
    await tester.tap(find.text('Remote Linux server'));
    await tester.pumpAndSettle();

    expect(find.text('SSH Connection Details'), findsOneWidget);

    // Click Continue without credentials -> validation error
    await tester.ensureVisible(find.text('Continue'));
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Please enter a valid remote hostname or IP address.'), findsOneWidget);

    // Switch back to Local
    await tester.ensureVisible(find.text('This computer'));
    await tester.tap(find.text('This computer'));
    await tester.pumpAndSettle();

    // Click Continue -> proceeds to Check step
    await tester.ensureVisible(find.text('Continue'));
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Check Server'), findsWidgets);
  });
}
