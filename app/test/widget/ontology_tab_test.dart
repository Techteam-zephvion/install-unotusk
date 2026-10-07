import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/project_graph.dart';
import 'package:app/features/workspace/presentation/tabs/ontology_tab.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

void main() {
  testWidgets('OntologyTab renders empty state when graph is empty', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectGraphProvider('test-proj').overrideWith(
            (ref) async => const ProjectGraph(nodes: [], edges: []),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: OntologyTab(projectId: 'test-proj'),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('ONTOLOGY GRAPH'), findsOneWidget);
    expect(find.text('No Ontology Entities Indexed'), findsOneWidget);
  });

  testWidgets('OntologyTab renders SERVICE, REPOSITORY, FILE, and SYMBOL nodes and inspects on tap',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    const testGraph = ProjectGraph(
      nodes: [
        ProjectGraphNode(
          id: 'srv-1',
          type: 'SERVICE',
          label: 'Auth Service',
          metadata: {'tier': 'tier-0', 'slug': 'auth-service'},
        ),
        ProjectGraphNode(
          id: 'repo-1',
          type: 'REPOSITORY',
          label: 'org/auth-repo',
          metadata: {'service_id': 'srv-1'},
        ),
        ProjectGraphNode(
          id: 'file-1',
          type: 'FILE',
          label: 'src/main.py',
          metadata: {'language': 'python'},
        ),
        ProjectGraphNode(
          id: 'sym-1',
          type: 'CLASS',
          label: 'TokenManager',
          metadata: {'start_line': 10},
        ),
      ],
      edges: [
        ProjectGraphEdge(id: 'e1', source: 'srv-1', target: 'repo-1', type: 'CONTAINS'),
        ProjectGraphEdge(id: 'e2', source: 'repo-1', target: 'file-1', type: 'CONTAINS'),
        ProjectGraphEdge(id: 'e3', source: 'file-1', target: 'sym-1', type: 'DEFINES'),
      ],
      totalNodes: 4,
      totalEdges: 3,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          projectGraphProvider('test-proj').overrideWith(
            (ref) async => testGraph,
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: OntologyTab(projectId: 'test-proj'),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify header and legend
    expect(find.text('ONTOLOGY GRAPH'), findsOneWidget);
    expect(find.text('Knowledge Graph'), findsOneWidget);
    expect(find.text('SERVICE'), findsWidgets);
    expect(find.text('REPOSITORY'), findsWidgets);
    expect(find.text('FILE'), findsWidgets);
    expect(find.text('SYMBOL'), findsWidgets);

    // Verify node labels are rendered
    expect(find.text('Auth Service'), findsOneWidget);
    expect(find.text('org/auth-repo'), findsOneWidget);
    expect(find.text('src/main.py'), findsOneWidget);
    expect(find.text('TokenManager'), findsOneWidget);

    // Tap on Auth Service node to inspect
    await tester.tap(find.text('Auth Service'));
    await tester.pumpAndSettle();

    // Verify inspector card appears with metadata
    expect(find.text('tier: '), findsOneWidget);
    expect(find.text('tier-0'), findsOneWidget);
  });
}
