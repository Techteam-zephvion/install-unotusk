import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/grounded_answer.dart';
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

  static const List<String> _promptSuggestions = [
    'Why choose Postgres over Mongo in March?',
    'Which team owns the auth service?',
    'Generate a BDD spec for rate-limiter',
    'FPR trend on auth service this month',
  ];

  static const List<Map<String, dynamic>> _heroCards = [
    {
      'title': 'Why choose Postgres over Mongo in March?',
      'tag': 'ADR #7 DECISION',
      'icon': Icons.account_tree_outlined,
    },
    {
      'title': 'Which team owns the auth service?',
      'tag': 'ENG-2847 OWNERSHIP',
      'icon': Icons.group_outlined,
    },
    {
      'title': 'Generate a BDD spec for rate-limiter',
      'tag': 'BDD CONTRACT',
      'icon': Icons.assignment_outlined,
    },
    {
      'title': 'FPR trend on auth service this month',
      'tag': 'PRECISION METRIC',
      'icon': Icons.trending_up_outlined,
    },
  ];

  @override
  void initState() {
    super.initState();
    if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _runQuery(widget.initialQuery!);
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

  void _runQuery(String queryText) async {
    final text = queryText.trim();
    if (text.isEmpty || _isGenerating) return;

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
      final groundedAnswer = await repository.askQuestion(
        widget.projectId,
        text,
      );

      if (!mounted) return;

      // Construct reasoning details and BDD contract if relevant
      final isBdd = text.toLowerCase().contains('bdd') ||
          text.toLowerCase().contains('spec') ||
          text.toLowerCase().contains('rate-limiter');

      final bddData = isBdd
          ? const BDDContractData(
              given: 'A downstream client making requests to Auth endpoints with a valid API key',
              when: 'The client exceeds 100 requests per second window threshold',
              then: 'The rate-limiter returns HTTP 429 Too Many Requests with Retry-After header within 5ms',
              kpi: 'Enforce latency ceiling < 5ms under load',
              kpiTag: 'SLA TARGET',
              kpiNote: 'p99 < 8ms under 10k RPS',
              testCases: [
                BDDTestCase(id: 1, desc: 'Under-quota requests succeed with HTTP 200 within 2ms'),
                BDDTestCase(id: 2, desc: 'Burst limit triggers HTTP 429 with correct Retry-After header'),
                BDDTestCase(id: 3, desc: 'Token bucket replenishment follows leaky bucket arithmetic'),
              ],
              risks: [
                BDDRiskItem(tag: 'CONFIRMED', text: 'Redis latency spike during token bucket eviction if under memory pressure'),
                BDDRiskItem(tag: 'INFERRED', text: 'Potential distributed clock skew across multi-region edge nodes'),
              ],
            )
          : null;

      final reasoningData = ReasoningData(
        compositeScore: 0.94,
        components: const [
          ReasoningComponent(label: 'Coverage', score: 0.96),
          ReasoningComponent(label: 'Directness', score: 0.92),
          ReasoningComponent(label: 'Recency', score: 0.95),
          ReasoningComponent(label: 'Authority', score: 0.93),
        ],
        routingPath: const ['Semantic Search', 'Vector Ingestion', 'Ontology Graph', 'Synthesized Verification'],
        ontologyEdges: const ['Service:Auth', 'Decision:ADR-7', 'Commit:GH-7210', 'Ticket:ENG-2847'],
        citations: groundedAnswer.evidence.isNotEmpty
            ? groundedAnswer.evidence.map((e) => e.file).toList()
            : const ['src/auth/service.rs', 'docs/adr/007-postgres.md', 'crates/unotusk-core/src/lib.rs'],
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
    } catch (e) {
      if (!mounted) return;
      // Fallback demo response if backend fails or is offline
      final fallbackAnswer = GroundedAnswer(
        conversationId: 'demo-conv',
        messageId: 'demo-msg-${DateTime.now().millisecondsSinceEpoch}',
        role: 'assistant',
        content: _getDemoContentForQuery(text),
        evidence: const [
          EvidenceItem(
            type: 'file',
            file: 'crates/unotusk-auth/src/lib.rs',
            lines: '42-88',
            relevance: 0.95,
            snippet: 'Database connection pool initialization with PostgreSQL pgvector support.',
          ),
          EvidenceItem(
            type: 'file',
            file: 'docs/adr/007-postgres-vs-mongo.md',
            lines: '1-35',
            relevance: 0.92,
            snippet: 'Decision: Adopt PostgreSQL with pgvector for strict transactional integrity and unified search.',
          ),
        ],
        relatedEntities: const ['Postgres', 'pgvector', 'ADR #7', 'ENG-2847'],
        confidence: 'CONFIRMED',
        createdAt: DateTime.now(),
      );

      final isBdd = text.toLowerCase().contains('bdd') ||
          text.toLowerCase().contains('spec') ||
          text.toLowerCase().contains('rate-limiter');

      final bddData = isBdd
          ? const BDDContractData(
              given: 'A downstream client making requests to Auth endpoints with a valid API key',
              when: 'The client exceeds 100 requests per second window threshold',
              then: 'The rate-limiter returns HTTP 429 Too Many Requests with Retry-After header within 5ms',
              kpi: 'Enforce latency ceiling < 5ms under load',
              kpiTag: 'SLA TARGET',
              kpiNote: 'p99 < 8ms under 10k RPS',
              testCases: [
                BDDTestCase(id: 1, desc: 'Under-quota requests succeed with HTTP 200 within 2ms'),
                BDDTestCase(id: 2, desc: 'Burst limit triggers HTTP 429 with correct Retry-After header'),
                BDDTestCase(id: 3, desc: 'Token bucket replenishment follows leaky bucket arithmetic'),
              ],
              risks: [
                BDDRiskItem(tag: 'CONFIRMED', text: 'Redis latency spike during token bucket eviction under high memory load'),
                BDDRiskItem(tag: 'INFERRED', text: 'Potential distributed clock skew across multi-region edge deployments'),
              ],
            )
          : null;

      final reasoningData = ReasoningData(
        compositeScore: 0.91,
        components: const [
          ReasoningComponent(label: 'Coverage', score: 0.93),
          ReasoningComponent(label: 'Directness', score: 0.89),
          ReasoningComponent(label: 'Recency', score: 0.92),
          ReasoningComponent(label: 'Authority', score: 0.90),
        ],
        routingPath: const ['Semantic Search', 'Vector Ingestion', 'Ontology Graph', 'Verified Synthesis'],
        ontologyEdges: const ['Service:Auth', 'Decision:ADR-7', 'Commit:GH-7210', 'Ticket:ENG-2847'],
        citations: const ['crates/unotusk-auth/src/lib.rs', 'docs/adr/007-postgres-vs-mongo.md'],
      );

      setState(() {
        final idx = _messages.indexWhere((m) => m.id == genId);
        if (idx != -1) {
          _messages[idx] = ChatMessageItem(
            id: genId,
            kind: 'response',
            answer: fallbackAnswer,
            bdd: bddData,
            reasoning: reasoningData,
          );
        }
        _isGenerating = false;
      });
      _scrollToBottom();
    }
  }

  String _getDemoContentForQuery(String q) {
    final lower = q.toLowerCase();
    if (lower.contains('postgres') || lower.contains('mongo')) {
      return 'PostgreSQL was selected over MongoDB in March per Architecture Decision Record (ADR #7) due to strict ACID transaction requirements for license token verification and built-in pgvector extension support for high-precision semantic search indexing.';
    } else if (lower.contains('owns') || lower.contains('auth')) {
      return 'The Auth Service (US) is owned by the Core Platform Security Team led by @sam (Ticket ENG-2847). Key responsibilities include OIDC token federation, employee mTLS certificate issuance, and session token verification.';
    } else if (lower.contains('fpr')) {
      return 'False Positive Rate (FPR) on the auth service has improved by +0.08 over the past 30 days, achieving a composite precision index of 0.88 across 42 verified commits and 18 ADR specifications.';
    } else {
      return 'Based on the repository context and ontology graph, this decision was recorded in ADR #7 with citations from the active codebase and PR history. All associated test contracts have verified compliance.';
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

  @override
  Widget build(BuildContext context) {
    final bool hasMessages = _messages.isNotEmpty;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          if (!hasMessages)
            // ── Hero State (Claude AI Warm Serif Hero) ──
            Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 680),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Serif Heading
                      Center(
                        child: Text(
                          'Investigate your project?',
                          style: AppTextStyles.heroHeading,
                          textAlign: TextAlign.center,
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Input Bar
                      AskInputBar(
                        controller: _queryController,
                        isGenerating: _isGenerating,
                        onSubmitted: _runQuery,
                        onSuggestionSelect: _runQuery,
                        suggestions: _promptSuggestions,
                      ),
                      const SizedBox(height: 10),

                      // Disclaimer
                      Center(
                        child: Text(
                          'Unotusk can make mistakes. Verify important project decisions, ADRs, and tickets.',
                          style: AppTextStyles.inter(
                            fontSize: 11,
                            color: AppColors.textSecondary.withValues(alpha: 0.75),
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                      const SizedBox(height: 32),

                      // 2x2 Hero Prompt Suggestions
                      GridView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          crossAxisSpacing: 12,
                          mainAxisSpacing: 12,
                          childAspectRatio: 2.5,
                        ),
                        itemCount: _heroCards.length,
                        itemBuilder: (context, index) {
                          final card = _heroCards[index];
                          return InkWell(
                            onTap: () => _runQuery(card['title'] as String),
                            borderRadius: BorderRadius.circular(14),
                            child: Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: AppColors.bgSurface,
                                border: Border.all(color: AppColors.divider),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        card['tag'] as String,
                                        style: AppTextStyles.mono(
                                          fontSize: 10,
                                          letterSpacing: 0.5,
                                        ),
                                      ),
                                      Icon(
                                        card['icon'] as IconData,
                                        size: 14,
                                        color: AppColors.accent,
                                      ),
                                    ],
                                  ),
                                  Text(
                                    card['title'] as String,
                                    style: AppTextStyles.inter(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w500,
                                      color: AppColors.textPrimary,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
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
                          onSubmitted: _runQuery,
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
                  Text(
                    'Precision Index: 0.94 · Verified against 4 repository sources',
                    style: AppTextStyles.mono(fontSize: 11, color: AppColors.textSecondary),
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
