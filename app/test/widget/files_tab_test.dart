import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/file_detail.dart';
import 'package:app/features/workspace/domain/project_file.dart';
import 'package:app/features/workspace/presentation/tabs/files_tab.dart';
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
      path: 'tests/test_requests.py',
      filename: 'test_requests.py',
      extension: '.py',
      language: 'Python',
      sizeBytes: 500,
      contentHash: 'h3',
      isBinary: false,
      isGenerated: false,
      isTest: true,
      lineCount: 200,
      parserSupported: true,
    ),
  ];

  testWidgets('FilesTab renders tree and handles selection and search filtering', (tester) async {
    ProjectFile? selected;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectFilesProvider('proj-1').overrideWith(
            (ref) async => testFiles,
          ),
          projectFileDetailProvider((projectId: 'proj-1', fileId: 'f1')).overrideWith(
            (ref) async => FileDetail(
              file: testFiles[0],
              fullContent: 'import adapters\nclass Session:\n    pass',
            ),
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: FilesTab(
              projectId: 'proj-1',
              projectName: 'requests',
              onSelectFile: (file) {
                selected = file;
              },
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Header
    expect(find.text('Project Files'), findsOneWidget);
    expect(find.text('3 files tracked in current snapshot'), findsOneWidget);

    // Verify Directory tree nodes
    expect(find.text('src'), findsOneWidget);
    expect(find.text('tests'), findsOneWidget);
    expect(find.text('sessions.py'), findsOneWidget);
    expect(find.text('adapters.py'), findsOneWidget);
    expect(find.text('test_requests.py'), findsOneWidget);
    expect(find.text('TEST'), findsOneWidget);

    // Test selection (opens FileDetailPanel on the right)
    await tester.tap(find.text('sessions.py'));
    await tester.pumpAndSettle();

    expect(selected?.filename, 'sessions.py');
    expect(find.text('src/requests/sessions.py'), findsOneWidget);
    expect(find.text('import adapters'), findsOneWidget);

    // Test Search filtering
    await tester.enterText(find.byType(TextField), 'adapters');
    await tester.pumpAndSettle();

    expect(find.text('adapters.py'), findsOneWidget);
    expect(find.text('test_requests.py'), findsNothing);
  });
}

