import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../theme/app_theme.dart';

/// Editorial Markdown & Artifact Compiler.
///
/// Parses full CommonMark and GitHub Flavored Markdown into native Flutter widgets:
/// - Fenced code blocks with language pills, file titles, line numbers, and instant copy button.
/// - Interactive file and artifact cards (`<artifact ...>` / ```filename).
/// - GFM tables with custom headers, cell alignment, zebra striping, and border dividers.
/// - Callout / Alert banners (> [!NOTE], > [!TIP], > [!WARNING], > [!IMPORTANT]).
/// - Rich headings (H1-H6) and comfortable paragraph typography (line height 1.65).
/// - Styled bullet lists, numbered lists, and task checkboxes (- [ ], - [x]).
/// - Styled blockquotes with accent border.
/// - Inline tokens: **bold**, *italic*, `inline code` badges, ~~strikethrough~~, and [links](url).
class MarkdownText extends StatelessWidget {
  final String text;
  final UnoPalette? palette;
  final TextStyle? baseStyle;
  final Widget? trailing;
  final bool selectable;
  final void Function(String url)? onLinkTap;
  final void Function(String filePath)? onFileTap;

  const MarkdownText({
    super.key,
    required this.text,
    this.palette,
    this.baseStyle,
    this.trailing,
    this.selectable = false,
    this.onLinkTap,
    this.onFileTap,
  });

  /// Utility that converts Markdown text into a clean, plain English string
  /// by stripping all Markdown characters.
  static String clean(String input) {
    if (input.isEmpty) return '';
    return input
        // Remove code blocks
        .replaceAll(RegExp(r'```[\s\S]*?```'), '')
        // Remove bold and italics
        .replaceAllMapped(RegExp(r'\*\*([^*]+)\*\*'), (m) => m[1] ?? '')
        .replaceAllMapped(RegExp(r'\*([^*]+)\*'), (m) => m[1] ?? '')
        .replaceAllMapped(RegExp(r'__([^_]+)__'), (m) => m[1] ?? '')
        .replaceAllMapped(RegExp(r'_([^_]+)_'), (m) => m[1] ?? '')
        // Remove code spans
        .replaceAllMapped(RegExp(r'`([^`]+)`'), (m) => m[1] ?? '')
        // Remove headers
        .replaceAll(RegExp(r'^\s*#{1,6}\s*', multiLine: true), '')
        // Remove horizontal rules
        .replaceAll(RegExp(r'^\s*[-*_]{3,}\s*$', multiLine: true), '')
        // Convert markdown bullets to clean bullets
        .replaceAll(RegExp(r'^\s*[-*+]\s+', multiLine: true), '• ')
        .trim();
  }

  @override
  Widget build(BuildContext context) {
    final effectivePalette = palette ?? UnoPalette.dark;

    final effectiveBaseStyle = baseStyle ??
        UnoTypography.body(
          color: effectivePalette.text,
          fontSize: 15,
          height: 1.65,
        );

    final blocks = _MarkdownParser.parse(text);

    if (blocks.isEmpty) {
      return const SizedBox.shrink();
    }

    final children = <Widget>[];

    for (int i = 0; i < blocks.length; i++) {
      final block = blocks[i];
      final isLastBlock = (i == blocks.length - 1);

      Widget blockWidget;
      if (block is _CodeBlockNode) {
        blockWidget = _UnoCodeBlock(
          node: block,
          palette: effectivePalette,
          onFileTap: onFileTap,
        );
      } else if (block is _ArtifactNode) {
        blockWidget = _UnoArtifactCard(
          node: block,
          palette: effectivePalette,
          onFileTap: onFileTap,
        );
      } else if (block is _TableNode) {
        blockWidget = _UnoTable(
          node: block,
          palette: effectivePalette,
          baseStyle: effectiveBaseStyle,
          onLinkTap: onLinkTap,
        );
      } else if (block is _CalloutNode) {
        blockWidget = _UnoCallout(
          node: block,
          palette: effectivePalette,
          baseStyle: effectiveBaseStyle,
          onLinkTap: onLinkTap,
        );
      } else if (block is _HeadingNode) {
        blockWidget = _buildHeading(block, effectivePalette, effectiveBaseStyle);
      } else if (block is _DividerNode) {
        blockWidget = Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Divider(
            color: effectivePalette.div,
            height: 1,
            thickness: 1,
          ),
        );
      } else if (block is _ListNode) {
        blockWidget = _buildList(block, effectivePalette, effectiveBaseStyle);
      } else if (block is _QuoteNode) {
        blockWidget = _buildQuote(block, effectivePalette, effectiveBaseStyle);
      } else if (block is _ParagraphNode) {
        blockWidget = _buildParagraph(
          block,
          effectivePalette,
          effectiveBaseStyle,
          trailingBadge: isLastBlock ? trailing : null,
        );
      } else {
        blockWidget = const SizedBox.shrink();
      }

      children.add(blockWidget);

      // Spacing between blocks
      if (!isLastBlock && block is! _DividerNode) {
        children.add(const SizedBox(height: 10));
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: children,
    );
  }

  Widget _buildHeading(_HeadingNode node, UnoPalette p, TextStyle base) {
    double size;
    FontWeight weight = FontWeight.w600;
    double topPad = 12;

    switch (node.level) {
      case 1:
        size = 22;
        weight = FontWeight.w700;
        topPad = 16;
        break;
      case 2:
        size = 18;
        weight = FontWeight.w700;
        topPad = 14;
        break;
      case 3:
        size = 16;
        weight = FontWeight.w600;
        topPad = 12;
        break;
      case 4:
        size = 15;
        weight = FontWeight.w600;
        topPad = 10;
        break;
      default:
        size = 14;
        weight = FontWeight.w600;
        topPad = 8;
    }

    return Padding(
      padding: EdgeInsets.only(top: topPad, bottom: 4),
      child: _InlineRichText(
        text: node.text,
        palette: p,
        style: base.copyWith(
          fontSize: size,
          fontWeight: weight,
          color: p.text,
          height: 1.35,
          letterSpacing: -0.2,
        ),
        selectable: selectable,
        onLinkTap: onLinkTap,
      ),
    );
  }

  Widget _buildList(_ListNode node, UnoPalette p, TextStyle base) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: node.items.map((item) {
        return Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (item.isTask)
                Padding(
                  padding: const EdgeInsets.only(top: 3, right: 8),
                  child: Icon(
                    item.isChecked ? LucideIcons.checkSquare : LucideIcons.square,
                    size: 15,
                    color: item.isChecked ? p.accent : p.textSec,
                  ),
                )
              else if (node.isOrdered)
                SizedBox(
                  width: 24,
                  child: Text(
                    item.prefix,
                    style: UnoTypography.mono(
                      color: p.accent,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                )
              else
                Padding(
                  padding: const EdgeInsets.only(top: 6, right: 10, left: 2),
                  child: Container(
                    width: 5,
                    height: 5,
                    decoration: BoxDecoration(
                      color: p.accent,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              Expanded(
                child: _InlineRichText(
                  text: item.content,
                  palette: p,
                  style: base,
                  selectable: selectable,
                  onLinkTap: onLinkTap,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildQuote(_QuoteNode node, UnoPalette p, TextStyle base) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.only(left: 14, top: 4, bottom: 4),
      decoration: BoxDecoration(
        border: Border(
          left: BorderSide(color: p.accent.withValues(alpha: 0.8), width: 3),
        ),
      ),
      child: _InlineRichText(
        text: node.text,
        palette: p,
        style: base.copyWith(
          color: p.textSec,
          fontStyle: FontStyle.italic,
        ),
        selectable: selectable,
        onLinkTap: onLinkTap,
      ),
    );
  }

  Widget _buildParagraph(
    _ParagraphNode node,
    UnoPalette p,
    TextStyle base, {
    Widget? trailingBadge,
  }) {
    return _InlineRichText(
      text: node.text,
      palette: p,
      style: base,
      trailingBadge: trailingBadge,
      selectable: selectable,
      onLinkTap: onLinkTap,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Fenced Code Block with Header Bar, Language Pill, and Copy
// ─────────────────────────────────────────────────────────────────────────────

class _UnoCodeBlock extends StatefulWidget {
  final _CodeBlockNode node;
  final UnoPalette palette;
  final void Function(String filePath)? onFileTap;

  const _UnoCodeBlock({
    required this.node,
    required this.palette,
    this.onFileTap,
  });

  @override
  State<_UnoCodeBlock> createState() => _UnoCodeBlockState();
}

class _UnoCodeBlockState extends State<_UnoCodeBlock> {
  bool _copied = false;

  void _copyCode() {
    Clipboard.setData(ClipboardData(text: widget.node.code));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final displayLang = widget.node.language.toUpperCase();
    final hasFilename = widget.node.filename != null && widget.node.filename!.isNotEmpty;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF131311),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: p.div, width: 1),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Header Top Bar ──
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF1D1C19),
              border: Border(bottom: BorderSide(color: p.div, width: 0.8)),
            ),
            child: Row(
              children: [
                if (hasFilename) ...[
                  Icon(LucideIcons.fileCode, size: 14, color: p.accent),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: () => widget.onFileTap?.call(widget.node.filename!),
                    child: Text(
                      widget.node.filename!,
                      style: UnoTypography.mono(
                        color: p.text,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                ],
                if (displayLang.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: p.bgElevated,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: p.div, width: 0.6),
                    ),
                    child: Text(
                      displayLang,
                      style: UnoTypography.mono(
                        color: p.textSec,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                const Spacer(),
                InkWell(
                  onTap: _copyCode,
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _copied ? LucideIcons.check : LucideIcons.copy,
                          size: 13,
                          color: _copied ? p.confirmed : p.textSec,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          _copied ? 'Copied!' : 'Copy code',
                          style: UnoTypography.mono(
                            color: _copied ? p.confirmed : p.textSec,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // ── Code Viewport ──
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.all(14),
            child: _SyntaxHighlightedCode(
              code: widget.node.code,
              language: widget.node.language,
              palette: p,
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Uno Interactive Artifact / File Card
// ─────────────────────────────────────────────────────────────────────────────

class _UnoArtifactCard extends StatefulWidget {
  final _ArtifactNode node;
  final UnoPalette palette;
  final void Function(String filePath)? onFileTap;

  const _UnoArtifactCard({
    required this.node,
    required this.palette,
    this.onFileTap,
  });

  @override
  State<_UnoArtifactCard> createState() => _UnoArtifactCardState();
}

class _UnoArtifactCardState extends State<_UnoArtifactCard> {
  bool _expanded = true;
  bool _copied = false;

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.node.content));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF161513),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: p.accent.withValues(alpha: 0.35), width: 1.2),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Bar
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFF201E1A),
                border: Border(bottom: BorderSide(color: p.div, width: 0.8)),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: p.accent.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Icon(LucideIcons.fileCode, size: 14, color: p.accent),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.node.title.isNotEmpty ? widget.node.title : 'Artifact',
                          style: UnoTypography.body(
                            color: p.text,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (widget.node.type.isNotEmpty)
                          Text(
                            widget.node.type,
                            style: UnoTypography.mono(
                              color: p.textSec,
                              fontSize: 10,
                            ),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: Icon(
                      _copied ? LucideIcons.check : LucideIcons.copy,
                      size: 14,
                      color: _copied ? p.confirmed : p.textSec,
                    ),
                    onPressed: _copy,
                    tooltip: 'Copy artifact content',
                    splashRadius: 16,
                  ),
                  Icon(
                    _expanded ? LucideIcons.chevronDown : LucideIcons.chevronRight,
                    size: 16,
                    color: p.textSec,
                  ),
                ],
              ),
            ),
          ),

          // Content body
          if (_expanded)
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.all(14),
              child: _SyntaxHighlightedCode(
                code: widget.node.content,
                language: widget.node.language,
                palette: p,
              ),
            ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Uno Table Renderer
// ─────────────────────────────────────────────────────────────────────────────

class _UnoTable extends StatelessWidget {
  final _TableNode node;
  final UnoPalette palette;
  final TextStyle baseStyle;
  final void Function(String url)? onLinkTap;

  const _UnoTable({
    required this.node,
    required this.palette,
    required this.baseStyle,
    this.onLinkTap,
  });

  @override
  Widget build(BuildContext context) {
    final p = palette;
    if (node.headers.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: p.bgSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: p.div, width: 1),
      ),
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowColor: WidgetStateProperty.all(const Color(0xFF22211D)),
          dataRowColor: WidgetStateProperty.resolveWith((states) {
            return const Color(0xFF181816);
          }),
          dividerThickness: 0.8,
          horizontalMargin: 16,
          columnSpacing: 24,
          headingTextStyle: UnoTypography.body(
            color: p.text,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
          columns: List.generate(node.headers.length, (colIdx) {
            final title = node.headers[colIdx];
            return DataColumn(
              label: Text(
                title.trim(),
                style: UnoTypography.body(
                  color: p.text,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            );
          }),
          rows: List.generate(node.rows.length, (rowIdx) {
            final row = node.rows[rowIdx];
            // Safe cell padding/clamping so unequal columns never throw
            final safeCells = List<String>.from(row);
            while (safeCells.length < node.headers.length) {
              safeCells.add('');
            }
            if (safeCells.length > node.headers.length) {
              safeCells.length = node.headers.length;
            }

            final isEven = rowIdx % 2 == 0;
            return DataRow(
              color: WidgetStateProperty.all(
                isEven ? const Color(0xFF1B1A17) : const Color(0xFF1F1E1B),
              ),
              cells: List.generate(node.headers.length, (cellIdx) {
                final cellContent = safeCells[cellIdx];
                return DataCell(
                  _InlineRichText(
                    text: cellContent.trim(),
                    palette: p,
                    style: baseStyle.copyWith(fontSize: 13),
                    onLinkTap: onLinkTap,
                  ),
                );
              }),
            );
          }),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Uno Callout / Alert Box
// ─────────────────────────────────────────────────────────────────────────────

class _UnoCallout extends StatelessWidget {
  final _CalloutNode node;
  final UnoPalette palette;
  final TextStyle baseStyle;
  final void Function(String url)? onLinkTap;

  const _UnoCallout({
    required this.node,
    required this.palette,
    required this.baseStyle,
    this.onLinkTap,
  });

  @override
  Widget build(BuildContext context) {
    final p = palette;
    Color borderCol;
    Color bgCol;
    IconData icon;

    switch (node.kind.toLowerCase()) {
      case 'tip':
        borderCol = const Color(0xFF38A169);
        bgCol = const Color(0xFF132219);
        icon = LucideIcons.lightbulb;
        break;
      case 'warning':
      case 'caution':
        borderCol = const Color(0xFFD97706);
        bgCol = const Color(0xFF251C12);
        icon = LucideIcons.alertTriangle;
        break;
      case 'important':
        borderCol = const Color(0xFF805AD5);
        bgCol = const Color(0xFF1D1728);
        icon = LucideIcons.flame;
        break;
      case 'note':
      default:
        borderCol = const Color(0xFF3182CE);
        bgCol = const Color(0xFF121C26);
        icon = LucideIcons.info;
        break;
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: bgCol,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: p.div, width: 0.8),
      ),
      clipBehavior: Clip.antiAlias,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(width: 4, color: borderCol),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(icon, size: 14, color: borderCol),
                        const SizedBox(width: 8),
                        Text(
                          node.kind.toUpperCase(),
                          style: UnoTypography.mono(
                            color: borderCol,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.6,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    _InlineRichText(
                      text: node.text,
                      palette: p,
                      style: baseStyle.copyWith(fontSize: 14, height: 1.5),
                      onLinkTap: onLinkTap,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Syntax Highlighting Engine (Clean Zero-Dependency Lexer)
// ─────────────────────────────────────────────────────────────────────────────

class _SyntaxHighlightedCode extends StatelessWidget {
  final String code;
  final String language;
  final UnoPalette palette;

  const _SyntaxHighlightedCode({
    required this.code,
    required this.language,
    required this.palette,
  });

  @override
  Widget build(BuildContext context) {
    final spans = _tokenizeCode(code, language.toLowerCase(), palette);

    return SelectableText.rich(
      TextSpan(
        style: UnoTypography.mono(
          color: const Color(0xFFDCD8D0),
          fontSize: 13,
        ).copyWith(height: 1.55),
        children: spans,
      ),
    );
  }

  List<TextSpan> _tokenizeCode(String source, String lang, UnoPalette p) {
    final spans = <TextSpan>[];
    final lines = source.split('\n');

    final kwColor = p.accent; // Warm terracotta/coral
    const strColor = Color(0xFF88B97C); // Olive green
    const numColor = Color(0xFFE5C07B); // Amber gold
    final commentColor = p.textSec; // Muted gray
    const typeColor = Color(0xFF61AFEF); // Cyan/sky blue

    final keywords = {
      'import', 'export', 'from', 'as', 'def', 'class', 'struct', 'interface',
      'func', 'function', 'return', 'yield', 'async', 'await', 'const', 'let',
      'var', 'final', 'val', 'type', 'switch', 'case', 'default', 'break',
      'continue', 'if', 'else', 'elif', 'for', 'while', 'do', 'try', 'catch',
      'except', 'finally', 'throw', 'raise', 'new', 'this', 'self', 'super',
      'true', 'false', 'null', 'nil', 'None', 'void', 'bool', 'int', 'string',
      'package', 'pub', 'use', 'impl', 'fn', 'mut', 'select', 'where',
      'join', 'group', 'by', 'order', 'insert', 'update', 'delete', 'create',
      'table', 'drop', 'alter'
    };

    for (int i = 0; i < lines.length; i++) {
      final line = lines[i];

      // Comment line check
      final trimmed = line.trimLeft();
      if (trimmed.startsWith('//') || trimmed.startsWith('#') || trimmed.startsWith('--')) {
        spans.add(TextSpan(text: line, style: TextStyle(color: commentColor, fontStyle: FontStyle.italic)));
      } else {
        // Tokenize line by regex matching tokens
        final tokenRegex = RegExp(r'''(//.*|#.*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`[^`]*`|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b|[^\sA-Za-z0-9_]+|\s+)''');
        for (final m in tokenRegex.allMatches(line)) {
          final token = m.group(0)!;
          if (token.startsWith('//') || token.startsWith('#')) {
            spans.add(TextSpan(text: token, style: TextStyle(color: commentColor, fontStyle: FontStyle.italic)));
          } else if ((token.startsWith('"') && token.endsWith('"')) ||
              (token.startsWith("'") && token.endsWith("'")) ||
              (token.startsWith('`') && token.endsWith('`'))) {
            spans.add(TextSpan(text: token, style: const TextStyle(color: strColor)));
          } else if (RegExp(r'^\d+(\.\d+)?$').hasMatch(token)) {
            spans.add(TextSpan(text: token, style: const TextStyle(color: numColor)));
          } else if (keywords.contains(token.toLowerCase())) {
            spans.add(TextSpan(text: token, style: TextStyle(color: kwColor, fontWeight: FontWeight.w600)));
          } else if (RegExp(r'^[A-Z][a-zA-Z0-9_]*$').hasMatch(token)) {
            spans.add(TextSpan(text: token, style: const TextStyle(color: typeColor)));
          } else {
            spans.add(TextSpan(text: token));
          }
        }
      }

      if (i < lines.length - 1) {
        spans.add(const TextSpan(text: '\n'));
      }
    }

    return spans;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Rich Inline Parser (Bold, Italic, Code, Links, Strikethrough)
// ─────────────────────────────────────────────────────────────────────────────

class _InlineRichText extends StatelessWidget {
  final String text;
  final UnoPalette palette;
  final TextStyle style;
  final Widget? trailingBadge;
  final bool selectable;
  final void Function(String url)? onLinkTap;

  const _InlineRichText({
    required this.text,
    required this.palette,
    required this.style,
    this.trailingBadge,
    this.selectable = false,
    this.onLinkTap,
  });

  @override
  Widget build(BuildContext context) {
    final spans = <InlineSpan>[];
    final tokenRegex = RegExp(
      r'(\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_([^_]+)_|~~[^~]+~~|`[^`]+`|\[([^\]]+)\]\(([^)]+)\))',
    );

    int lastIndex = 0;
    for (final match in tokenRegex.allMatches(text)) {
      if (match.start > lastIndex) {
        spans.add(TextSpan(text: text.substring(lastIndex, match.start), style: style));
      }

      final token = match.group(0)!;
      if (token.startsWith('**') && token.endsWith('**')) {
        spans.add(
          TextSpan(
            text: token.substring(2, token.length - 2),
            style: style.copyWith(
              fontWeight: FontWeight.w700,
              color: palette.text,
            ),
          ),
        );
      } else if (token.startsWith('*') && token.endsWith('*')) {
        spans.add(
          TextSpan(
            text: token.substring(1, token.length - 1),
            style: style.copyWith(fontStyle: FontStyle.italic),
          ),
        );
      } else if (token.startsWith('__') && token.endsWith('__')) {
        spans.add(
          TextSpan(
            text: token.substring(2, token.length - 2),
            style: style.copyWith(fontWeight: FontWeight.w700, color: palette.text),
          ),
        );
      } else if (token.startsWith('_') && token.endsWith('_')) {
        spans.add(
          TextSpan(
            text: token.substring(1, token.length - 1),
            style: style.copyWith(fontStyle: FontStyle.italic),
          ),
        );
      } else if (token.startsWith('~~') && token.endsWith('~~')) {
        spans.add(
          TextSpan(
            text: token.substring(2, token.length - 2),
            style: style.copyWith(decoration: TextDecoration.lineThrough),
          ),
        );
      } else if (token.startsWith('`') && token.endsWith('`')) {
        spans.add(
          WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
              margin: const EdgeInsets.symmetric(horizontal: 2),
              decoration: BoxDecoration(
                color: palette.bgElevated,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: palette.div, width: 0.8),
              ),
              child: Text(
                token.substring(1, token.length - 1),
                style: UnoTypography.mono(
                  color: palette.accent,
                  fontSize: (style.fontSize ?? 14) * 0.88,
                ),
              ),
            ),
          ),
        );
      } else if (token.startsWith('[') && token.contains('](') && token.endsWith(')')) {
        final linkMatch = RegExp(r'\[([^\]]+)\]\(([^)]+)\)').firstMatch(token);
        if (linkMatch != null) {
          final label = linkMatch.group(1)!;
          final url = linkMatch.group(2)!;
          spans.add(
            WidgetSpan(
              alignment: PlaceholderAlignment.baseline,
              baseline: TextBaseline.alphabetic,
              child: InkWell(
                onTap: () => onLinkTap?.call(url),
                child: Text(
                  label,
                  style: style.copyWith(
                    color: palette.accent,
                    decoration: TextDecoration.underline,
                    decorationColor: palette.accent.withValues(alpha: 0.5),
                  ),
                ),
              ),
            ),
          );
        }
      }

      lastIndex = match.end;
    }

    if (lastIndex < text.length) {
      spans.add(TextSpan(text: text.substring(lastIndex), style: style));
    }

    if (trailingBadge != null) {
      spans.add(const WidgetSpan(child: SizedBox(width: 8)));
      spans.add(
        WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: trailingBadge!,
        ),
      );
    }

    if (selectable) {
      return SelectableText.rich(TextSpan(children: spans));
    }

    return Text.rich(TextSpan(children: spans));
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AST Nodes and Multi-Block Markdown Parser
// ─────────────────────────────────────────────────────────────────────────────

abstract class _MarkdownNode {}

class _HeadingNode extends _MarkdownNode {
  final int level;
  final String text;
  _HeadingNode(this.level, this.text);
}

class _DividerNode extends _MarkdownNode {}

class _CodeBlockNode extends _MarkdownNode {
  final String language;
  final String? filename;
  final String code;
  _CodeBlockNode({required this.language, this.filename, required this.code});
}

class _ArtifactNode extends _MarkdownNode {
  final String identifier;
  final String type;
  final String title;
  final String language;
  final String content;
  _ArtifactNode({
    required this.identifier,
    required this.type,
    required this.title,
    required this.language,
    required this.content,
  });
}

class _TableNode extends _MarkdownNode {
  final List<String> headers;
  final List<TextAlign> alignments;
  final List<List<String>> rows;
  _TableNode({
    required this.headers,
    this.alignments = const [],
    required this.rows,
  });
}

class _CalloutNode extends _MarkdownNode {
  final String kind;
  final String text;
  _CalloutNode({required this.kind, required this.text});
}

class _QuoteNode extends _MarkdownNode {
  final String text;
  _QuoteNode(this.text);
}

class _ListItemNode {
  final String prefix;
  final bool isTask;
  final bool isChecked;
  final String content;
  _ListItemNode({
    required this.prefix,
    this.isTask = false,
    this.isChecked = false,
    required this.content,
  });
}

class _ListNode extends _MarkdownNode {
  final bool isOrdered;
  final List<_ListItemNode> items;
  _ListNode({required this.isOrdered, required this.items});
}

class _ParagraphNode extends _MarkdownNode {
  final String text;
  _ParagraphNode(this.text);
}

class _MarkdownParser {
  static List<_MarkdownNode> parse(String rawText) {
    final nodes = <_MarkdownNode>[];
    final lines = rawText.split('\n');
    int i = 0;

    while (i < lines.length) {
      final line = lines[i];
      final trimmed = line.trim();

      if (trimmed.isEmpty) {
        i++;
        continue;
      }

      // ── Uno Artifact Tag: <artifact ...> or <antArtifact ...> ──
      if (trimmed.startsWith('<artifact') || trimmed.startsWith('<antArtifact')) {
        final artifactMatch = RegExp(r'<(?:antA|a)rtifact(?:\s+identifier="([^"]*)")?(?:\s+type="([^"]*)")?(?:\s+title="([^"]*)")?[^>]*>').firstMatch(trimmed);
        final id = artifactMatch?.group(1) ?? '';
        final type = artifactMatch?.group(2) ?? '';
        final title = artifactMatch?.group(3) ?? '';
        
        final contentLines = <String>[];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith('</artifact>') && !lines[i].trim().startsWith('</antArtifact>')) {
          contentLines.add(lines[i]);
          i++;
        }
        if (i < lines.length) i++; // skip closing tag

        nodes.add(_ArtifactNode(
          identifier: id,
          type: type,
          title: title,
          language: _detectLanguage(type, title),
          content: contentLines.join('\n'),
        ));
        continue;
      }

      // ── Fenced Code Block: ``` or ~~~ ──
      if (trimmed.startsWith('```') || trimmed.startsWith('~~~')) {
        final fence = trimmed.substring(0, 3);
        final info = trimmed.substring(3).trim();
        String lang = '';
        String? filename;

        // Extract language and filename (e.g. ```dart:lib/main.dart or ```python title="app.py")
        if (info.contains(':')) {
          final parts = info.split(':');
          lang = parts[0].trim();
          filename = parts.sublist(1).join(':').trim();
        } else if (info.contains('title="') || info.contains('filename="')) {
          final m = RegExp(r'(?:title|filename)="([^"]+)"').firstMatch(info);
          if (m != null) filename = m.group(1);
          lang = info.split(RegExp(r'\s+'))[0];
        } else {
          lang = info;
        }

        final codeLines = <String>[];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith(fence)) {
          codeLines.add(lines[i]);
          i++;
        }
        if (i < lines.length) i++; // skip closing fence

        nodes.add(_CodeBlockNode(
          language: lang,
          filename: filename,
          code: codeLines.join('\n'),
        ));
        continue;
      }

      // ── Horizontal Rule: ---, ***, ___ ──
      if (RegExp(r'^[-*_]{3,}$').hasMatch(trimmed)) {
        nodes.add(_DividerNode());
        i++;
        continue;
      }

      // ── Heading: #, ##, ###, #### ──
      if (trimmed.startsWith('#')) {
        int level = 0;
        while (level < trimmed.length && trimmed[level] == '#') {
          level++;
        }
        if (level <= 6 && (level == trimmed.length || trimmed[level] == ' ')) {
          nodes.add(_HeadingNode(level, trimmed.substring(level).trim()));
          i++;
          continue;
        }
      }

      // ── Callout / Alert: > [!NOTE], > [!TIP], > [!WARNING], etc. ──
      final calloutMatch = RegExp(r'^>\s*\[!(NOTE|TIP|WARNING|IMPORTANT|CAUTION)\]\s*(.*)$', caseSensitive: false).firstMatch(trimmed);
      if (calloutMatch != null) {
        final kind = calloutMatch.group(1)!;
        final firstLine = calloutMatch.group(2) ?? '';
        final quoteLines = <String>[];
        if (firstLine.isNotEmpty) quoteLines.add(firstLine);

        i++;
        while (i < lines.length && lines[i].trim().startsWith('>')) {
          quoteLines.add(lines[i].trim().substring(1).trim());
          i++;
        }

        nodes.add(_CalloutNode(kind: kind, text: quoteLines.join('\n')));
        continue;
      }

      // ── Standard Blockquote: > text ──
      if (trimmed.startsWith('>')) {
        final quoteLines = <String>[trimmed.substring(1).trim()];
        i++;
        while (i < lines.length && lines[i].trim().startsWith('>')) {
          quoteLines.add(lines[i].trim().substring(1).trim());
          i++;
        }
        nodes.add(_QuoteNode(quoteLines.join('\n')));
        continue;
      }

      // ── GFM Table: | Col 1 | Col 2 | or Col 1 | Col 2 ──
      if (line.contains('|') && i + 1 < lines.length && _isTableDelimiter(lines[i + 1])) {
        final rawHeaders = _parseTableRow(trimmed);
        final alignments = _parseTableAlignments(lines[i + 1]);
        i += 2; // skip header and delimiter

        final rows = <List<String>>[];
        while (i < lines.length) {
          final rowLine = lines[i].trim();
          if (rowLine.isEmpty || !rowLine.contains('|')) break;
          if (rowLine.startsWith('```') || rowLine.startsWith('~~~') || rowLine.startsWith('#')) break;

          final cells = _parseTableRow(rowLine);
          rows.add(cells);
          i++;
        }

        nodes.add(_TableNode(headers: rawHeaders, alignments: alignments, rows: rows));
        continue;
      }

      // ── Lists: Bullet lists or Numbered lists ──
      final isBullet = RegExp(r'^[-*+]\s+').hasMatch(trimmed);
      final isNumbered = RegExp(r'^\d+\.\s+').hasMatch(trimmed);
      if (isBullet || isNumbered) {
        final isOrdered = isNumbered;
        final items = <_ListItemNode>[];

        while (i < lines.length) {
          final l = lines[i].trim();
          if (l.isEmpty) break;

          final bMatch = RegExp(r'^[-*+]\s+(.*)').firstMatch(l);
          final nMatch = RegExp(r'^(\d+\.)\s+(.*)').firstMatch(l);

          if (bMatch != null) {
            final content = bMatch.group(1)!;
            // Check for task checkbox: [ ] or [x]
            final taskMatch = RegExp(r'^\[([ xX])\]\s+(.*)').firstMatch(content);
            if (taskMatch != null) {
              items.add(_ListItemNode(
                prefix: '',
                isTask: true,
                isChecked: taskMatch.group(1)!.toLowerCase() == 'x',
                content: taskMatch.group(2)!,
              ));
            } else {
              items.add(_ListItemNode(prefix: '•', content: content));
            }
            i++;
          } else if (nMatch != null) {
            items.add(_ListItemNode(
              prefix: nMatch.group(1)!,
              content: nMatch.group(2)!,
            ));
            i++;
          } else {
            break;
          }
        }

        nodes.add(_ListNode(isOrdered: isOrdered, items: items));
        continue;
      }

      // ── Normal Paragraph ──
      // Collect contiguous lines until blank line or block start
      final paraLines = <String>[trimmed];
      i++;
      while (i < lines.length) {
        final nextLine = lines[i].trim();
        if (nextLine.isEmpty ||
            nextLine.startsWith('#') ||
            nextLine.startsWith('```') ||
            nextLine.startsWith('~~~') ||
            nextLine.startsWith('>') ||
            RegExp(r'^[-*_]{3,}$').hasMatch(nextLine) ||
            RegExp(r'^[-*+]\s+').hasMatch(nextLine) ||
            RegExp(r'^\d+\.\s+').hasMatch(nextLine) ||
            (nextLine.startsWith('|') && nextLine.endsWith('|'))) {
          break;
        }
        paraLines.add(nextLine);
        i++;
      }

      nodes.add(_ParagraphNode(paraLines.join(' ')));
    }

    return nodes;
  }

  static String _detectLanguage(String type, String title) {
    final lowerTitle = title.toLowerCase();
    if (lowerTitle.endsWith('.dart')) return 'dart';
    if (lowerTitle.endsWith('.py')) return 'python';
    if (lowerTitle.endsWith('.ts') || lowerTitle.endsWith('.tsx')) return 'typescript';
    if (lowerTitle.endsWith('.js') || lowerTitle.endsWith('.jsx')) return 'javascript';
    if (lowerTitle.endsWith('.json')) return 'json';
    if (lowerTitle.endsWith('.sh') || lowerTitle.endsWith('.bash')) return 'bash';
    if (lowerTitle.endsWith('.yaml') || lowerTitle.endsWith('.yml')) return 'yaml';
    if (lowerTitle.endsWith('.sql')) return 'sql';
    if (type.contains('markdown')) return 'markdown';
    return type;
  }

  static bool _isTableDelimiter(String line) {
    var trimmed = line.trim();
    if (!trimmed.contains('-')) return false;
    if (trimmed.startsWith('|')) trimmed = trimmed.substring(1);
    if (trimmed.endsWith('|')) trimmed = trimmed.substring(0, trimmed.length - 1);
    final parts = trimmed.split('|').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return false;
    return parts.every((p) => RegExp(r'^:?-+:?$').hasMatch(p));
  }

  static List<String> _parseTableRow(String line) {
    var trimmed = line.trim();
    if (trimmed.startsWith('|')) trimmed = trimmed.substring(1);
    if (trimmed.endsWith('|')) trimmed = trimmed.substring(0, trimmed.length - 1);
    return trimmed.split('|').map((s) => s.trim()).toList();
  }

  static List<TextAlign> _parseTableAlignments(String delimiterLine) {
    var trimmed = delimiterLine.trim();
    if (trimmed.startsWith('|')) trimmed = trimmed.substring(1);
    if (trimmed.endsWith('|')) trimmed = trimmed.substring(0, trimmed.length - 1);
    final parts = trimmed.split('|').map((s) => s.trim()).toList();
    return parts.map((p) {
      final leftColon = p.startsWith(':');
      final rightColon = p.endsWith(':');
      if (leftColon && rightColon) return TextAlign.center;
      if (rightColon) return TextAlign.right;
      return TextAlign.left;
    }).toList();
  }
}
