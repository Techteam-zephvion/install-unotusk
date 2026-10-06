import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:setup_app/app/app.dart';
import 'package:setup_app/features/manager/data/server_manager_controller.dart';
import 'package:setup_app/features/manager/data/server_registry.dart';

void main() {
  testWidgets('UnotuskSetupApp boots and displays Server Manager view', (WidgetTester tester) async {
    final mockRegistry = ServerRegistry(
      processExecutor: (
        executable,
        arguments, {
        workingDirectory,
        environment,
        includeParentEnvironment = true,
        runInShell = false,
        stdoutEncoding = systemEncoding,
        stderrEncoding = systemEncoding,
      }) async {
        return ProcessResult(0, 0, '', '');
      },
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          serverRegistryProvider.overrideWithValue(mockRegistry),
        ],
        child: const UnotuskSetupApp(),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Unotusk Server Manager'), findsOneWidget);
    expect(find.text('Add Server'), findsOneWidget);
  });
}
