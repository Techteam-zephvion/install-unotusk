import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/badges.dart';
import '../widgets/chat_input_box.dart';
import '../widgets/markdown_text.dart';
import '../widgets/thinking_scanner.dart';
import '../services/api_service.dart';

class ChatScreen extends StatefulWidget {
  final UnoPalette palette;
  final List<ChatMessage> messages;
  final bool isGenerating;
  final void Function(
    String query, {
    String thinkingTier,
    bool thinkingEnabled,
  }) onSubmitQuery;

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

  final String? userName;
  final String? projectName;
  final void Function(String file, String? lines)? onCitationTap;

  const ChatScreen({
    super.key,
    required this.palette,
    required this.messages,
    required this.isGenerating,
    required this.onSubmitQuery,
    this.userName,
    this.projectName,
    this.onCitationTap,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _showScrollToBottom = false;
  bool _thinkingEnabled = true;
  String _thinkingTier = 'warm';

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      if (!_scrollController.hasClients) return;
      final show = _scrollController.position.maxScrollExtent - _scrollController.offset > 150;
      if (show != _showScrollToBottom) {
        setState(() => _showScrollToBottom = show);
      }
    });
  }

  String _getGreetingHeadline(String name) {
    final hour = DateTime.now().hour;
    final List<String> phrases;

    if (hour >= 5 && hour < 12) {
      phrases = [
        'Morning, $name. What are we tracing?',
        'Coffee’s ready. What’s the merge?',
        'Let’s make sense of the code, $name.',
      ];
    } else if (hour >= 12 && hour < 17) {
      phrases = [
        'Afternoon, $name. Got a merge to untangle?',
        'Let’s trace it, $name.',
        'Which decision are we unpacking?',
      ];
    } else if (hour >= 17 && hour < 22) {
      phrases = [
        'Evening, $name. Any last merge?',
        'Let’s review today’s changes.',
        'One more trace before you sign off?',
      ];
    } else {
      phrases = [
        'Late night, $name. Let’s trace it.',
        'Night shift. What’s breaking?',
        'Quiet hours. What are we digging into?',
      ];
    }

    final slot = (DateTime.now().minute ~/ 15) % phrases.length;
    return phrases[slot];
  }

  void _handleSubmit() {
    final text = _inputController.text.trim();
    if (text.isEmpty || widget.isGenerating) return;
    _inputController.clear();
    widget.onSubmitQuery(
      text,
      thinkingTier: _thinkingEnabled ? _thinkingTier : 'hot',
      thinkingEnabled: _thinkingEnabled,
    );

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
    final name = widget.userName != null && widget.userName!.isNotEmpty
        ? widget.userName!
        : 'Dev Lead';

    return LayoutBuilder(
      builder: (context, constraints) {
        final heroWidth =
            (constraints.maxWidth * 0.72).clamp(320.0, 820.0);

        return Container(
          decoration: BoxDecoration(
            gradient: widget.palette.heroGlowGradient,
          ),
          child: SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: Center(
                child: Container(
                  width: heroWidth,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 20, vertical: 40),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Text(
                        _getGreetingHeadline(name),
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: UnoTypography.displaySerif(
                          palette: widget.palette,
                          fontSize: 27,
                          lineHeight: 1.15,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        widget.projectName != null &&
                                widget.projectName!.isNotEmpty
                            ? 'Investigate ${formatDisplayTitle(widget.projectName!)}, architecture, or code decisions'
                            : 'Investigate your project, architecture, or code decisions',
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: UnoTypography.body(
                          color: widget.palette.textSec,
                          fontSize: 14.5,
                        ),
                      ),
                      const SizedBox(height: 26),
                      ChatInputBox(
                        controller: _inputController,
                        palette: widget.palette,
                        thinkingEnabled: _thinkingEnabled,
                        thinkingTier: _thinkingTier,
                        onThinkingEnabledChanged: (val) =>
                            setState(() => _thinkingEnabled = val),
                        onThinkingTierChanged: (tier) =>
                            setState(() => _thinkingTier = tier),
                        onSubmit: _handleSubmit,
                        onChipSelected: (prompt) {
                          _inputController.text = prompt;
                          _handleSubmit();
                        },
                        suggestions: ChatScreen.querySuggestions,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Unotusk can make mistakes. Verify important project decisions, ADRs, and tickets.',
                        textAlign: TextAlign.center,
                        style: UnoTypography.body(
                          color: widget.palette.textMuted,
                          fontSize: 11.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildChatStream() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final contentWidth = (constraints.maxWidth * 0.80)
            .clamp(320.0, (constraints.maxWidth - 32).clamp(320.0, 960.0));

        return Container(
          decoration: BoxDecoration(
            gradient: widget.palette.heroGlowGradient,
          ),
          child: Stack(
            children: [
              // Messages scroll area — comfortable reading column
              Positioned.fill(
                child: ScrollConfiguration(
                  behavior: ScrollConfiguration.of(context).copyWith(
                    scrollbars: false,
                  ),
                  child: RawScrollbar(
                    controller: _scrollController,
                    thumbVisibility: false,
                    trackVisibility: false,
                    thickness: 2.0,
                    radius: const Radius.circular(2),
                    thumbColor: widget.palette.textSec.withValues(alpha: 0.25),
                    fadeDuration: const Duration(milliseconds: 250),
                    padding: const EdgeInsets.only(right: 4, top: 8, bottom: 8),
                    child: ListView.builder(
                      controller: _scrollController,
                      physics: const AlwaysScrollableScrollPhysics(
                        parent: BouncingScrollPhysics(),
                      ),
                      padding: const EdgeInsets.fromLTRB(0, 28, 0, 196),
                      itemCount: widget.messages.length,
                      itemBuilder: (context, index) {
                        final msg = widget.messages[index];
                        return Center(
                          child: SizedBox(
                            width: contentWidth,
                            child: _buildMessageItem(msg),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ),

              // Floating Bottom Input with Seamless Canvas Fade
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
                        widget.palette.bgBase.withValues(alpha: 0.94),
                        widget.palette.bgBase,
                      ],
                      stops: const [0.0, 0.42, 1.0],
                    ),
                  ),
                  padding: const EdgeInsets.fromLTRB(0, 26, 0, 14),
                  child: Center(
                    child: SizedBox(
                      width: contentWidth,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_showScrollToBottom)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: MouseRegion(
                                cursor: SystemMouseCursors.click,
                                child: GestureDetector(
                                  onTap: () {
                                    _scrollController.animateTo(
                                      _scrollController
                                          .position.maxScrollExtent,
                                      duration:
                                          const Duration(milliseconds: 300),
                                      curve: Curves.easeOutCubic,
                                    );
                                  },
                                  child: Container(
                                    width: 32,
                                    height: 32,
                                    decoration: BoxDecoration(
                                      color: widget.palette.bgElevated,
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                          color: widget.palette.div, width: 1),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black
                                              .withValues(alpha: 0.16),
                                          blurRadius: 10,
                                          offset: const Offset(0, 3),
                                        ),
                                      ],
                                    ),
                                    child: Icon(
                                      LucideIcons.arrowDown,
                                      size: 14.5,
                                      color: widget.palette.accent,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ChatInputBox(
                            controller: _inputController,
                            palette: widget.palette,
                            thinkingEnabled: _thinkingEnabled,
                            thinkingTier: _thinkingTier,
                            onThinkingEnabledChanged: (val) =>
                                setState(() => _thinkingEnabled = val),
                            onThinkingTierChanged: (tier) =>
                                setState(() => _thinkingTier = tier),
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
                          Text(
                            'Unotusk can make mistakes. Verify important project decisions, ADRs, and tickets.',
                            textAlign: TextAlign.center,
                            style: UnoTypography.body(
                              color: widget.palette.textMuted,
                              fontSize: 11.5,
                            ),
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
      },
    );
  }

  Widget _buildMessageItem(ChatMessage msg) {
    if (msg.kind == MessageKind.query) {
      return _UserQueryBubble(
        text: msg.text ?? '',
        palette: widget.palette,
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
        width: double.infinity,
        child: _ResponseCard(
          data: msg.data!,
          palette: widget.palette,
          onCitationTap: widget.onCitationTap,
        ),
      );
    }

    return const SizedBox.shrink();
  }
}

class _UserQueryBubble extends StatefulWidget {
  final String text;
  final UnoPalette palette;

  const _UserQueryBubble({
    required this.text,
    required this.palette,
  });

  @override
  State<_UserQueryBubble> createState() => _UserQueryBubbleState();
}

class _UserQueryBubbleState extends State<_UserQueryBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _animController;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;
  bool _isHovered = false;
  bool _copied = false;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 280),
    );
    _fadeAnim = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOut,
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.12),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutCubic,
    ));
    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.text));
    setState(() => _copied = true);
    Future.delayed(const Duration(milliseconds: 1600), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.palette.isDark;
    // Refined warm ivory conversation card in Dark Mode; midnight navy in Light Mode
    final bubbleBg =
        isDark ? const Color(0xFFE9DFD0) : const Color(0xFF0B1020);
    final bubbleText =
        isDark ? const Color(0xFF0B1020) : const Color(0xFFF4F1EC);
    final bubblePalette = isDark ? UnoPalette.light : UnoPalette.dark;
    final hoverBase =
        isDark ? const Color(0xFFE9DFD0) : const Color(0xFF0B1020);

    return FadeTransition(
      opacity: _fadeAnim,
      child: SlideTransition(
        position: _slideAnim,
        child: Padding(
          padding: const EdgeInsets.only(top: 12, bottom: 28),
          child: MouseRegion(
            onEnter: (_) => setState(() => _isHovered = true),
            onExit: (_) => setState(() => _isHovered = false),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Subtle hover-only Copy button outside the card
                AnimatedOpacity(
                  opacity: (_isHovered || _copied) ? 1.0 : 0.0,
                  duration: const Duration(milliseconds: 160),
                  curve: Curves.easeOutCubic,
                  child: Padding(
                    padding: const EdgeInsets.only(right: 10),
                    child: Tooltip(
                      message: _copied ? 'Copied' : 'Copy prompt',
                      child: MouseRegion(
                        cursor: SystemMouseCursors.click,
                        child: GestureDetector(
                          onTap: _copy,
                          behavior: HitTestBehavior.opaque,
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 150),
                            width: 28,
                            height: 28,
                            decoration: BoxDecoration(
                              color: hoverBase.withValues(
                                  alpha: _copied ? 0.10 : 0.05),
                              borderRadius: BorderRadius.circular(7),
                              border: Border.all(
                                color: widget.palette.div.withValues(alpha: 0.6),
                                width: 1,
                              ),
                            ),
                            alignment: Alignment.center,
                            child: Icon(
                              _copied ? LucideIcons.check : LucideIcons.copy,
                              size: 13,
                              color: _copied
                                  ? widget.palette.live
                                  : widget.palette.textSec,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),

                // Refined warm-ivory conversation card
                Flexible(
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 620),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 19, vertical: 12),
                    decoration: BoxDecoration(
                      color: bubbleBg,
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF050814)
                              .withValues(alpha: isDark ? 0.22 : 0.10),
                          blurRadius: 10,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: MarkdownText(
                      text: widget.text,
                      palette: bubblePalette,
                      selectable: true,
                      baseStyle: GoogleFonts.inter(
                        color: bubbleText,
                        fontSize: 14.8,
                        height: 1.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ResponseCard extends StatefulWidget {
  final QueryResponseData data;
  final UnoPalette palette;
  final void Function(String file, String? lines)? onCitationTap;

  const _ResponseCard({
    required this.data,
    required this.palette,
    this.onCitationTap,
  });

  @override
  State<_ResponseCard> createState() => _ResponseCardState();
}

class _ResponseCardState extends State<_ResponseCard> {
  bool _copied = false;
  String? _feedback; // up, down
  bool _thoughtExpanded = false;
  bool _thoughtHovered = false;
  final Set<String> _expandedSteps = {};

  String _sanitizeMeta(String meta) {
    if (meta.isEmpty) return meta;
    var cleaned = meta
        // Remove "via http://..." or "via 10.0.0.59:28000" or "via 127.0.0.1:..."
        .replaceAll(
            RegExp(r'\bvia\s+(https?://)?[^\s·]+', caseSensitive: false), '')
        // Remove any remaining URLs like http://... or https://...
        .replaceAll(RegExp(r'https?://[^\s·]+', caseSensitive: false), '')
        // Remove raw IPs with or without port e.g. 10.0.0.59:28000 or 127.0.0.1
        .replaceAll(
            RegExp(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b'), '')
        // Remove leftover port numbers like :28000 or :28101
        .replaceAll(RegExp(r':\d{4,5}\b'), '')
        // Clean up redundant dots/separators
        .replaceAll(RegExp(r'(\s*·\s*)+'), ' · ')
        .replaceAll(RegExp(r'^\s*·\s*'), '')
        .replaceAll(RegExp(r'\s*·\s*$'), '')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();

    if (cleaned.isEmpty) return 'Grounded';
    return cleaned;
  }

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
    final p = widget.palette;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Minimal, quiet Reasoning / Thought Process disclosure
        if (widget.data.reasoning != null) ...[
          _buildThoughtProcessDrawer(widget.data.reasoning!),
          const SizedBox(height: 14),
        ],

        // BDD Spec Viewer (if available)
        if (widget.data.bdd != null) ...[
          _buildBddContract(widget.data.bdd!),
          const SizedBox(height: 16),
        ],

        // Clean Editorial Response Prose (Calm, readable technical document)
        if (widget.data.bdd == null) ...[
          ...widget.data.segments.map((seg) => Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: MarkdownText(
                  text: ApiService.synthesizeMermaidDiagram(
                    question: '',
                    content: seg.text,
                    citations: widget.data.reasoning?.citations ?? const [],
                    evidence: widget.data.reasoning?.evidence ?? const [],
                  ),
                  palette: p,
                  selectable: true,
                  baseStyle: GoogleFonts.inter(
                    color: p.isDark
                        ? p.text.withValues(alpha: 0.90)
                        : p.text.withValues(alpha: 0.92),
                    fontSize: 15.0,
                    height: 1.72,
                    fontWeight: FontWeight.w400,
                  ),
                  trailing: seg.tag != null
                      ? TagBadge(
                          tag: seg.tag!,
                          palette: p,
                        )
                      : null,
                ),
              )),
        ],

        // Minimal, quiet Response Action Strip
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(
            children: [
              _ResponseActionButton(
                icon: _copied ? LucideIcons.check : LucideIcons.copy,
                label: _copied ? 'Copied' : null,
                tooltip: 'Copy response',
                palette: p,
                activeColor: _copied ? p.live : null,
                onTap: _copyToClipboard,
              ),
              const SizedBox(width: 4),
              _ResponseActionButton(
                icon: LucideIcons.thumbsUp,
                tooltip: 'Helpful',
                palette: p,
                isActive: _feedback == 'up',
                onTap: () {
                  setState(() {
                    _feedback = _feedback == 'up' ? null : 'up';
                  });
                },
              ),
              const SizedBox(width: 4),
              _ResponseActionButton(
                icon: LucideIcons.thumbsDown,
                tooltip: 'Needs improvement',
                palette: p,
                isActive: _feedback == 'down',
                onTap: () {
                  setState(() {
                    _feedback = _feedback == 'down' ? null : 'down';
                  });
                },
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _sanitizeMeta(widget.data.meta),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: UnoTypography.body(
                    color: p.textSec.withValues(alpha: 0.75),
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildThoughtProcessDrawer(ReasoningModel reasoning) {
    final p = widget.palette;
    final isDark = p.isDark;
    final hoverBase =
        isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);
    final isActive = _thoughtExpanded || _thoughtHovered;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Whisper-quiet inline disclosure trigger
        MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) => setState(() => _thoughtHovered = true),
          onExit: (_) => setState(() => _thoughtHovered = false),
          child: GestureDetector(
            onTap: () => setState(() => _thoughtExpanded = !_thoughtExpanded),
            behavior: HitTestBehavior.opaque,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              curve: Curves.easeOutCubic,
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              decoration: BoxDecoration(
                color: hoverBase.withValues(alpha: isActive ? 0.05 : 0.0),
                borderRadius: BorderRadius.circular(7),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    LucideIcons.sparkles,
                    size: 13.5,
                    color: isActive ? p.accent : p.accentMuted,
                  ),
                  const SizedBox(width: 7),
                  Text(
                    'Thought for 2.6s',
                    style: UnoTypography.body(
                      color: isActive ? p.text : p.textSec,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(width: 4),
                  AnimatedRotation(
                    turns: _thoughtExpanded ? 0.25 : 0.0,
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOutCubic,
                    child: Icon(
                      LucideIcons.chevronRight,
                      size: 12.5,
                      color: isActive ? p.text : p.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        // Smooth animated minimal disclosure panel (left guide rail, no noisy boxes/pills)
        AnimatedSize(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          alignment: Alignment.topLeft,
          child: _thoughtExpanded
              ? Padding(
                  padding: const EdgeInsets.only(left: 14, top: 8, bottom: 4),
                  child: Container(
                    padding: const EdgeInsets.only(left: 14, top: 2, bottom: 2),
                    decoration: BoxDecoration(
                      border: Border(
                        left: BorderSide(
                          color: p.div,
                          width: 1.5,
                        ),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (reasoning.citations.isNotEmpty)
                          _buildReasoningRow(
                            id: 'citations',
                            icon: LucideIcons.fileText,
                            title: 'Sources',
                            summary: '${reasoning.citations.length} files',
                            content: Wrap(
                              spacing: 6,
                              runSpacing: 6,
                              children: reasoning.citations.map((cite) {
                                return Tooltip(
                                  message: 'Jump to $cite in Files tab',
                                  child: InkWell(
                                    onTap: () => widget.onCitationTap?.call(cite, null),
                                    borderRadius: BorderRadius.circular(6),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 8, vertical: 3.5),
                                      decoration: BoxDecoration(
                                        color: hoverBase.withValues(alpha: 0.05),
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(
                                            color: p.accent.withValues(alpha: 0.25)),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(LucideIcons.fileCode,
                                              size: 11, color: p.accent),
                                          const SizedBox(width: 5),
                                          Text(
                                            cite,
                                            style: UnoTypography.mono(
                                              color: p.text,
                                              fontSize: 11,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                        if (reasoning.evidence.isNotEmpty)
                          _buildReasoningRow(
                            id: 'evidence',
                            icon: LucideIcons.code,
                            title: 'Code evidence',
                            summary: '${reasoning.evidence.length} snippets',
                            content: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: reasoning.evidence.take(5).map((ev) {
                                return Tooltip(
                                  message: 'Jump to ${ev.file}${ev.lines != null ? ':${ev.lines}' : ''} in Files tab',
                                  child: InkWell(
                                    onTap: () => widget.onCitationTap?.call(ev.file, ev.lines),
                                    borderRadius: BorderRadius.circular(8),
                                    child: Container(
                                      margin: const EdgeInsets.only(bottom: 6),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 10, vertical: 8),
                                      decoration: BoxDecoration(
                                        color: hoverBase.withValues(alpha: 0.04),
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                            color: p.accent.withValues(alpha: 0.20)),
                                      ),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Icon(LucideIcons.code,
                                                  size: 12, color: p.accent),
                                              const SizedBox(width: 6),
                                              Expanded(
                                                child: Text(
                                                  ev.file +
                                                      (ev.lines != null
                                                          ? ':${ev.lines}'
                                                          : ''),
                                                  style: UnoTypography.mono(
                                                    color: p.text,
                                                    fontSize: 11,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                  overflow: TextOverflow.ellipsis,
                                                ),
                                              ),
                                              Icon(LucideIcons.arrowUpRight,
                                                  size: 12, color: p.accent),
                                            ],
                                          ),
                                          if (ev.snippet != null &&
                                              ev.snippet!.isNotEmpty) ...[
                                            const SizedBox(height: 5),
                                            Text(
                                              ev.snippet!,
                                              style: UnoTypography.mono(
                                                color: p.textSec,
                                                fontSize: 10.5,
                                                height: 1.45,
                                              ),
                                              maxLines: 4,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                        if (reasoning.ontologyEdges.isNotEmpty)
                          _buildReasoningRow(
                            id: 'ontology',
                            icon: LucideIcons.gitFork,
                            title: 'Graph context',
                            summary:
                                '${reasoning.ontologyEdges.length} connections',
                            content: Wrap(
                              spacing: 6,
                              runSpacing: 6,
                              children: reasoning.ontologyEdges.map((edge) {
                                return Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 3.5),
                                  decoration: BoxDecoration(
                                    color: hoverBase.withValues(alpha: 0.045),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    edge,
                                    style: UnoTypography.mono(
                                      color: p.textSec,
                                      fontSize: 11,
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                        _buildReasoningRow(
                          id: 'score',
                          icon: LucideIcons.shieldCheck,
                          title: 'Verification',
                          summary:
                              '${(reasoning.compositeScore * 100).round()}% grounded',
                          content: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: ClipRRect(
                                      borderRadius: BorderRadius.circular(3),
                                      child: LinearProgressIndicator(
                                        value: reasoning.compositeScore
                                            .clamp(0.0, 1.0),
                                        minHeight: 4,
                                        backgroundColor: p.div,
                                        valueColor: AlwaysStoppedAnimation(
                                            p.accent),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Text(
                                    reasoning.compositeScore.toStringAsFixed(2),
                                    style: UnoTypography.mono(
                                      color: p.text,
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                              if (reasoning.components.isNotEmpty) ...[
                                const SizedBox(height: 8),
                                ...reasoning.components.map((c) => Padding(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 2),
                                      child: Row(
                                        children: [
                                          SizedBox(
                                            width: 90,
                                            child: Text(
                                              c.label,
                                              style: UnoTypography.body(
                                                color: p.textSec,
                                                fontSize: 11.5,
                                              ),
                                            ),
                                          ),
                                          Expanded(
                                            child: ClipRRect(
                                              borderRadius:
                                                  BorderRadius.circular(2),
                                              child: LinearProgressIndicator(
                                                value: c.score.clamp(0.0, 1.0),
                                                minHeight: 3,
                                                backgroundColor: p.div,
                                                valueColor:
                                                    AlwaysStoppedAnimation(
                                                        p.textSec.withValues(
                                                            alpha: 0.65)),
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          SizedBox(
                                            width: 34,
                                            child: Text(
                                              c.score.toStringAsFixed(2),
                                              textAlign: TextAlign.right,
                                              style: UnoTypography.mono(
                                                color: p.textSec,
                                                fontSize: 11,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    )),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }

  Widget _buildReasoningRow({
    required String id,
    required IconData icon,
    required String title,
    required String summary,
    required Widget content,
  }) {
    final isExpanded = _expandedSteps.contains(id);
    return _MinimalReasoningStep(
      icon: icon,
      title: title,
      summary: summary,
      isExpanded: isExpanded,
      palette: widget.palette,
      onToggle: () {
        setState(() {
          if (isExpanded) {
            _expandedSteps.remove(id);
          } else {
            _expandedSteps.add(id);
          }
        });
      },
      content: content,
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
                          fontSize: 16.5,
                          fontStyle: FontStyle.italic,
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

class _ResponseActionButton extends StatefulWidget {
  final IconData icon;
  final String? label;
  final String tooltip;
  final UnoPalette palette;
  final bool isActive;
  final Color? activeColor;
  final VoidCallback onTap;

  const _ResponseActionButton({
    required this.icon,
    this.label,
    required this.tooltip,
    required this.palette,
    this.isActive = false,
    this.activeColor,
    required this.onTap,
  });

  @override
  State<_ResponseActionButton> createState() => _ResponseActionButtonState();
}

class _ResponseActionButtonState extends State<_ResponseActionButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final hoverBase =
        p.isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);
    final fg = widget.activeColor ??
        (widget.isActive ? p.accent : (_hovered ? p.text : p.textSec));

    return Tooltip(
      message: widget.tooltip,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 140),
            curve: Curves.easeOutCubic,
            height: 28,
            padding: EdgeInsets.symmetric(
              horizontal: widget.label != null ? 9 : 7,
            ),
            decoration: BoxDecoration(
              color: hoverBase.withValues(
                alpha: (_hovered || widget.isActive) ? 0.06 : 0.0,
              ),
              borderRadius: BorderRadius.circular(7),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(widget.icon, size: 13.5, color: fg),
                if (widget.label != null) ...[
                  const SizedBox(width: 5),
                  Text(
                    widget.label!,
                    style: UnoTypography.body(
                      color: fg,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MinimalReasoningStep extends StatefulWidget {
  final IconData icon;
  final String title;
  final String summary;
  final bool isExpanded;
  final UnoPalette palette;
  final VoidCallback onToggle;
  final Widget content;

  const _MinimalReasoningStep({
    required this.icon,
    required this.title,
    required this.summary,
    required this.isExpanded,
    required this.palette,
    required this.onToggle,
    required this.content,
  });

  @override
  State<_MinimalReasoningStep> createState() => _MinimalReasoningStepState();
}

class _MinimalReasoningStepState extends State<_MinimalReasoningStep> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final hoverBase =
        p.isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);
    final highlighted = _hovered || widget.isExpanded;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) => setState(() => _hovered = true),
          onExit: (_) => setState(() => _hovered = false),
          child: GestureDetector(
            onTap: widget.onToggle,
            behavior: HitTestBehavior.opaque,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 140),
              curve: Curves.easeOutCubic,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              decoration: BoxDecoration(
                color: hoverBase.withValues(alpha: _hovered ? 0.04 : 0.0),
                borderRadius: BorderRadius.circular(7),
              ),
              child: Row(
                children: [
                  Icon(
                    widget.icon,
                    size: 13,
                    color: highlighted ? p.text : p.textSec,
                  ),
                  const SizedBox(width: 9),
                  Text(
                    widget.title,
                    style: UnoTypography.body(
                      color: highlighted ? p.text : p.textSec,
                      fontSize: 13,
                      fontWeight:
                          widget.isExpanded ? FontWeight.w500 : FontWeight.w400,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    widget.summary,
                    style: UnoTypography.body(
                      color: p.textSec.withValues(alpha: 0.78),
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(width: 6),
                  AnimatedRotation(
                    turns: widget.isExpanded ? 0.25 : 0.0,
                    duration: const Duration(milliseconds: 160),
                    curve: Curves.easeOutCubic,
                    child: Icon(
                      LucideIcons.chevronRight,
                      size: 12,
                      color: p.textSec,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
          alignment: Alignment.topLeft,
          child: widget.isExpanded
              ? Padding(
                  padding: const EdgeInsets.fromLTRB(30, 4, 8, 10),
                  child: widget.content,
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }
}
