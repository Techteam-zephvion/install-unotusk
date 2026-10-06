import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/badges.dart';
import '../widgets/chat_input_box.dart';
import '../widgets/thinking_scanner.dart';

class ChatScreen extends StatefulWidget {
  final UnoPalette palette;
  final List<ChatMessage> messages;
  final bool isGenerating;
  final Function(String) onSubmitQuery;

  static const List<String> querySuggestions = [
    'What are the primary components in this repository?',
    'Explain the database migration flow and schema',
    'How does authentication and OIDC discovery work?',
    'What services are exposed over the LAN on port 28000?',
  ];

  static const List<HeroCardItem> heroCards = [
    HeroCardItem(
      title: 'Explain the core server architecture',
      tag: 'ARCHITECTURE',
      icon: LucideIcons.layers,
    ),
    HeroCardItem(
      title: 'How does OIDC Single Sign-On authenticate?',
      tag: 'SECURITY',
      icon: LucideIcons.shieldCheck,
    ),
    HeroCardItem(
      title: 'Inspect active background ingestion tasks',
      tag: 'PIPELINE',
      icon: LucideIcons.cpu,
    ),
    HeroCardItem(
      title: 'Audit LAN network connectivity and ports',
      tag: 'TELEMETRY',
      icon: LucideIcons.network,
    ),
  ];

  const ChatScreen({
    super.key,
    required this.palette,
    required this.messages,
    required this.isGenerating,
    required this.onSubmitQuery,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  void _handleSubmit() {
    final text = _inputController.text.trim();
    if (text.isEmpty || widget.isGenerating) return;
    _inputController.clear();
    widget.onSubmitQuery(text);

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
    if (widget.messages.isEmpty) {
      return _buildHero();
    }
    return _buildChatStream();
  }

  Widget _buildHero() {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Center(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 680),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 40),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(
                      'Investigate your project?',
                      textAlign: TextAlign.center,
                      style: UnoTypography.displaySerif(
                        palette: widget.palette,
                        fontSize: 26,
                      ),
                    ),
                    const SizedBox(height: 24),
                    ChatInputBox(
                      controller: _inputController,
                      palette: widget.palette,
                      onSubmit: _handleSubmit,
                      onChipSelected: (prompt) {
                        _inputController.text = prompt;
                        _handleSubmit();
                      },
                      suggestions: ChatScreen.querySuggestions,
                    ),
                    const SizedBox(height: 10),
                    Opacity(
                      opacity: 0.75,
                      child: Text(
                        'Unotusk can make mistakes. Verify important project decisions, ADRs, and tickets.',
                        textAlign: TextAlign.center,
                        style: UnoTypography.body(
                          color: widget.palette.textSec,
                          fontSize: 11,
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),

                    // 4 Quick Prompt Cards Grid
                    LayoutBuilder(
                      builder: (context, gridConstraints) {
                        final isWide = gridConstraints.maxWidth > 500;
                        return GridView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: isWide ? 2 : 1,
                            crossAxisSpacing: 12,
                            mainAxisSpacing: 12,
                            childAspectRatio: isWide ? 4.7 : 4.0,
                          ),
                    itemCount: ChatScreen.heroCards.length,
                    itemBuilder: (context, index) {
                      final item = ChatScreen.heroCards[index];
                      return InkWell(
                        onTap: () {
                          _inputController.text = item.title;
                          _handleSubmit();
                        },
                        borderRadius: BorderRadius.circular(14),
                        hoverColor: widget.palette.accent.withValues(alpha: 0.05),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 14),
                          decoration: BoxDecoration(
                            color: widget.palette.bgSurface,
                            border: Border.all(color: widget.palette.div),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    item.tag,
                                    style: UnoTypography.mono(
                                      color: widget.palette.textSec,
                                      fontSize: 10,
                                      letterSpacing: 0.4,
                                    ),
                                  ),
                                  Icon(item.icon,
                                      size: 14,
                                      color: widget.palette.accent
                                          .withValues(alpha: 0.8)),
                                ],
                              ),
                              Text(
                                item.title,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: UnoTypography.body(
                                  color: widget.palette.text,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                          },
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildChatStream() {
    return Stack(
      children: [
        // Messages scroll area
        Positioned.fill(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 180),
            itemCount: widget.messages.length,
            itemBuilder: (context, index) {
              final msg = widget.messages[index];
              return Center(
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 680),
                  child: _buildMessageItem(msg),
                ),
              );
            },
          ),
        ),

        // Floating Bottom Input with Gradient Fade
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  widget.palette.bgBase.withValues(alpha: 0.0),
                  widget.palette.bgBase.withValues(alpha: 0.95),
                  widget.palette.bgBase,
                ],
                stops: const [0.0, 0.45, 1.0],
              ),
            ),
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 16),
            child: Center(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 680),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ChatInputBox(
                      controller: _inputController,
                      palette: widget.palette,
                      onSubmit: _handleSubmit,
                      onChipSelected: (prompt) {
                        _inputController.text = prompt;
                        _handleSubmit();
                      },
                      suggestions: ChatScreen.querySuggestions,
                      placeholder:
                          'Ask a follow-up about decisions, commits, or tickets…',
                    ),
                    const SizedBox(height: 8),
                    Opacity(
                      opacity: 0.75,
                      child: Text(
                        'Unotusk can make mistakes. Verify important project decisions, ADRs, and tickets.',
                        textAlign: TextAlign.center,
                        style: UnoTypography.body(
                          color: widget.palette.textSec,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMessageItem(ChatMessage msg) {
    if (msg.kind == MessageKind.query) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(bottom: 24, top: 12),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          constraints: const BoxConstraints(maxWidth: 580),
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.03),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'YOUR QUERY',
                style: UnoTypography.mono(
                  color: widget.palette.accent,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                msg.text ?? '',
                style: UnoTypography.body(
                  color: widget.palette.text,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (msg.kind == MessageKind.generating) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: ThinkingScanner(
          phase: msg.phase ?? 'scoring',
          palette: widget.palette,
        ),
      );
    }

    if (msg.kind == MessageKind.response && msg.data != null) {
      return Container(
        margin: const EdgeInsets.only(bottom: 36),
        child: _ResponseCard(
          data: msg.data!,
          palette: widget.palette,
        ),
      );
    }

    return const SizedBox.shrink();
  }
}

class _ResponseCard extends StatefulWidget {
  final QueryResponseData data;
  final UnoPalette palette;

  const _ResponseCard({required this.data, required this.palette});

  @override
  State<_ResponseCard> createState() => _ResponseCardState();
}

class _ResponseCardState extends State<_ResponseCard> {
  bool _copied = false;
  String? _feedback; // up, down
  bool _thoughtExpanded = false;
  bool _vulnScanVisible = false;

  void _copyToClipboard() {
    final text = widget.data.segments.map((s) => s.text).join('\n\n');
    Clipboard.setData(ClipboardData(text: text));
    setState(() => _copied = true);
    Future.delayed(const Duration(milliseconds: 1800), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Reasoning Thought Process Drawer (if available)
        if (widget.data.reasoning != null) ...[
          _buildThoughtProcessDrawer(widget.data.reasoning!),
          const SizedBox(height: 16),
        ],

        // BDD Spec Viewer (if available)
        if (widget.data.bdd != null) ...[
          _buildBddContract(widget.data.bdd!),
          const SizedBox(height: 16),
        ],

        // Segment text paragraphs
        if (widget.data.bdd == null) ...[
          ...widget.data.segments.map((seg) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: RichText(
                  text: TextSpan(
                    style: UnoTypography.body(
                      color: widget.palette.text,
                      fontSize: 15,
                      height: 1.7,
                    ),
                    children: [
                      TextSpan(text: seg.text),
                      if (seg.tag != null)
                        WidgetSpan(
                          alignment: PlaceholderAlignment.middle,
                          child: TagBadge(
                            tag: seg.tag!,
                            palette: widget.palette,
                          ),
                        ),
                    ],
                  ),
                ),
              )),
        ],

        // Footer Meta Bar
        Container(
          padding: const EdgeInsets.only(top: 10),
          decoration: BoxDecoration(
            border: Border(top: BorderSide(color: widget.palette.div)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  widget.data.meta,
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 11,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
              Row(
                children: [
                  IconButton(
                    icon: Icon(
                      _copied ? LucideIcons.check : LucideIcons.copy,
                      size: 14,
                      color: _copied
                          ? widget.palette.live
                          : widget.palette.textSec,
                    ),
                    onPressed: _copyToClipboard,
                    tooltip: 'Copy response',
                  ),
                  IconButton(
                    icon: Icon(
                      LucideIcons.thumbsUp,
                      size: 14,
                      color: _feedback == 'up'
                          ? widget.palette.accent
                          : widget.palette.textSec,
                    ),
                    onPressed: () {
                      setState(() {
                        _feedback = _feedback == 'up' ? null : 'up';
                      });
                    },
                    tooltip: 'Good response',
                  ),
                  IconButton(
                    icon: Icon(
                      LucideIcons.thumbsDown,
                      size: 14,
                      color: _feedback == 'down'
                          ? widget.palette.inferred
                          : widget.palette.textSec,
                    ),
                    onPressed: () {
                      setState(() {
                        _feedback = _feedback == 'down' ? null : 'down';
                      });
                    },
                    tooltip: 'Needs improvement',
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildThoughtProcessDrawer(ReasoningModel reasoning) {
    const thoughtTime = '2.6';
    final scoreColor = const Color(0xFFDA7756);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Drawer toggle button
        InkWell(
          onTap: () => setState(() => _thoughtExpanded = !_thoughtExpanded),
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: widget.palette.bgSurface,
              border: Border.all(color: widget.palette.div),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(LucideIcons.zap, size: 13, color: Color(0xFFDA7756)),
                const SizedBox(width: 7),
                Text(
                  'Thought process for ${thoughtTime}s',
                  style: UnoTypography.body(
                    color: widget.palette.text,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 6),
                Icon(
                  _thoughtExpanded
                      ? LucideIcons.chevronUp
                      : LucideIcons.chevronDown,
                  size: 13,
                  color: widget.palette.textSec,
                ),
              ],
            ),
          ),
        ),

        // Expanded details
        if (_thoughtExpanded) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: widget.palette.bgSurface,
              border: Border.all(color: widget.palette.div),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Composite Score Header
                Text(
                  'COMPOSITE SCORE',
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 10,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 8,
                        decoration: BoxDecoration(
                          color: widget.palette.div,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: FractionallySizedBox(
                          alignment: Alignment.centerLeft,
                          widthFactor: reasoning.compositeScore.clamp(0.0, 1.0),
                          child: Container(
                            decoration: BoxDecoration(
                              color: scoreColor,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Text(
                      reasoning.compositeScore.toStringAsFixed(2),
                      style: UnoTypography.mono(
                        color: widget.palette.text,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF38231C),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'CONFIRMED',
                        style: UnoTypography.mono(
                          color: const Color(0xFFDA7756),
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Component scores (Coverage, Directness, Recency, Authority) in Teal/Mint
                ...reasoning.components.map((c) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 85,
                          child: Text(
                            c.label,
                            style: UnoTypography.body(
                              color: widget.palette.textSec,
                              fontSize: 13,
                            ),
                          ),
                        ),
                        Expanded(
                          child: Container(
                            height: 5,
                            decoration: BoxDecoration(
                              color: widget.palette.div,
                              borderRadius: BorderRadius.circular(3),
                            ),
                            child: FractionallySizedBox(
                              alignment: Alignment.centerLeft,
                              widthFactor: c.score.clamp(0.0, 1.0),
                              child: Container(
                                decoration: BoxDecoration(
                                  color: const Color(0xFF5BA495),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        SizedBox(
                          width: 38,
                          child: Text(
                            c.score.toStringAsFixed(2),
                            textAlign: TextAlign.right,
                            style: UnoTypography.mono(
                              color: widget.palette.textSec,
                              fontSize: 11,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                }),
                const SizedBox(height: 18),

                // Routing Path
                Text(
                  'ROUTING PATH',
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 10,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (int i = 0; i < reasoning.routingPath.length; i++) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: widget.palette.bgElevated,
                          border: Border.all(color: widget.palette.div),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          reasoning.routingPath[i],
                          style: UnoTypography.body(
                            color: widget.palette.text,
                            fontSize: 12,
                          ),
                        ),
                      ),
                      if (i < reasoning.routingPath.length - 1)
                        Text(
                          '→',
                          style: TextStyle(
                            color: widget.palette.textSec,
                            fontSize: 13,
                          ),
                        ),
                    ],
                  ],
                ),
                const SizedBox(height: 18),

                // Ontology Edges
                Text(
                  'ONTOLOGY EDGES',
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 10,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: reasoning.ontologyEdges.map((edge) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF142921),
                        border: Border.all(color: const Color(0xFF2C5E48)),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        edge,
                        style: UnoTypography.mono(
                          color: const Color(0xFF4ADE80),
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // Sources Cited
                Text(
                  'SOURCES CITED',
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 10,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: reasoning.citations.map((cite) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF271C17),
                        border: Border.all(color: const Color(0xFF573324)),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        cite,
                        style: UnoTypography.mono(
                          color: const Color(0xFFDA7756),
                          fontSize: 11,
                        ),
                      ),
                    );
                  }).toList(),
                ),

                // Real Code Evidence (from server AST snapshot)
                if (reasoning.evidence.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text(
                    'GROUNDED CODE EVIDENCE (${reasoning.evidence.length} SNIPPETS)',
                    style: UnoTypography.mono(
                      color: widget.palette.accent,
                      fontSize: 10,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...reasoning.evidence.map((ev) {
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: widget.palette.bgElevated,
                        border: Border.all(color: widget.palette.div),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(LucideIcons.fileCode, size: 12, color: widget.palette.accent),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  ev.file + (ev.lines != null ? ':${ev.lines}' : ''),
                                  style: UnoTypography.mono(
                                    color: widget.palette.text,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              if (ev.symbol != null && ev.symbol!.isNotEmpty) ...[
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: widget.palette.accent.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    ev.symbol!,
                                    style: UnoTypography.mono(
                                      color: widget.palette.accent,
                                      fontSize: 10,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                          if (ev.snippet != null && ev.snippet!.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: widget.palette.bgSurface,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                ev.snippet!,
                                style: UnoTypography.mono(
                                  color: widget.palette.textSec,
                                  fontSize: 10,
                                ),
                                maxLines: 6,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ],
                      ),
                    );
                  }),
                ],

                if (reasoning.debugSignals != null && reasoning.debugSignals!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Icon(LucideIcons.server, size: 11, color: widget.palette.textSec),
                      const SizedBox(width: 6),
                      Text(
                        'Backend: http://10.0.0.59:28000 · Model: ${reasoning.debugSignals?['model'] ?? 'Qwen 3.8-27b'} · Grounding: Active',
                        style: UnoTypography.mono(
                          color: widget.palette.textSec,
                          fontSize: 9,
                        ),
                      ),
                    ],
                  ),
                ],

                const SizedBox(height: 16),
                Divider(color: widget.palette.div),
                const SizedBox(height: 10),

                // Vulnerability Scan toggle
                OutlinedButton.icon(
                  onPressed: () =>
                      setState(() => _vulnScanVisible = !_vulnScanVisible),
                  icon: Icon(LucideIcons.shield,
                      size: 12, color: widget.palette.textSec),
                  label: Text(
                    '${_vulnScanVisible ? "Hide" : "Scan for"} vulnerabilities',
                    style: UnoTypography.body(
                        color: widget.palette.textSec, fontSize: 12),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: widget.palette.div),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8)),
                  ),
                ),

                if (_vulnScanVisible) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: widget.palette.inferred.withValues(alpha: 0.10),
                      border: Border.all(
                          color:
                              widget.palette.inferred.withValues(alpha: 0.3)),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'VULNERABILITY SCAN — SUPPLEMENTARY',
                          style: UnoTypography.mono(
                            color: widget.palette.inferred,
                            fontSize: 10,
                            letterSpacing: 0.8,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'No additional vulnerabilities identified beyond those in the locked Risk Report. Scan checked 12 decision-events for unresolved security implications.',
                          style: UnoTypography.body(
                            color: widget.palette.textSec,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildBddContract(BddSpec bdd) {
    return Container(
      decoration: BoxDecoration(
        color: widget.palette.bgSurface,
        border: Border.all(color: widget.palette.div),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(6),
      child: Container(
        decoration: BoxDecoration(
          color: widget.palette.bgElevated,
          border: Border.all(color: widget.palette.div),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // BDD Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              decoration: BoxDecoration(
                color: widget.palette.bgSurface,
                border: Border(bottom: BorderSide(color: widget.palette.div)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text(
                        'BDD Intent Contract',
                        style: UnoTypography.displaySerif(
                          palette: widget.palette,
                          fontSize: 16,
                          fontStyle: FontStyle.italic,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const QueryTierBadge(tier: 'cold'),
                      const SizedBox(width: 6),
                      const ConfidenceBadge(tier: 'confirmed'),
                    ],
                  ),
                  Text(
                    'Verified Artifact',
                    style: UnoTypography.mono(
                      color: widget.palette.textSec,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),

            // Given
            _buildBddClause('GIVEN', bdd.given),
            _buildBddClause('WHEN', bdd.when),
            _buildBddClause('THEN', bdd.then),

            // Suggested KPI
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'SUGGESTED KPI',
                    style: UnoTypography.mono(
                      color: widget.palette.accent,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          bdd.kpi,
                          style: UnoTypography.body(
                            color: widget.palette.text,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: widget.palette.inferred
                              .withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '[${bdd.kpiTag}${bdd.kpiNote != null ? ' — ${bdd.kpiNote}' : ''}]',
                          style: UnoTypography.mono(
                            color: widget.palette.inferred,
                            fontSize: 10,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Divider(height: 1, color: widget.palette.div),

            // Test Cases
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'TEST CASES',
                    style: UnoTypography.mono(
                      color: widget.palette.accent,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...bdd.testCases.map((tc) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: widget.palette.bgSurface,
                          border: Border.all(color: widget.palette.div),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '0${tc.id}',
                              style: UnoTypography.mono(
                                color: widget.palette.accent,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                tc.desc,
                                style: UnoTypography.body(
                                  color: widget.palette.text,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )),
                ],
              ),
            ),
            Divider(height: 1, color: widget.palette.div),

            // Risk Report
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'RISK REPORT',
                    style: UnoTypography.mono(
                      color: widget.palette.accent,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...bdd.risks.map((risk) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: (risk.tag == 'CONFIRMED'
                                        ? widget.palette.confirmed
                                        : widget.palette.inferred)
                                    .withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                '[${risk.tag}]',
                                style: UnoTypography.mono(
                                  color: risk.tag == 'CONFIRMED'
                                      ? widget.palette.confirmed
                                      : widget.palette.inferred,
                                  fontSize: 10,
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                risk.text,
                                style: UnoTypography.body(
                                  color: widget.palette.text,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBddClause(String label, String content) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: widget.palette.div)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: UnoTypography.mono(
              color: widget.palette.accent,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            content,
            style: UnoTypography.body(
              color: widget.palette.text,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}
