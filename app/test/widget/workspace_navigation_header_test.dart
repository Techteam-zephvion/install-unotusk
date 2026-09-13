import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/projects/domain/project.dart';
import 'package:app/features/projects/presentation/projects_controller.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/discovery_summary.dart';
import 'package:app/features/workspace/domain/project_finding.dart';
import 'package:app/features/workspace/domain/repository_context.dart';
import 'package:app/features/workspace/presentation/workspace_screen.dart';

class _NavFakeRepository extends Fake implements WorkspaceRepository {
  @override
  Future<ProjectRepositoryContext> getProjectRepositoryContext(String projectId) async {
    return const ProjectRepositoryContext(
      repository: RepositoryInfo(
        id: 'repo-1',
        name: 'requests',
        fullName: 'psf/requests',
        defaultBranch: 'main',
      ),
      activeSnapshot: ActiveSnapshot(
        id: 'snap-1',
        repositoryId: 'repo-1',
        commitHash: '9e4f21a88b',
        branch: 'main',
        status: 'READY',
        totalFiles: 120,
        totalBytes: 50000,
      ),
      metrics: ProjectContextMetrics(
        totalFiles: 120,
        symbolsCount: 450,
        dependenciesCount: 80,
      ),
    );
  }

  @override
  Future<List<ProjectFinding>> getFindings(
    String projectId, {
    String? severity,
    String? status,
    String? category,
  }) async {
    if (severity == 'CRITICAL' && status == 'OPEN') {
      return [
        ProjectFinding(
          id: 'f-1',
          projectId: projectId,
          snapshotId: 'snap-1',
          category: 'SECURITY',
          title: 'Hardcoded Secret Detected',
          description: 'A secret is hardcoded in auth.py',
          whyItMatters: 'Can compromise credentials',
          severity: 'CRITICAL',
          confidence: 'HIGH',
          status: 'OPEN',
          score: 9.5,
          recommendation: 'Move credentials to environment variables',
          createdAt: DateTime(2026, 9, 12),
        ),
      ];
    }
    return [];
  }

  @override
  Future<DiscoverySummary> getDiscoverySummary(String projectId) async {
    return const DiscoverySummary(
      totalFindings: 1,
      criticalCount: 1,
      highCount: 0,
      mediumCount: 0,
      lowCount: 0,
    );
  }
}

void main() {
  testWidgets('Workspace header displays repository full name, branch, commit, and discovery attention count', (tester) async {
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
          workspaceRepositoryProvider.overrideWithValue(_NavFakeRepository()),
        ],
        child: const MaterialApp(
          home: WorkspaceScreen(projectId: 'proj-1'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Project Name, Status, Repo Full Name, and Branch/Commit
    expect(find.text('requests'), findsWidgets);
    expect(find.text('READY'), findsWidgets);
    expect(find.text('psf/requests'), findsOneWidget);
    expect(find.text('main @ 9e4f21a'), findsOneWidget);

    // Verify Discoveries tab has the critical count indicator '1'
    expect(find.text('Discoveries'), findsOneWidget);
    expect(find.text('1'), findsWidgets);
  });
}
