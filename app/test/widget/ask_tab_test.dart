import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/grounded_answer.dart';
import 'package:app/features/workspace/presentation/tabs/ask_tab.dart';

class _FakeWorkspaceRepository extends Fake implements WorkspaceRepository {
  @override
  Future<GroundedAnswer> askQuestion(
    String projectId,
    String question, {
    String? conversationId,
  }) async {
    return GroundedAnswer(
      conversationId: 'c1',
      messageId: 'm1',
      role: 'assistant',
      content: 'Connection pooling is configured in HTTPAdapter using urllib3.PoolManager.',
      evidence: const [
        EvidenceItem(
          type: 'symbol',
          file: 'src/requests/adapters.py',
          symbol: 'HTTPAdapter.init_poolmanager',
          lines: '45-80',
          relevance: 0.95,
          snippet: 'self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize)',
        ),
      ],
      relatedEntities: const ['src/requests/adapters.py'],
      confidence: 'HIGH',
      createdAt: DateTime(2026, 9, 12),
    );
  }
}

void main() {
  testWidgets('AskTab renders hero state with Instrument Serif heading and prompt cards', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          workspaceRepositoryProvider.overrideWithValue(_FakeWorkspaceRepository()),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: AskTab(
              projectId: 'proj-1',
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify initial Figma hero elements
    expect(find.text('Investigate your project?'), findsOneWidget);
    expect(find.textContaining('Unotusk can make mistakes'), findsOneWidget);
    expect(find.text('Why choose Postgres over Mongo in March?'), findsOneWidget);
    expect(find.text('Which team owns the auth service?'), findsOneWidget);
  });
}
