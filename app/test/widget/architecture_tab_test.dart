import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/project_dependency.dart';
import 'package:app/features/workspace/domain/project_file.dart';
import 'package:app/features/workspace/presentation/tabs/architecture_tab.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

void main() {
  final testFiles = [
    const ProjectFile(
      id: 'f1',
      snapshotId: 's1',
      path: 'src/requests/sessions.py',
      filename: 'sessions.py',
      extension: '.py',
      language: 'Python',
      sizeBytes: 1000,
      contentHash: 'h1',
      isBinary: false,
      isGenerated: false,
      isTest: false,
      lineCount: 780,
      parserSupported: true,
    ),
    const ProjectFile(
      id: 'f2',
      snapshotId: 's1',
      path: 'src/requests/adapters.py',
      filename: 'adapters.py',
      extension: '.py',
      language: 'Python',
      sizeBytes: 800,
      contentHash: 'h2',
      isBinary: false,
      isGenerated: false,
      isTest: false,
      lineCount: 450,
      parserSupported: true,
    ),
    const ProjectFile(
      id: 'f3',
      snapshotId: 's1',
      path: 'src/requests/api.py',
      filename: 'api.py',
      extension: '.py',
      language: 'Python',
      sizeBytes: 400,
      contentHash: 'h3',
      isBinary: false,
      isGenerated: false,
      isTest: false,
      lineCount: 150,
      parserSupported: true,
    ),
  ];

  final testDeps = [
    // api.py -> sessions.py
    const ProjectDependency(
      id: 'd1',
      sourceFileId: 'f3',
      targetFileId: 'f1',
      dependencyType: 'IMPORT',
      lineNumber: 10,
      sourcePath: 'src/requests/api.py',
      targetPath: 'src/requests/sessions.py',
    ),
    // sessions.py -> adapters.py
    const ProjectDependency(
      id: 'd2',
      sourceFileId: 'f1',
      targetFileId: 'f2',
      dependencyType: 'IMPORT',
      lineNumber: 25,
      sourcePath: 'src/requests/sessions.py',
      targetPath: 'src/requests/adapters.py',
    ),
    // adapters.py -> urllib3 (external)
    const ProjectDependency(
      id: 'd3',
      sourceFileId: 'f2',
      externalPackage: 'urllib3',
      dependencyType: 'IMPORT',
      lineNumber: 5,
      sourcePath: 'src/requests/adapters.py',
    ),
  ];

  testWidgets('ArchitectureTab renders components, callers, and dependencies', (tester) async {
    int? navigatedTab;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectDependenciesProvider('proj-1').overrideWith(
            (ref) async => testDeps,
          ),
          projectFilesProvider('proj-1').overrideWith(
            (ref) async => testFiles,
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: ArchitectureTab(
              projectId: 'proj-1',
              projectName: 'requests',
              onNavigateToTab: (index) {
                navigatedTab = index;
              },
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Header
    expect(find.text('Component Relationships'), findsOneWidget);
    expect(find.text('3 components • 3 dependency edges'), findsOneWidget);

    // Verify component list rendering
    expect(find.text('sessions.py'), findsOneWidget);
    expect(find.text('adapters.py'), findsOneWidget);
    expect(find.text('api.py'), findsOneWidget);

    // Select adapters.py
    await tester.tap(find.text('adapters.py'));
    await tester.pumpAndSettle();

    // Verify Relationship Inspector for adapters.py
    expect(find.text('Used by'), findsOneWidget);
    expect(find.text('1 files'), findsOneWidget);
    expect(find.text('src/requests/sessions.py'), findsWidgets);

    expect(find.text('Depends on'), findsOneWidget);
    expect(find.text('1 imports'), findsOneWidget);
    expect(find.text('urllib3'), findsOneWidget);
    expect(find.text('EXTERNAL'), findsOneWidget);

    // Test Open in Files navigation action
    final openFilesBtn = find.text('Open in Files');
    expect(openFilesBtn, findsOneWidget);
    await tester.tap(openFilesBtn);
    await tester.pumpAndSettle();

    expect(navigatedTab, 3);
  });
}
