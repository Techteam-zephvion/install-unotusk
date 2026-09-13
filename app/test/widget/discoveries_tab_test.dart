import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/discovery_summary.dart';
import 'package:app/features/workspace/domain/project_finding.dart';
import 'package:app/features/workspace/presentation/tabs/discoveries_tab.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

void main() {
  final testFinding = ProjectFinding(
    id: 'f1',
    projectId: 'proj-1',
    snapshotId: 's1',
    category: 'ARCHITECTURE',
    title: 'Circular dependency between auth and session',
    description: 'auth_token.py and user_session.py import each other directly.',
    whyItMatters: 'Causes tight coupling and initialization order bugs.',
    severity: 'CRITICAL',
    confidence: 'HIGH',
    status: 'OPEN',
    score: 0.98,
    recommendation: 'Extract token parser to auth_core.py',
    relatedEntities: ['src/requests/auth_token.py', 'src/requests/user_session.py'],
    evidence: [
      {'file': 'auth_token.py', 'line': 14, 'reason': 'imports user_session'},
    ],
    createdAt: DateTime(2026, 9, 12),
  );

  const testSummary = DiscoverySummary(
    totalFindings: 1,
    criticalCount: 1,
    highCount: 0,
    mediumCount: 0,
    lowCount: 0,
  );

  testWidgets('DiscoveriesTab renders finding feed and opens detail view', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    int? navigatedTab;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectDiscoverySummaryProvider('proj-1').overrideWith(
            (ref) async => testSummary,
          ),
          projectFindingsListProvider((
            projectId: 'proj-1',
            category: null,
            severity: null,
            status: null,
          )).overrideWith(
            (ref) async => [testFinding],
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: DiscoveriesTab(
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
    expect(find.text('Project Discoveries'), findsOneWidget);
    expect(find.text('1 findings • 1 critical, 0 high'), findsOneWidget);

    // Verify FindingCard in Left Feed
    expect(find.text('Circular dependency between auth and session'), findsOneWidget);
    expect(find.text('CRITICAL'), findsOneWidget);

    // Click Finding to open Right Investigation Pane
    await tester.tap(find.text('Circular dependency between auth and session'));
    await tester.pumpAndSettle();

    // Verify Investigation Pane details
    expect(find.text('What was detected'), findsOneWidget);
    expect(find.text('Why it matters'), findsOneWidget);
    expect(find.text('Actionable Recommendation'), findsOneWidget);
    expect(find.text('Extract token parser to auth_core.py'), findsOneWidget);
    expect(find.text('src/requests/auth_token.py'), findsOneWidget);

    // Verify Action buttons
    expect(find.text('Acknowledge'), findsOneWidget);
    expect(find.text('Resolve'), findsOneWidget);
    expect(find.text('Dismiss'), findsOneWidget);
    expect(find.text('Ask about finding'), findsOneWidget);

    // Test Ask about finding click
    await tester.tap(find.text('Ask about finding'));
    await tester.pumpAndSettle();

    expect(navigatedTab, 5);
  });
}
