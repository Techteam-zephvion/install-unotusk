import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/project_knowledge.dart';
import 'package:app/features/workspace/presentation/tabs/knowledge_tab.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

void main() {
  final testKnowledgeItem = ProjectKnowledge(
    id: 'k1',
    projectId: 'proj-1',
    category: 'ARCHITECTURE_DECISION',
    title: 'Use Connection Pooling for all Outbound HTTP',
    content: 'All external network calls must use HTTPAdapter with urllib3 pool connections.',
    status: 'ACTIVE',
    sourceType: 'CUSTOMER',
    relatedFilePath: 'src/requests/adapters.py',
    relatedSymbol: 'HTTPAdapter',
    createdAt: DateTime(2026, 9, 12),
    updatedAt: DateTime(2026, 9, 12),
  );

  testWidgets('KnowledgeTab renders knowledge items and opens create dialog', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    int? navigatedTab;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectKnowledgeListProvider((
            projectId: 'proj-1',
            category: null,
            status: 'ACTIVE',
          )).overrideWith(
            (ref) async => [testKnowledgeItem],
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: KnowledgeTab(
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

    // Verify Knowledge item rendered
    expect(find.text('Use Connection Pooling for all Outbound HTTP'), findsOneWidget);
    expect(find.text('ARCHITECTURE DECISION'), findsOneWidget);
    expect(find.text('src/requests/adapters.py'), findsOneWidget);

    // Test Navigation to File
    await tester.tap(find.text('src/requests/adapters.py'));
    await tester.pumpAndSettle();
    expect(navigatedTab, 3);

    // Test Add Knowledge button opens dialog
    await tester.tap(find.text('Add Knowledge'));
    await tester.pumpAndSettle();

    expect(find.text('Add Project Knowledge'), findsOneWidget);
    expect(find.text('Category'), findsOneWidget);
    expect(find.text('Title'), findsOneWidget);
    expect(find.text('Content / Engineering Context'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);

    // Close Dialog
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(find.text('Add Project Knowledge'), findsNothing);
  });
}
