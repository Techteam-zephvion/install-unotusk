import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../data/workspace_repository.dart';
import '../../domain/grounded_answer.dart';
import '../widgets/ask_history_sidebar.dart';
import '../widgets/grounded_answer_card.dart';
import '../workspace_controller.dart';

class AskTab extends ConsumerStatefulWidget {
  final String projectId;
  final String projectName;
  final String? initialQuery;
  final void Function(int tabIndex)? onNavigateToTab;
  final void Function(String file, String? lines)? onNavigateToFileWithLines;

  const AskTab({
    super.key,
    required this.projectId,
    required this.projectName,
    this.initialQuery,
    this.onNavigateToTab,
    this.onNavigateToFileWithLines,
  });

  @override
  ConsumerState<AskTab> createState() => _AskTabState();
}

class _AskTabState extends ConsumerState<AskTab> {
  late final TextEditingController _queryController;
  final List<({String question, GroundedAnswer answer})> _qaHistory = [];
  bool _isLoading = false;
  String? _activeConversationId;

  @override
  void initState() {
    super.initState();
    _queryController = TextEditingController(text: widget.initialQuery ?? '');
    if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _submitQuestion();
      });
    }
  }

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _submitQuestion() async {
    final question = _queryController.text.trim();
    if (question.isEmpty || _isLoading) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final answer = await ref.read(workspaceRepositoryProvider).askQuestion(
            widget.projectId,
            question,
            conversationId: _activeConversationId,
          );

      setState(() {
        _activeConversationId = answer.conversationId;
        _qaHistory.insert(0, (question: question, answer: answer));
        _queryController.clear();
      });

      ref.invalidate(projectConversationsProvider(widget.projectId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Inquiry failed: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _handleCitationTap(String file, String? lines) {
    if (widget.onNavigateToFileWithLines != null) {
      widget.onNavigateToFileWithLines!(file, lines);
    } else {
      // Navigate to files tab (index 3)
      widget.onNavigateToTab?.call(3);
    }
  }

  @override
  Widget build(BuildContext context) {
    final conversationsAsync = ref.watch(projectConversationsProvider(widget.projectId));

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Left History Sidebar (Flex 3)
        Expanded(
          flex: 3,
          child: conversationsAsync.when(
            loading: () => const AskHistorySidebar(
              threads: [],
              activeThreadId: null,
              onNewThread: _noop,
              onSelectThread: _noopThread,
            ),
            error: (e, s) => AskHistorySidebar(
              threads: const [],
              activeThreadId: null,
              onNewThread: () => setState(() => _activeConversationId = null),
              onSelectThread: _noopThread,
            ),
            data: (threads) => AskHistorySidebar(
              threads: threads,
              activeThreadId: _activeConversationId,
              onNewThread: () {
                setState(() {
                  _activeConversationId = null;
                  _qaHistory.clear();
                  _queryController.clear();
                });
              },
              onSelectThread: (thread) {
                setState(() {
                  _activeConversationId = thread.id;
                });
              },
            ),
          ),
        ),
        const SizedBox(width: 16),

        // Right Investigation Workspace (Flex 7)
        Expanded(
          flex: 7,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Search & Inquiry Input Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.slate200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Grounded Project Inquiry',
                      style: AppTextStyles.h2.copyWith(fontSize: 15, color: AppColors.slate900),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Search architecture, code symbols, dependencies, or knowledge context with verified citations.',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _queryController,
                            style: AppTextStyles.bodyMedium,
                            textInputAction: TextInputAction.send,
                            onSubmitted: (_) => _submitQuestion(),
                            decoration: InputDecoration(
                              hintText: 'e.g. Where is connection pooling configured?',
                              hintStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate400),
                              prefixIcon: const Icon(Icons.search, size: 18, color: AppColors.slate400),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(6),
                                borderSide: const BorderSide(color: AppColors.slate300),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(6),
                                borderSide: const BorderSide(color: AppColors.slate900),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        ElevatedButton.icon(
                          onPressed: _isLoading ? null : _submitQuestion,
                          icon: _isLoading
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : const Icon(Icons.send, size: 14),
                          label: Text(_isLoading ? 'Searching...' : 'Investigate'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.slate900,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        Text('Suggestions:', style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500)),
                        _SuggestionChip(
                          label: 'Where is authentication handled?',
                          onTap: () {
                            _queryController.text = 'Where is authentication handled?';
                            _submitQuestion();
                          },
                        ),
                        _SuggestionChip(
                          label: 'How is connection pooling configured?',
                          onTap: () {
                            _queryController.text = 'How is connection pooling configured?';
                            _submitQuestion();
                          },
                        ),
                        _SuggestionChip(
                          label: 'What dependencies are imported?',
                          onTap: () {
                            _queryController.text = 'What dependencies are imported?';
                            _submitQuestion();
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Q&A Answers List
              Expanded(
                child: _qaHistory.isEmpty
                    ? Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.slate200),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.psychology_outlined, size: 40, color: AppColors.slate300),
                              const SizedBox(height: 12),
                              Text(
                                'No active inquiries yet',
                                style: AppTextStyles.h2.copyWith(fontSize: 15, color: AppColors.slate700),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Ask a question above to explore symbols, files, and architectural flows.',
                                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _qaHistory.length,
                        itemBuilder: (context, index) {
                          final item = _qaHistory[index];
                          return GroundedAnswerCard(
                            question: item.question,
                            answer: item.answer,
                            onCitationTap: _handleCitationTap,
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

void _noop() {}
void _noopThread(ConversationThread t) {}

class _SuggestionChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _SuggestionChip({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: AppColors.slate100,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: AppColors.slate200),
        ),
        child: Text(
          label,
          style: AppTextStyles.bodySmall.copyWith(
            fontSize: 11,
            color: AppColors.slate700,
          ),
        ),
      ),
    );
  }
}
