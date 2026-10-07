import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/app/theme/app_colors.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/grounded_answer.dart';
import 'package:app/features/workspace/presentation/tabs/ask_tab.dart';
import 'package:app/features/workspace/presentation/widgets/ask_input_bar.dart';

class _RecordingWorkspaceRepository extends Fake implements WorkspaceRepository {
  String? lastProjectId;
  String? lastQuestion;
  String? lastConversationId;
  String? lastThinkingTier;
  int callCount = 0;

  @override
  Future<GroundedAnswer> askQuestion(
    String projectId,
    String question, {
    String? conversationId,
    String thinkingTier = 'warm',
  }) async {
    callCount++;
    lastProjectId = projectId;
    lastQuestion = question;
    lastConversationId = conversationId;
    lastThinkingTier = thinkingTier;

    return GroundedAnswer(
      conversationId: conversationId ?? 'test-conv',
      messageId: 'msg-$callCount',
      role: 'assistant',
      content: 'Answer for $question under tier $thinkingTier',
      evidence: const [],
      relatedEntities: const [],
      confidence: 'HIGH',
      createdAt: DateTime(2026, 9, 29),
    );
  }
}

void main() {
  group('AskInputBar Thinking Tier Widget Tests', () {
    testWidgets('defaults to Warm tier and displays "Warm tier" label', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 700,
                child: AskInputBar(
                  controller: controller,
                  onSubmitted: (_) {},
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('thinking_tier_button')), findsOneWidget);
      expect(find.text('Warm tier'), findsOneWidget);
    });

    testWidgets('tapping thinking button opens dropdown with Hot, Warm, Cold options', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 700,
                child: AskInputBar(
                  controller: controller,
                  onSubmitted: (_) {},
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('thinking_tier_button')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('thinking_toggle_switch')), findsOneWidget);
      expect(find.byKey(const Key('thinking_tier_hot')), findsOneWidget);
      expect(find.byKey(const Key('thinking_tier_warm')), findsOneWidget);
      expect(find.byKey(const Key('thinking_tier_cold')), findsOneWidget);
      expect(find.text('Quick answers'), findsOneWidget);
      expect(find.text('Balanced'), findsOneWidget);
      expect(find.text('Deep reasoning'), findsOneWidget);
    });

    testWidgets('selecting Hot tier updates label, color, and submits with ThinkingTier.hot', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);
      ThinkingTier? changedTier;
      String? submittedText;
      ThinkingTier? submittedTier;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 700,
                child: AskInputBar(
                  controller: controller,
                  onTierChanged: (t) => changedTier = t,
                  onSubmittedWithTier: (txt, t) {
                    submittedText = txt;
                    submittedTier = t;
                  },
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open dropdown
      await tester.tap(find.byKey(const Key('thinking_tier_button')));
      await tester.pumpAndSettle();

      // Tap Hot
      await tester.tap(find.byKey(const Key('thinking_tier_hot')));
      await tester.pumpAndSettle();

      expect(changedTier, ThinkingTier.hot);
      expect(find.text('Hot tier'), findsOneWidget);

      // Verify modeHot color is applied to the pill text
      final textWidget = tester.widget<Text>(find.text('Hot tier'));
      expect(textWidget.style?.color, AppColors.modeHot);

      // Enter text and submit
      await tester.enterText(find.byType(TextField), 'Quick summary of repo');
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('ask_submit_button')));
      await tester.pumpAndSettle();

      expect(submittedText, 'Quick summary of repo');
      expect(submittedTier, ThinkingTier.hot);
    });

    testWidgets('selecting Cold tier updates label, color, and submits with ThinkingTier.cold', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);
      ThinkingTier? changedTier;
      String? submittedText;
      ThinkingTier? submittedTier;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 700,
                child: AskInputBar(
                  controller: controller,
                  onTierChanged: (t) => changedTier = t,
                  onSubmittedWithTier: (txt, t) {
                    submittedText = txt;
                    submittedTier = t;
                  },
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open dropdown
      await tester.tap(find.byKey(const Key('thinking_tier_button')));
      await tester.pumpAndSettle();

      // Tap Cold
      await tester.tap(find.byKey(const Key('thinking_tier_cold')));
      await tester.pumpAndSettle();

      expect(changedTier, ThinkingTier.cold);
      expect(find.text('Cold tier'), findsOneWidget);

      final textWidget = tester.widget<Text>(find.text('Cold tier'));
      expect(textWidget.style?.color, AppColors.modeCold);

      // Enter text and submit
      await tester.enterText(find.byType(TextField), 'Deep architecture audit');
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('ask_submit_button')));
      await tester.pumpAndSettle();

      expect(submittedText, 'Deep architecture audit');
      expect(submittedTier, ThinkingTier.cold);
    });

    testWidgets('toggling switch off switches label to "Thinking" and falls back to warm tier', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);
      ThinkingTier? changedTier;
      String? submittedText;
      ThinkingTier? submittedTier;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 700,
                child: AskInputBar(
                  controller: controller,
                  onTierChanged: (t) => changedTier = t,
                  onSubmittedWithTier: (txt, t) {
                    submittedText = txt;
                    submittedTier = t;
                  },
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open dropdown
      await tester.tap(find.byKey(const Key('thinking_tier_button')));
      await tester.pumpAndSettle();

      // Toggle switch OFF
      await tester.tap(find.byKey(const Key('thinking_toggle_switch')));
      await tester.pumpAndSettle();

      expect(changedTier, ThinkingTier.warm);
      // Both the dropdown title and the pill button display 'Thinking'
      expect(find.text('Thinking'), findsNWidgets(2));

      // Close dropdown by tapping button
      await tester.tap(find.byKey(const Key('thinking_tier_button')));
      await tester.pumpAndSettle();
      expect(find.text('Thinking'), findsOneWidget);

      // Enter text and submit
      await tester.enterText(find.byType(TextField), 'Untiered inquiry');
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('ask_submit_button')));
      await tester.pumpAndSettle();

      expect(submittedText, 'Untiered inquiry');
      expect(submittedTier, ThinkingTier.warm);
    });
  });

  group('AskTab Thinking Tier Integration Tests', () {
    testWidgets('AskTab renders with Warm tier selector in hero mode', (tester) async {
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = _RecordingWorkspaceRepository();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            workspaceRepositoryProvider.overrideWithValue(repo),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: AskTab(
                projectId: 'proj-int-1',
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Warm tier'), findsOneWidget);

      // Tap thinking button to open tier menu
      await tester.tap(find.byKey(const Key('thinking_tier_button')));
      await tester.pumpAndSettle();

      // Tap Cold
      await tester.tap(find.byKey(const Key('thinking_tier_cold')));
      await tester.pumpAndSettle();

      expect(find.text('Cold tier'), findsOneWidget);
    });
  });
}
