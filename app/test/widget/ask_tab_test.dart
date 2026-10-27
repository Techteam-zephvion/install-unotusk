import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/grounded_answer.dart';
import 'package:app/features/workspace/presentation/tabs/ask_tab.dart';

import 'package:app/features/workspace/domain/feature_specification.dart';

class _FakeWorkspaceRepository extends Fake implements WorkspaceRepository {
  @override
  Future<FeatureSpecification> generateFeatureSpecification(
    String projectId,
    String featureRequest, {
    String thinkingTier = 'warm',
  }) async {
    return FeatureSpecification(
      projectId: projectId,
      featureName: 'Adaptive Rate Limiter',
      intent: 'Enforce rate limiting on API endpoints with Retry-After header',
      confidence: 'HIGH',
      confirmedCodeFacts: const [
        'Confirmed existing: HTTPAdapter handles connection pooling',
      ],
      inferredRequirements: const [
        'Implement token bucket replenishment algorithm',
      ],
      scenarios: const [
        BDDScenario(
          id: 1,
          title: 'Burst limit threshold',
          given: 'A downstream client with valid API key',
          when: 'Client exceeds 100 req/sec',
          then: 'Return HTTP 429 Too Many Requests',
          citedFiles: ['src/requests/adapters.py'],
        ),
      ],
      evidence: const [
        EvidenceItem(
          type: 'symbol',
          file: 'src/requests/adapters.py',
          symbol: 'HTTPAdapter.send',
          lines: '100-150',
          relevance: 0.95,
          snippet: 'def send(self, request, ...): pass',
        ),
      ],
      citedFiles: const ['src/requests/adapters.py'],
      citedSymbols: const ['HTTPAdapter.send'],
      createdAt: DateTime(2026, 9, 12),
    );
  }
  @override
  Future<GroundedAnswer> askQuestion(
    String projectId,
    String question, {
    String? conversationId,
    String thinkingTier = 'warm',
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
    expect(find.text('Good morning.'), findsOneWidget);
    expect(find.textContaining('Analyzed Files'), findsOneWidget);
    expect(find.text('Discovered Risks'), findsOneWidget);
    expect(find.text('Total Symbols'), findsOneWidget);
  });


  testWidgets('AskTab runs BDD spec query and renders BDDContractCard with confirmed facts', (tester) async {
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
              initialQuery: 'Generate a BDD spec for rate-limiter',
            ),
          ),
        ),
      ),
    );

    // Initial pump
    await tester.pump();
    // Advance timers for step phases (1400ms + 1400ms)
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pumpAndSettle();

    // Verify BDD Contract card is rendered with real backend feature specification data
    expect(find.text('BDD Spec: Adaptive Rate Limiter'), findsOneWidget);
    expect(find.textContaining('CONFIRMED'), findsWidgets);
    expect(find.text('A downstream client with valid API key'), findsOneWidget);
    expect(find.text('Return HTTP 429 Too Many Requests'), findsOneWidget);
    expect(find.textContaining('HTTPAdapter handles connection pooling'), findsOneWidget);
  });
}