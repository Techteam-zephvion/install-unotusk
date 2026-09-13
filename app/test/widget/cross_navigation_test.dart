import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/projects/domain/project.dart';
import 'package:app/features/projects/presentation/projects_controller.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/discovery_summary.dart';
import 'package:app/features/workspace/domain/file_detail.dart';
import 'package:app/features/workspace/domain/grounded_answer.dart';
import 'package:app/features/workspace/domain/project_dependency.dart';
import 'package:app/features/workspace/domain/project_file.dart';
import 'package:app/features/workspace/domain/project_finding.dart';
import 'package:app/features/workspace/domain/project_knowledge.dart';
import 'package:app/features/workspace/domain/project_symbol.dart';
import 'package:app/features/workspace/domain/repository_context.dart';
import 'package:app/features/workspace/presentation/workspace_screen.dart';

class _CrossNavFakeRepository extends Fake implements WorkspaceRepository {
  @override
  Future<ProjectRepositoryContext> getProjectRepositoryContext(String projectId) async {
    return const ProjectRepositoryContext(
      metrics: ProjectContextMetrics(
        totalFiles: 1,
        symbolsCount: 1,
        dependenciesCount: 1,
        languageDistribution: {'Python': 1},
      ),
    );
  }

  @override
  Future<List<ProjectFile>> getProjectFiles(String projectId, {int limit = 500}) async {
    return const [
      ProjectFile(
        id: 'file-1',
        snapshotId: 's1',
        path: 'src/requests/adapters.py',
        filename: 'adapters.py',
        extension: 'py',
        language: 'Python',
        sizeBytes: 1024,
        contentHash: 'hash1',
        isBinary: false,
        isGenerated: false,
        isTest: false,
        lineCount: 80,
        parserSupported: true,
      ),
    ];
  }

  @override
  Future<FileDetail> getFileDetail(String projectId, String fileId) async {
    const file = ProjectFile(
      id: 'file-1',
      snapshotId: 's1',
      path: 'src/requests/adapters.py',
      filename: 'adapters.py',
      extension: 'py',
      language: 'Python',
      sizeBytes: 1024,
      contentHash: 'hash1',
      isBinary: false,
      isGenerated: false,
      isTest: false,
      lineCount: 80,
      parserSupported: true,
    );

    return const FileDetail(
      file: file,
      fullContent: 'class HTTPAdapter:\n  def init_poolmanager():\n    pass\n',
      chunks: [],
      symbols: [
        ProjectSymbol(
          id: 'sym-1',
          fileId: 'file-1',
          name: 'HTTPAdapter',
          qualifiedName: 'requests.adapters.HTTPAdapter',
          symbolType: 'CLASS',
          startLine: 1,
          endLine: 3,
        ),
      ],
      outgoingDependencies: [],
      incomingReferences: [],
    );
  }

  @override
  Future<List<ProjectSymbol>> getProjectSymbols(String projectId, {int limit = 500}) async {
    return const [
      ProjectSymbol(
        id: 'sym-1',
        fileId: 'file-1',
        name: 'HTTPAdapter',
        qualifiedName: 'requests.adapters.HTTPAdapter',
        symbolType: 'CLASS',
        startLine: 1,
        endLine: 3,
      ),
    ];
  }

  @override
  Future<List<ProjectDependency>> getProjectDependencies(String projectId, {int limit = 500}) async {
    return [];
  }

  @override
  Future<DiscoverySummary> getDiscoverySummary(String projectId) async {
    return const DiscoverySummary(
      totalFindings: 1,
      criticalCount: 0,
      highCount: 0,
      mediumCount: 1,
      lowCount: 0,
    );
  }

  @override
  Future<List<ProjectFinding>> getFindings(
    String projectId, {
    String? severity,
    String? status,
    String? category,
  }) async {
    return [];
  }

  @override
  Future<List<ProjectKnowledge>> getKnowledge(
    String projectId, {
    String? category,
    String? status,
  }) async {
    return [
      ProjectKnowledge(
        id: 'k1',
        projectId: projectId,
        category: 'ARCHITECTURE_DECISION',
        title: 'Use Connection Pooling for all Outbound HTTP',
        content: 'All network calls must use HTTPAdapter.',
        status: 'ACTIVE',
        relatedFilePath: 'src/requests/adapters.py',
        createdAt: DateTime(2026, 9, 12),
        updatedAt: DateTime(2026, 9, 12),
      ),
    ];
  }

  @override
  Future<List<ConversationThread>> getConversations(String projectId) async {
    return [];
  }
}

void main() {
  testWidgets('WorkspaceScreen enables switching tabs and cross-navigation from Knowledge to Files', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    SharedPreferences.setMockInitialValues({
      'unotusk_auth_token': 'test-token-xyz',
      'unotusk_user_data': '{"id":"u1","email":"dev@acme.com","full_name":"Jane Dev","role":"member"}',
    });
    final prefs = await SharedPreferences.getInstance();

    const project = Project(
      id: 'proj-1',
      name: 'requests',
      slug: 'requests',
      status: 'READY',
      repositoryName: 'psf/requests',
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          selectedProjectProvider('proj-1').overrideWith((ref) async => project),
          workspaceRepositoryProvider.overrideWithValue(_CrossNavFakeRepository()),
        ],
        child: const MaterialApp(
          home: WorkspaceScreen(projectId: 'proj-1'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Overview tab is loaded
    expect(find.text('Overview'), findsOneWidget);
    expect(find.text('Needs attention'), findsOneWidget);

    // Switch to Knowledge Tab
    await tester.tap(find.text('Knowledge'));
    await tester.pumpAndSettle();

    expect(find.text('Use Connection Pooling for all Outbound HTTP'), findsOneWidget);
    expect(find.text('src/requests/adapters.py'), findsOneWidget);

    // Click file reference in Knowledge -> Navigates to Files Tab
    await tester.tap(find.text('src/requests/adapters.py'));
    await tester.pumpAndSettle();

    // Now in Files tab with Project Files header and Code view for adapters.py
    expect(find.text('Project Files'), findsOneWidget);
    expect(find.text('adapters.py'), findsWidgets);
    expect(find.text('class HTTPAdapter:'), findsOneWidget);

    // Switch to Ask Tab
    await tester.tap(find.text('Ask'));
    await tester.pumpAndSettle();

    expect(find.text('Grounded Project Inquiry'), findsOneWidget);
  });
}
