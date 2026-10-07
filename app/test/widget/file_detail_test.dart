import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/file_detail.dart';
import 'package:app/features/workspace/domain/project_dependency.dart';
import 'package:app/features/workspace/domain/project_file.dart';
import 'package:app/features/workspace/domain/project_symbol.dart';
import 'package:app/features/workspace/presentation/widgets/file_detail_panel.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

void main() {
  const testFile = ProjectFile(
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
  );

  final testDetail = FileDetail(
    file: testFile,
    symbols: [
      const ProjectSymbol(
        id: 'sym-1',
        fileId: 'f1',
        name: 'Session',
        symbolType: 'CLASS',
        qualifiedName: 'requests.sessions.Session',
        startLine: 350,
        endLine: 620,
      ),
    ],
    outgoingDependencies: [
      const ProjectDependency(
        id: 'dep-1',
        sourceFileId: 'f1',
        targetFileId: 'f2',
        dependencyType: 'IMPORT',
        lineNumber: 24,
        sourcePath: 'src/requests/sessions.py',
        targetPath: 'src/requests/adapters.py',
      ),
    ],
    incomingReferences: [
      const ProjectDependency(
        id: 'dep-2',
        sourceFileId: 'f3',
        targetFileId: 'f1',
        dependencyType: 'IMPORT',
        lineNumber: 12,
        sourcePath: 'src/requests/api.py',
        targetPath: 'src/requests/sessions.py',
      ),
    ],
    fullContent: 'import adapters\n\nclass Session:\n    def __init__(self):\n        pass\n',
  );

  testWidgets('FileDetailPanel renders code, switches to symbols and dependencies', (tester) async {
    bool closed = false;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectFileDetailProvider((projectId: 'proj-1', fileId: 'f1')).overrideWith(
            (ref) async => testDetail,
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: FileDetailPanel(
              projectId: 'proj-1',
              file: testFile,
              onClose: () {
                closed = true;
              },
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Header
    expect(find.text('sessions.py'), findsOneWidget);
    expect(find.text('src/requests/sessions.py'), findsOneWidget);

    // Verify Code View initially
    expect(find.text('import adapters'), findsOneWidget);
    expect(find.text('class Session:'), findsOneWidget);

    // Switch to Symbols segment
    await tester.tap(find.text('Symbols'));
    await tester.pumpAndSettle();

    expect(find.text('Session'), findsOneWidget);
    expect(find.text('requests.sessions.Session'), findsOneWidget);
    expect(find.text('L350-620'), findsOneWidget);

    // Switch to Dependencies segment
    await tester.tap(find.text('Dependencies'));
    await tester.pumpAndSettle();

    expect(find.text('Depends on (1)'), findsOneWidget);
    expect(find.text('src/requests/adapters.py'), findsOneWidget);
    expect(find.text('Used by (1 files)'), findsOneWidget);
    expect(find.text('src/requests/api.py'), findsOneWidget);

    // Test close button
    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();

    expect(closed, isTrue);
  });
}
