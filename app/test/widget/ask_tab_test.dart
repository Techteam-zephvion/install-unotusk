import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/grounded_answer.dart';
import 'package:app/features/workspace/presentation/tabs/ask_tab.dart';
import 'package:app/features/workspace/presentation/widgets/evidence_citation_chip.dart';
import 'package:app/features/workspace/presentation/workspace_controller.dart';

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

  @override
  Future<List<ConversationThread>> getConversations(String projectId) async {
    return [
      ConversationThread(
        id: 'c1',
        projectId: projectId,
        title: 'Connection pooling query',
        createdAt: DateTime(2026, 9, 12),
        updatedAt: DateTime(2026, 9, 12),
        messageCount: 1,
      ),
    ];
  }
}

void main() {
  testWidgets('AskTab renders search input, submits question, and displays grounded answer with citation', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    String? navigatedFile;
    String? navigatedLines;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          workspaceRepositoryProvider.overrideWithValue(_FakeWorkspaceRepository()),
          projectConversationsProvider('proj-1').overrideWith(
            (ref) async => [
              ConversationThread(
                id: 'c1',
                projectId: 'proj-1',
                title: 'Connection pooling query',
                createdAt: DateTime(2026, 9, 12),
                updatedAt: DateTime(2026, 9, 12),
                messageCount: 1,
              ),
            ],
          ),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: AskTab(
              projectId: 'proj-1',
              projectName: 'requests',
              onNavigateToFileWithLines: (file, lines) {
                navigatedFile = file;
                navigatedLines = lines;
              },
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify initial UI elements
    expect(find.text('Grounded Project Inquiry'), findsOneWidget);
    expect(find.text('Recent Inquiries'), findsOneWidget);
    expect(find.text('Connection pooling query'), findsOneWidget);
    expect(find.text('No active inquiries yet'), findsOneWidget);

    // Enter query and submit
    await tester.enterText(find.byType(TextField), 'Where is connection pooling configured?');
    await tester.tap(find.text('Investigate'));
    await tester.pumpAndSettle();

    // Verify Grounded answer rendered
    expect(find.text('Where is connection pooling configured?'), findsOneWidget);
    expect(find.text('GROUNDED'), findsOneWidget);
    expect(find.text('Connection pooling is configured in HTTPAdapter using urllib3.PoolManager.'), findsOneWidget);
    expect(find.text('Supporting Evidence & Citations'), findsOneWidget);
    expect(find.byType(EvidenceCitationChip), findsOneWidget);

    // Tap citation chip
    await tester.tap(find.byType(EvidenceCitationChip).first);
    await tester.pumpAndSettle();

    expect(navigatedFile, 'src/requests/adapters.py');
    expect(navigatedLines, '45-80');
  });
}
