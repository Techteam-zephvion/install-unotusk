import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

class _ShortcutsFakeRepository extends Fake implements WorkspaceRepository {
  @override
  Future<ProjectRepositoryContext> getProjectRepositoryContext(String projectId) async {
    return const ProjectRepositoryContext(
      metrics: ProjectContextMetrics(
        totalFiles: 10,
        symbolsCount: 20,
        dependenciesCount: 5,
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
    return [];
  }

  @override
  Future<DiscoverySummary> getDiscoverySummary(String projectId) async {
    return const DiscoverySummary(
      totalFindings: 0,
      criticalCount: 0,
      highCount: 0,
      mediumCount: 0,
      lowCount: 0,
    );
  }
}

void main() {
  testWidgets('Workspace keyboard shortcuts Ctrl+2, Ctrl+4, Ctrl+6 switch tabs', (tester) async {
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
          workspaceRepositoryProvider.overrideWithValue(_ShortcutsFakeRepository()),
        ],
        child: const MaterialApp(
          home: WorkspaceScreen(projectId: 'proj-1'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify currently on Overview (tab 0)
    expect(find.text('Needs attention'), findsOneWidget);

    // Send Ctrl+2 to switch to Discoveries
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.digit2);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();

    expect(find.text('Project Discoveries'), findsOneWidget);

    // Send Ctrl+6 to switch to Ask
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.digit6);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();

    expect(find.text('Grounded Project Inquiry'), findsOneWidget);

    // Send Ctrl+1 to switch back to Overview
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.digit1);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();

    expect(find.text('Needs attention'), findsOneWidget);
  });
}
