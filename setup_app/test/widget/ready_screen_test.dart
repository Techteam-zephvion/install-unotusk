import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/config/presentation/config_controller.dart';
import 'package:setup_app/features/ready/data/app_launcher.dart';
import 'package:setup_app/features/ready/presentation/ready_screen.dart';
import 'package:setup_app/features/wizard/domain/wizard_step.dart';
import 'package:setup_app/features/wizard/presentation/wizard_controller.dart';

void main() {
  testWidgets('ReadyScreen displays server URL, copies address, and triggers app launch',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final mockLauncher = AppLauncher(
      processExecutor: (exec, args, {workingDirectory, environment}) async =>
          ProcessResult(1234, 0, '', ''),
    );

    final container = ProviderContainer(
      overrides: [
        appLauncherProvider.overrideWithValue(mockLauncher),
      ],
    );
    container.read(configControllerProvider.notifier).updateServerPort('8000');
    container.read(wizardControllerProvider.notifier).setStep(WizardStep.ready);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Unotusk is ready.'), findsOneWidget);
    expect(find.text('http://localhost:8000'), findsOneWidget);
    expect(find.text('Copy'), findsOneWidget);
    expect(find.text('Open Employee App'), findsOneWidget);

    // Click Copy
    await tester.tap(find.text('Copy'));
    await tester.pump();

    expect(find.text('Copied'), findsOneWidget);

    // Advance past the 2-second feedback timer
    await tester.pump(const Duration(seconds: 3));

    // Click Open Employee App
    await tester.tap(find.text('Open Employee App'));
    await tester.pump();
  });

  testWidgets('ReadyScreen dynamically resolves LAN IP and displays LAN Server URL with badge',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final mockLauncher = AppLauncher(
      processExecutor: (exec, args, {workingDirectory, environment}) async =>
          ProcessResult(1234, 0, '', ''),
    );

    final container = ProviderContainer(
      overrides: [
        appLauncherProvider.overrideWithValue(mockLauncher),
      ],
    );
    container.read(configControllerProvider.notifier).updateServerPort('8000');
    container.read(configControllerProvider.notifier).updateLanIp('10.0.0.59');
    container.read(wizardControllerProvider.notifier).setStep(WizardStep.ready);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const UnotuskSetupApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Unotusk is ready.'), findsOneWidget);
    expect(find.text('LAN Server URL (Employee Clients)'), findsOneWidget);
    expect(find.text('LAN REACHABLE'), findsOneWidget);
    expect(find.text('http://10.0.0.59:8000'), findsOneWidget);
    expect(find.text('Local host address: '), findsOneWidget);
    expect(find.text('http://localhost:8000'), findsOneWidget);
  });
}
