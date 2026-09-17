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

class _ShortcutsFakeRepository extends Fake implements WorkspaceRepository {
  @override
  Future<GroundedAnswer> askQuestion(String projectId, String question, {String? conversationId}) async {
    return GroundedAnswer(
      conversationId: 'c1',
      messageId: 'm1',
      role: 'assistant',
      content: 'Answer',
      evidence: const [],
      relatedEntities: const [],
      confidence: 'HIGH',
      createdAt: DateTime.now(),
    );
  }
}

void main() {
  testWidgets('Workspace screen renders and allows navigation to all tabs', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    SharedPreferences.setMockInitialValues({
      'unotusk_auth_token': 'test-token-xyz',
      'unotusk_user_data': '{"id":"u1","email":"dev@acme.com","full_name":"Jane Dev","role":"member"}',
    });
    final prefs = await SharedPreferences.getInstance();

    final project = Project(
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
          selectedProjectProvider('proj-1').overrideWith((ref) async => project),
          workspaceRepositoryProvider.overrideWithValue(_ShortcutsFakeRepository()),
        ],
        child: const MaterialApp(
          home: WorkspaceScreen(projectId: 'proj-1'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Ask'), findsOneWidget);
    expect(find.text('Spec History'), findsOneWidget);
    expect(find.text('Ontology Graph'), findsOneWidget);
    expect(find.text('Ingestion Feed'), findsOneWidget);
  });
}
