import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/projects/domain/project.dart';
import 'package:app/features/projects/presentation/projects_controller.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/grounded_answer.dart';
import 'package:app/features/workspace/presentation/workspace_screen.dart';

class _CrossNavFakeRepository extends Fake implements WorkspaceRepository {
  @override
  Future<GroundedAnswer> askQuestion(String projectId, String question, {String? conversationId}) async {
    return GroundedAnswer(
      conversationId: 'c1',
      messageId: 'm1',
      role: 'assistant',
      content: 'Answer for $question',
      evidence: const [],
      relatedEntities: const [],
      confidence: 'HIGH',
      createdAt: DateTime.now(),
    );
  }
}

void main() {
  testWidgets('WorkspaceScreen enables switching tabs via sidebar navigation', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    final fakeProject = Project(
      id: 'proj-1',
      name: 'requests',
      slug: 'requests',
      status: 'READY',
      repositoryName: 'psf/requests',
      updatedAt: DateTime.now(),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          workspaceRepositoryProvider.overrideWithValue(_CrossNavFakeRepository()),
          selectedProjectProvider('proj-1').overrideWith((ref) async => fakeProject),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: WorkspaceScreen(projectId: 'proj-1'),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Initial Ask tab is displayed
    expect(find.text('Investigate your project?'), findsOneWidget);
    expect(find.text('Ask'), findsOneWidget);
    expect(find.text('Spec History'), findsOneWidget);
    expect(find.text('Ontology Graph'), findsOneWidget);
    expect(find.text('Ingestion Feed'), findsOneWidget);

    // Switch to Spec History tab
    await tester.tap(find.text('Spec History'));
    await tester.pumpAndSettle();

    expect(find.text('Project Intelligence Record'), findsOneWidget);

    // Switch to Ontology Graph tab
    await tester.tap(find.text('Ontology Graph'));
    await tester.pumpAndSettle();

    expect(find.text('Knowledge Graph'), findsOneWidget);

    // Switch to Ingestion Feed tab
    await tester.tap(find.text('Ingestion Feed'));
    await tester.pumpAndSettle();

    expect(find.text('Project Dashboard'), findsOneWidget);
  });
}
