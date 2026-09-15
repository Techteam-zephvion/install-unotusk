import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/app/theme/app_theme.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/projects/domain/project.dart';
import 'package:app/features/workspace/domain/repository_context.dart';
import 'package:app/features/workspace/presentation/widgets/ingestion_progress_view.dart';

void main() {
  testWidgets('IngestionProgressView displays phases correctly for active ingestion', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    final project = Project(
      id: 'proj-123',
      name: 'Requests',
      slug: 'requests',
      status: 'CONNECTING',
      updatedAt: DateTime.now(),
    );

    const snapshot = ActiveSnapshot(
      id: 'snap-1',
      repositoryId: 'repo-1',
      commitHash: 'abcdef123456',
      branch: 'main',
      status: 'PARSING',
      totalFiles: 42,
      totalBytes: 10240,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: Scaffold(
            body: IngestionProgressView(
              project: project,
              snapshot: snapshot,
            ),
          ),
        ),
      ),
    );

    await tester.pump();

    expect(find.text('Analyzing Codebase'), findsOneWidget);
    expect(find.text('Cloning Codebase'), findsOneWidget);
    expect(find.text('Scanning File Tree'), findsOneWidget);
    expect(find.text('Parsing AST Symbols'), findsOneWidget);
    expect(find.text('Indexing & Dependency Mapping'), findsOneWidget);
    expect(find.text('Intelligence Engine Online'), findsOneWidget);
  });

  testWidgets('IngestionProgressView shows failure notice and retry button when failed', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    final project = Project(
      id: 'proj-123',
      name: 'Requests',
      slug: 'requests',
      status: 'ERROR',
      updatedAt: DateTime.now(),
    );

    const snapshot = ActiveSnapshot(
      id: 'snap-1',
      repositoryId: 'repo-1',
      commitHash: '',
      branch: 'main',
      status: 'FAILED',
      totalFiles: 0,
      totalBytes: 0,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: Scaffold(
            body: IngestionProgressView(
              project: project,
              snapshot: snapshot,
            ),
          ),
        ),
      ),
    );

    await tester.pump();

    expect(find.text('Ingestion Encountered an Issue'), findsOneWidget);
    expect(find.text('Retry Ingestion'), findsOneWidget);
  });
}
