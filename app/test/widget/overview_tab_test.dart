import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/project_finding.dart';
import 'package:app/features/workspace/domain/repository_context.dart';
import 'package:app/features/workspace/presentation/tabs/overview_tab.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

void main() {
  testWidgets('OverviewTab renders project metrics and attention card correctly', (tester) async {
    final mockContext = ProjectRepositoryContext(
      repository: const RepositoryInfo(
        id: 'repo-1',
        name: 'requests',
        fullName: 'psf/requests',
      ),
      activeSnapshot: const ActiveSnapshot(
        id: 'snap-1',
        repositoryId: 'repo-1',
        commitHash: 'a1b2c3d4e5f6',
        branch: 'main',
        status: 'COMPLETED',
        totalFiles: 121,
        totalBytes: 1048576,
      ),
      metrics: const ProjectContextMetrics(
        totalFiles: 121,
        languagesCount: 2,
        symbolsCount: 450,
        dependenciesCount: 310,
        languageDistribution: {'Python': 115, 'TOML': 6},
      ),
    );

    final mockFinding = ProjectFinding(
      id: 'finding-1',
      projectId: 'proj-1',
      snapshotId: 'snap-1',
      category: 'ARCHITECTURE',
      title: 'Circular dependency detected',
      description: 'auth_token.py and user_session.py depend on each other',
      whyItMatters: 'Increases coupling',
      severity: 'CRITICAL',
      confidence: 'HIGH',
      status: 'OPEN',
      score: 0.95,
      recommendation: 'Refactor session interfaces',
      relatedEntities: ['requests.auth_token', 'requests.user_session'],
      createdAt: DateTime(2026, 9, 12),
    );

    int? navigatedTab;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectContextProvider('proj-1').overrideWith(
            (ref) async => mockContext,
          ),
          projectCriticalFindingsProvider('proj-1').overrideWith(
            (ref) async => [mockFinding],
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: OverviewTab(
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

    // Pump to resolve AsyncValues
    await tester.pumpAndSettle();

    // Verify Metric Strip
    expect(find.text('Project Type'), findsOneWidget);
    expect(find.text('Python Project'), findsOneWidget);
    expect(find.text('121'), findsOneWidget);
    expect(find.text('450'), findsOneWidget);
    expect(find.text('310'), findsOneWidget);

    // Verify Needs Attention section
    expect(find.text('Needs attention'), findsOneWidget);
    expect(find.text('Circular dependency detected'), findsOneWidget);
    expect(find.text('CRITICAL'), findsOneWidget);
    expect(find.text('requests.auth_token'), findsOneWidget);

    // Verify Language distribution & Snapshot
    expect(find.text('Language Distribution'), findsOneWidget);
    expect(find.text('Python'), findsOneWidget);
    expect(find.text('Active Snapshot'), findsOneWidget);
    expect(find.text('a1b2c3d'), findsOneWidget);

    // Test Open button click
    final openButton = find.text('Open');
    expect(openButton, findsOneWidget);
    await tester.tap(openButton);
    await tester.pumpAndSettle();

    expect(navigatedTab, 1);
  });

  testWidgets('OverviewTab renders clean empty attention state when no critical issues', (tester) async {
    final mockContext = ProjectRepositoryContext(
      metrics: const ProjectContextMetrics(
        totalFiles: 50,
        languagesCount: 1,
        symbolsCount: 120,
        dependenciesCount: 60,
        languageDistribution: {'Python': 50},
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectContextProvider('proj-2').overrideWith(
            (ref) async => mockContext,
          ),
          projectCriticalFindingsProvider('proj-2').overrideWith(
            (ref) async => [],
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: OverviewTab(
              projectId: 'proj-2',
              projectName: 'clean-project',
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('No critical structural issues or circular dependencies detected.'), findsOneWidget);
  });
}
