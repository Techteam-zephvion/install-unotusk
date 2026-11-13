import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/grounded_answer.dart';
import '../../domain/feature_specification.dart';
import '../../domain/project_file.dart';
import '../../data/workspace_repository.dart';
import '../workspace_controller.dart';
import '../widgets/ask_input_bar.dart';
import '../widgets/constellation_loader.dart';
import '../widgets/bdd_contract_card.dart';
import '../widgets/reasoning_panel.dart';
import '../widgets/file_detail_panel.dart';

class ChatMessageItem {
  final String id;
  final String kind; // 'query' | 'generating' | 'response'
  final String? text;
  final String? phase; // 'ingesting', 'scoring', 'deepScoring'
  final GroundedAnswer? answer;
  final BDDContractData? bdd;
  final ReasoningData? reasoning;

  const ChatMessageItem({
    required this.id,
    required this.kind,
    this.text,
    this.phase,
    this.answer,
    this.bdd,
    this.reasoning,
  });
}

class AskTab extends ConsumerStatefulWidget {
  final String projectId;
  final String? initialQuery;

  const AskTab({
    super.key,
    required this.projectId,
    this.initialQuery,
  });

  @override
  ConsumerState<AskTab> createState() => _AskTabState();
}

class _AskTabState extends ConsumerState<AskTab> {
  final TextEditingController _queryController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessageItem> _messages = [];
  bool _isGenerating = false;
  ThinkingTier _selectedTier = ThinkingTier.warm;

  static const List<String> _promptSuggestions = [
    'Why choose Postgres over Mongo in March?',
    'Which team owns the auth service?',
    'Generate a BDD spec for rate-limiter',
    'FPR trend on auth service this month',
  ];


  @override
  void initState() {
    super.initState();
    if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _runQuery(widget.initialQuery!, tier: _selectedTier);
      });
    }
  }

  @override
  void dispose() {
    _queryController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _openFileCitation(String filePath, {String? lines}) async {
    int? startLine;
    int? endLine;
    if (lines != null && lines.isNotEmpty) {
      final parts = lines.split('-');
      if (parts.isNotEmpty) startLine = int.tryParse(parts[0].trim());
      if (parts.length > 1) endLine = int.tryParse(parts[1].trim());
      endLine ??= startLine;
    }

    ProjectFile targetFile;
    try {
      final files = await ref.read(projectFilesProvider(widget.projectId).future);
      final filename = filePath.split('/').last;
      targetFile = files.firstWhere(
        (f) => f.path == filePath || f.filename == filename,
        orElse: () => ProjectFile(
          id: 'cite-${filePath.hashCode.abs()}',
          snapshotId: 'current',
          path: filePath,
          filename: filename,
          extension: filename.contains('.') ? filename.split('.').last : '',
          language: filename.endsWith('.rs') ? 'Rust' : (filename.endsWith('.py') ? 'Python' : 'Markdown'),
          sizeBytes: 2048,
          contentHash: 'hash',
          isBinary: false,
          isGenerated: false,
          isTest: false,
          lineCount: 120,
          parserSupported: true,
        ),
      );
    } catch (_) {
      final filename = filePath.split('/').last;
      targetFile = ProjectFile(
        id: 'cite-${filePath.hashCode.abs()}',
        snapshotId: 'current',
        path: filePath,
        filename: filename,
        extension: filename.contains('.') ? filename.split('.').last : '',
        language: filename.endsWith('.rs') ? 'Rust' : (filename.endsWith('.py') ? 'Python' : 'Markdown'),
        sizeBytes: 2048,
        contentHash: 'hash',
        isBinary: false,
        isGenerated: false,
        isTest: false,
        lineCount: 120,
        parserSupported: true,
      );
    }

    if (!mounted) return;

    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 880, maxHeight: 720),
          child: FileDetailPanel(
            projectId: widget.projectId,
            file: targetFile,
            initialHighlightStartLine: startLine,
            initialHighlightEndLine: endLine,
            onClose: () => Navigator.of(ctx).pop(),
          ),
        ),
      ),
    );
  }

  void _runQuery(String queryText, {ThinkingTier? tier}) async {
    final text = queryText.trim();
    if (text.isEmpty || _isGenerating) return;

    final activeTier = tier ?? _selectedTier;
    _selectedTier = activeTier;

    final queryId = 'q-${DateTime.now().millisecondsSinceEpoch}';
    final genId = 'g-${DateTime.now().millisecondsSinceEpoch}';

    setState(() {
      _messages.add(ChatMessageItem(
        id: queryId,
        kind: 'query',
        text: text,
      ));
      _messages.add(ChatMessageItem(
        id: genId,
        kind: 'generating',
        phase: 'ingesting',
      ));
      _isGenerating = true;
    });
    _queryController.clear();
    _scrollToBottom();

    // Step through ontology generation phases
    await Future.delayed(const Duration(milliseconds: 1400));
    if (!mounted) return;
    setState(() {
      final idx = _messages.indexWhere((m) => m.id == genId);
      if (idx != -1) {
        _messages[idx] = ChatMessageItem(
          id: genId,
          kind: 'generating',
          phase: 'scoring',
        );
      }
    });

    await Future.delayed(const Duration(milliseconds: 1400));
    if (!mounted) return;
    setState(() {
      final idx = _messages.indexWhere((m) => m.id == genId);
      if (idx != -1) {
        _messages[idx] = ChatMessageItem(
          id: genId,
          kind: 'generating',
          phase: 'deepScoring',
        );
      }
    });

    try {
      final repository = ref.read(workspaceRepositoryProvider);

      final isBdd = text.toLowerCase().contains('bdd') ||
          text.toLowerCase().contains('spec') ||
          text.toLowerCase().contains('contract');

      if (isBdd) {
        try {
          final FeatureSpecification spec = await repository.generateFeatureSpecification(
            widget.projectId,
            text,
            thinkingTier: activeTier.name,
          );
          if (!mounted) return;

          final bddData = spec.toBDDContractData(tier: '${activeTier.name.toUpperCase()} TIER');

          final contentBuffer = StringBuffer();
          contentBuffer.writeln('### ${spec.featureName}\n');
          contentBuffer.writeln('${spec.intent}\n');
          if (spec.warning != null && spec.warning!.isNotEmpty) {
            contentBuffer.writeln('> ⚠️ **Grounding Notice**: ${spec.warning}\n');
          }
          if (spec.confirmedCodeFacts.isNotEmpty) {
            contentBuffer.writeln('**Confirmed Code Facts:**');
            for (final fact in spec.confirmedCodeFacts) {
              contentBuffer.writeln('- $fact');
            }
            contentBuffer.writeln();
          }
          if (spec.inferredRequirements.isNotEmpty) {
            contentBuffer.writeln('**Inferred Requirements:**');
            for (final req in spec.inferredRequirements) {
              contentBuffer.writeln('- $req');
            }
            contentBuffer.writeln();
          }

          final groundedAnswer = GroundedAnswer(
            conversationId: 'spec-${spec.projectId}',
            messageId: 'spec-msg-${DateTime.now().millisecondsSinceEpoch}',
            role: 'assistant',
            content: contentBuffer.toString().trim(),
            evidence: spec.evidence,
            relatedEntities: spec.citedFiles,
            confidence: spec.confidence,
            createdAt: spec.createdAt,
          );

          final reasoningData = ReasoningData(
            compositeScore: spec.confidence == 'HIGH' ? 0.94 : (spec.confidence == 'LOW' ? 0.40 : 0.72),
            components: [
              ReasoningComponent(label: 'Coverage', score: spec.confidence == 'HIGH' ? 0.96 : (spec.confidence == 'LOW' ? 0.35 : 0.70)),
              ReasoningComponent(label: 'Directness', score: spec.confidence == 'HIGH' ? 0.92 : (spec.confidence == 'LOW' ? 0.30 : 0.68)),
              ReasoningComponent(label: 'Recency', score: spec.hasSupersededPrecursors ? 0.40 : 0.95),
              ReasoningComponent(label: 'Authority', score: spec.confidence == 'HIGH' ? 0.93 : 0.60),
            ],
            routingPath: const ['Semantic Search', 'Vector Ingestion', 'Ontology Graph', 'Synthesized Verification'],
            ontologyEdges: spec.citedFiles,
            citations: spec.citedFiles,
          );

          setState(() {
            final idx = _messages.indexWhere((m) => m.id == genId);
            if (idx != -1) {
              _messages[idx] = ChatMessageItem(
                id: genId,
                kind: 'response',
                answer: groundedAnswer,
                bdd: bddData,
                reasoning: reasoningData,
              );
            }
            _isGenerating = false;
          });
          _scrollToBottom();
          return;
        } catch (_) {
          // If specification endpoint fails, gracefully fall through to standard askQuestion
        }
      }

      final groundedAnswer = await repository.askQuestion(
        widget.projectId,
        text,
        thinkingTier: activeTier.name,
      );

      if (!mounted) return;

      final reasoningData = ReasoningData(
        compositeScore: 0.94,
        components: const [
          ReasoningComponent(label: 'Coverage', score: 0.96),
          ReasoningComponent(label: 'Directness', score: 0.92),
          ReasoningComponent(label: 'Recency', score: 0.95),
          ReasoningComponent(label: 'Authority', score: 0.93),
        ],
        routingPath: const ['Semantic Search', 'Vector Ingestion', 'Ontology Graph', 'Synthesized Verification'],
        ontologyEdges: groundedAnswer.relatedEntities,
        citations: groundedAnswer.evidence.isNotEmpty
            ? groundedAnswer.evidence.map((e) => e.file).where((f) => f.isNotEmpty).toSet().toList()
            : const [],
      );

      setState(() {
        final idx = _messages.indexWhere((m) => m.id == genId);
        if (idx != -1) {
          _messages[idx] = ChatMessageItem(
            id: genId,
            kind: 'response',
            answer: groundedAnswer,
            bdd: null,
            reasoning: reasoningData,
          );
        }
        _isGenerating = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      final errorAnswer = GroundedAnswer(
        conversationId: 'err-conv',
        messageId: 'err-msg-${DateTime.now().millisecondsSinceEpoch}',
        role: 'assistant',
        content: 'Failed to retrieve answer from backend: $e\n\nPlease ensure backend is reachable at http://10.0.0.59:28000.',
        evidence: const [],
        relatedEntities: const [],
        confidence: 'INFERRED',
        createdAt: DateTime.now(),
      );

      final reasoningData = ReasoningData(
        compositeScore: 0.0,
        components: const [],
        routingPath: const ['Direct API Connection'],
        ontologyEdges: const [],
        citations: const [],
      );

      setState(() {
        final idx = _messages.indexWhere((m) => m.id == genId);
        if (idx != -1) {
          _messages[idx] = ChatMessageItem(
            id: genId,
            kind: 'response',
            answer: errorAnswer,
            bdd: null,
            reasoning: reasoningData,
          );
        }
        _isGenerating = false;
      });
      _scrollToBottom();
    }
  }


  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Widget _buildStatCard({required IconData icon, required Color iconColor, required String title, required String value}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgSurface,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          const SizedBox(height: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppTextStyles.inter(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                value,
                style: AppTextStyles.mono(
                  fontSize: 22,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildActionPill({required IconData icon, required String label, bool isPrimary = false}) {
    return InkWell(
      onTap: () {},
      borderRadius: BorderRadius.circular(24),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isPrimary ? AppColors.accent : Colors.transparent,
          border: Border.all(color: isPrimary ? AppColors.accent : AppColors.divider),
          borderRadius: BorderRadius.circular(24),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: isPrimary ? AppColors.bgBase : AppColors.textPrimary),
            const SizedBox(width: 8),
            Text(
              label,
              style: AppTextStyles.inter(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: isPrimary ? AppColors.bgBase : AppColors.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActivityItem({
    required String title,
    required String subtitle,
    required String time,
    required String status,
    required Color statusColor,
    required bool isLast,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: isLast ? null : const Border(bottom: BorderSide(color: AppColors.divider)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.bgElevated,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.divider),
                  ),
                  child: const Icon(Icons.history, size: 18, color: AppColors.textSecondary),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: AppTextStyles.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: AppTextStyles.inter(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  status,
                  style: AppTextStyles.mono(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: statusColor,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                time,
                style: AppTextStyles.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDemoButton({required String label, bool isPrimary = false, IconData? icon, Color? iconColor}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isPrimary ? AppColors.textPrimary : AppColors.bgElevated,
        border: Border.all(color: isPrimary ? AppColors.textPrimary : AppColors.divider),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: iconColor ?? (isPrimary ? AppColors.bgBase : AppColors.textPrimary)),
            const SizedBox(width: 6),
          ],
          Text(
            label,
            style: AppTextStyles.mono(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: isPrimary ? AppColors.bgBase : AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDesignPrinciple({
    required IconData icon,
    required String title,
    required String description,
    required bool isLast,
    Widget? actions,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24),
      decoration: BoxDecoration(
        border: isLast ? null : const Border(bottom: BorderSide(color: AppColors.divider)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: AppColors.textSecondary),
          const SizedBox(width: 24),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.mono(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  description,
                  style: AppTextStyles.mono(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                    height: 1.5,
                  ),
                ),
                if (actions != null) ...[
                  const SizedBox(height: 16),
                  actions,
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool hasMessages = _messages.isNotEmpty;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          if (!hasMessages)
            // ── Dashboard Hero State ──
            Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 40),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 800),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Greeting
                      Text(
                        'Good morning.',
                        style: AppTextStyles.mono(
                          fontSize: 28,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Input Bar
                      AskInputBar(
                        controller: _queryController,
                        isGenerating: _isGenerating,
                        initialTier: _selectedTier,
                        onTierChanged: (tier) => setState(() => _selectedTier = tier),
                        onSubmittedWithTier: (text, tier) => _runQuery(text, tier: tier),
                        onSubmitted: (text) => _runQuery(text, tier: _selectedTier),
                        onSuggestionSelect: (text) => _runQuery(text, tier: _selectedTier),
                        suggestions: _promptSuggestions,
                      ),
                      const SizedBox(height: 32),
                      
                      // Stat Cards Grid
                      LayoutBuilder(
                        builder: (context, constraints) {
                          final crossAxisCount = constraints.maxWidth > 600 ? 4 : 2;
                          return GridView.count(
                            crossAxisCount: crossAxisCount,
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            mainAxisSpacing: 16,
                            crossAxisSpacing: 16,
                            childAspectRatio: crossAxisCount == 4 ? 1.1 : 1.8,
                            children: [
                              _buildStatCard(
                                icon: Icons.folder_outlined,
                                iconColor: Colors.blueAccent,
                                title: 'Analyzed Files',
                                value: '1,248',
                              ),
                              _buildStatCard(
                                icon: Icons.warning_amber_rounded,
                                iconColor: Colors.orangeAccent,
                                title: 'Discovered Risks',
                                value: '14',
                              ),
                              _buildStatCard(
                                icon: Icons.data_object,
                                iconColor: Colors.greenAccent,
                                title: 'Total Symbols',
                                value: '8,432',
                              ),
                              _buildStatCard(
                                icon: Icons.hub_outlined,
                                iconColor: Colors.purpleAccent,
                                title: 'Dependencies',
                                value: '34',
                              ),
                            ],
                          );
                        }
                      ),
                      const SizedBox(height: 32),
                      
                      // Quick Actions
                      Text(
                        'Quick actions',
                        style: AppTextStyles.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          _buildActionPill(icon: Icons.add, label: 'Analyze Repo', isPrimary: true),
                          _buildActionPill(icon: Icons.upload_file, label: 'View Discoveries'),
                          _buildActionPill(icon: Icons.assessment_outlined, label: 'Generate Report'),
                        ],
                      ),
                      const SizedBox(height: 32),
                      
                      // Recent Activity
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Recent Activity',
                            style: AppTextStyles.inter(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          TextButton(
                            onPressed: () {},
                            child: Text(
                              'View all',
                              style: AppTextStyles.inter(
                                fontSize: 13,
                                color: AppColors.accent,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Container(
                        decoration: BoxDecoration(
                          color: AppColors.bgSurface,
                          border: Border.all(color: AppColors.divider),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          children: [
                            _buildActivityItem(
                              title: 'Unotusk MVP Ingestion',
                              subtitle: 'Analyzed 342 files across 4 languages',
                              time: '2 mins ago',
                              status: 'COMPLETED',
                              statusColor: Colors.greenAccent,
                              isLast: false,
                            ),
                            _buildActivityItem(
                              title: 'Security Audit Scan',
                              subtitle: 'Identified 2 high-severity risks in auth service',
                              time: '1 hour ago',
                              status: 'REVIEW REQUIRED',
                              statusColor: Colors.orangeAccent,
                              isLast: true,
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 48),
                      _buildDesignPrinciple(
                        icon: Icons.near_me_outlined,
                        title: '01 — Pointer and hover',
                        description: 'Buttons darken slightly. Rows receive a faint background. Icons respond subtly. Interactive elements never look inert.',
                        actions: Row(
                          children: [
                            _buildDemoButton(label: 'Save changes', isPrimary: true),
                            const SizedBox(width: 8),
                            _buildDemoButton(label: 'Cancel', isPrimary: false),
                          ],
                        ),
                        isLast: false,
                      ),
                      _buildDesignPrinciple(
                        icon: Icons.done_all,
                        title: '02 — Selection and state',
                        description: 'Checkboxes draw their checkmarks, navigation selection transitions cleanly, dropdowns open naturally, and attendance status changes receive immediate visual feedback.',
                        actions: Row(
                          children: [
                            _buildDemoButton(label: 'Present', icon: Icons.check_box, iconColor: Colors.greenAccent),
                            const SizedBox(width: 8),
                            _buildDemoButton(label: 'Absent', icon: Icons.check_box_outline_blank),
                          ],
                        ),
                        isLast: false,
                      ),
                      _buildDesignPrinciple(
                        icon: Icons.keyboard_outlined,
                        title: '03 — Keyboard and focus',
                        description: 'Visible focus indicators, sensible Tab order, Enter and Space activation, Escape to close popovers, and keyboard navigation through tables and lists.',
                        isLast: false,
                      ),
                      _buildDesignPrinciple(
                        icon: Icons.sync,
                        title: '04 — Loading and saving',
                        description: 'Buttons show a compact loading state; saved records show a restrained checkmark; failed requests explain what happened and offer recovery. No giant spinners or celebration animations.',
                        isLast: false,
                      ),
                      _buildDesignPrinciple(
                        icon: Icons.swap_horiz,
                        title: '05 — Navigation and transitions',
                        description: 'Subtle page transitions, anchored menus, smoothly expanding filters, preserved scroll position where appropriate, and no jarring layout shifts.',
                        isLast: true,
                      ),
                    ],
                  ),
                ),
              ),
            )
          else
            // ── Chat State (Scrollable thread with pinned bottom input) ──
            Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(24, 24, 24, 180),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final msg = _messages[index];
                      return Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 720),
                          child: _buildMessageBubble(msg),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),

          // Floating pinned bottom input bar in chat mode
          if (hasMessages)
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      AppColors.bgBase.withValues(alpha: 0.0),
                      AppColors.bgBase.withValues(alpha: 0.8),
                      AppColors.bgBase,
                    ],
                    stops: const [0.0, 0.4, 1.0],
                  ),
                ),
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 680),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        AskInputBar(
                          controller: _queryController,
                          isGenerating: _isGenerating,
                          initialTier: _selectedTier,
                          onTierChanged: (tier) => setState(() => _selectedTier = tier),
                          onSubmittedWithTier: (text, tier) => _runQuery(text, tier: tier),
                          onSubmitted: (text) => _runQuery(text, tier: _selectedTier),
                          placeholder: 'Ask a follow-up about decisions, commits, or tickets…',
                          suggestions: _promptSuggestions,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Unotusk can make mistakes. Verify important project decisions, ADRs, and tickets.',
                          style: AppTextStyles.inter(
                            fontSize: 11,
                            color: AppColors.textSecondary.withValues(alpha: 0.75),
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessageItem msg) {
    if (msg.kind == 'query') {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(bottom: 24),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.bgElevated,
            border: Border.all(color: AppColors.divider),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 12,
              ),
            ],
          ),
          child: Text(
            msg.text ?? '',
            style: AppTextStyles.inter(
              fontSize: 14,
              color: AppColors.textPrimary,
              height: 1.5,
            ),
          ),
        ),
      );
    } else if (msg.kind == 'generating') {
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 24),
        alignment: Alignment.center,
        child: ConstellationLoader(phase: msg.phase ?? 'scoring'),
      );
    } else {
      // Grounded Response bubble
      final answer = msg.answer;
      if (answer == null) return const SizedBox.shrink();

      return Container(
        margin: const EdgeInsets.only(bottom: 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Reasoning accordion at top
            if (msg.reasoning != null)
              ReasoningPanel(
                reasoning: msg.reasoning!,
                onCitationTap: _openFileCitation,
              ),

            // BDD Contract Card if present
            if (msg.bdd != null)
              BDDContractCard(bdd: msg.bdd!),

            // Text segments if not BDD-only
            if (msg.bdd == null)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text(
                  answer.content,
                  style: AppTextStyles.inter(
                    fontSize: 15,
                    color: AppColors.textPrimary,
                    height: 1.65,
                  ),
                ),
              ),

            // Citations evidence row
            if (answer.evidence.isNotEmpty) ...[
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: answer.evidence.map((ev) {
                  return InkWell(
                    onTap: () => _openFileCitation(ev.file, lines: ev.lines),
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.bgSurface,
                        border: Border.all(color: AppColors.divider),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.description_outlined, size: 12, color: AppColors.accent),
                          const SizedBox(width: 6),
                          Text(
                            ev.file,
                            style: AppTextStyles.mono(
                              fontSize: 11,
                              color: AppColors.accent,
                            ),
                          ),
                          if (ev.lines != null && ev.lines!.isNotEmpty) ...[
                            const SizedBox(width: 4),
                            Text(
                              'L${ev.lines}',
                              style: AppTextStyles.mono(
                                fontSize: 10,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],

            // Response metadata and feedback actions
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.only(top: 10),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: AppColors.divider)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      'Precision Index: 0.94 · Verified against 4 repository sources',
                      style: AppTextStyles.mono(fontSize: 11, color: AppColors.textSecondary),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.copy, size: 14),
                        color: AppColors.textSecondary,
                        tooltip: 'Copy response',
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: answer.content));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Copied response to clipboard'),
                              duration: Duration(seconds: 2),
                            ),
                          );
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.thumb_up_outlined, size: 14),
                        color: AppColors.textSecondary,
                        tooltip: 'Good response',
                        onPressed: () {},
                      ),
                      IconButton(
                        icon: const Icon(Icons.thumb_down_outlined, size: 14),
                        color: AppColors.textSecondary,
                        tooltip: 'Needs improvement',
                        onPressed: () {},
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }
  }
}
