import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../theme/app_theme.dart';

class ChatInputBox extends StatefulWidget {
  final TextEditingController controller;
  final UnoPalette palette;
  final VoidCallback onSubmit;
  final Function(String) onChipSelected;
  final List<String> suggestions;
  final String? placeholder;

  const ChatInputBox({
    super.key,
    required this.controller,
    required this.palette,
    required this.onSubmit,
    required this.onChipSelected,
    this.suggestions = const [],
    this.placeholder,
  });

  @override
  State<ChatInputBox> createState() => _ChatInputBoxState();
}

class _ChatInputBoxState extends State<ChatInputBox> {
  bool _thinkingEnabled = false;
  String _thinkingMode = 'warm'; // warm, cold, hot
  String? _activeSearchMode; // research, web
  bool _showSuggestions = false;

  final LayerLink _layerLink = LayerLink();

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _onTextChanged() {
    final text = widget.controller.text.trim();
    setState(() {
      _showSuggestions = text.isNotEmpty && widget.suggestions.isNotEmpty;
    });
  }

  Color _tierColor() {
    switch (_thinkingMode) {
      case 'hot':
        return UnoPalette.queryHot;
      case 'cold':
        return UnoPalette.queryCold;
      case 'warm':
      default:
        return UnoPalette.queryWarm;
    }
  }

  @override
  Widget build(BuildContext context) {
    final canSubmit = widget.controller.text.trim().isNotEmpty;
    final tierColor = _tierColor();

    return CompositedTransformTarget(
      link: _layerLink,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Active Search Mode Badge (if any)
          if (_activeSearchMode != null) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: widget.palette.accent.withValues(alpha: 0.12),
                border: Border.all(
                  color: widget.palette.accent.withValues(alpha: 0.35),
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _activeSearchMode == 'research'
                        ? LucideIcons.bookOpen
                        : LucideIcons.globe,
                    size: 11,
                    color: widget.palette.accent,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _activeSearchMode == 'research'
                        ? 'Research'
                        : 'Web Search',
                    style: UnoTypography.body(
                      color: widget.palette.accent,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(width: 4),
                  InkWell(
                    onTap: () => setState(() => _activeSearchMode = null),
                    child: Icon(
                      LucideIcons.x,
                      size: 12,
                      color: widget.palette.accent,
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Main Card
          Container(
            decoration: BoxDecoration(
              color: widget.palette.bgElevated,
              border: Border.all(color: widget.palette.div),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.06),
                  blurRadius: 30,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Text input
                TextField(
                  controller: widget.controller,
                  maxLines: 4,
                  minLines: 1,
                  style: UnoTypography.body(
                    color: widget.palette.text,
                    fontSize: 15,
                  ),
                  decoration: InputDecoration(
                    hintText: widget.placeholder ??
                        'Ask about a merge, a ticket, or a decision on your project…',
                    hintStyle: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 15,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(vertical: 6),
                  ),
                  onSubmitted: (_) {
                    if (canSubmit) {
                      widget.onSubmit();
                      setState(() => _showSuggestions = false);
                    }
                  },
                ),

                const SizedBox(height: 8),
                Divider(
                  height: 1,
                  thickness: 1,
                  color: widget.palette.div.withValues(alpha: 0.55),
                ),
                const SizedBox(height: 6),

                // Bottom toolbar inside card
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    // Left buttons: Plus, Attach, Thinking Capsule
                    Row(
                      children: [
                        // Plus button
                        PopupMenuButton<String>(
                          tooltip: 'Add context or search mode',
                          offset: const Offset(0, -140),
                          color: widget.palette.bgElevated,
                          shape: RoundedRectangleBorder(
                            side: BorderSide(color: widget.palette.div),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          onSelected: (mode) {
                            if (mode == 'research' || mode == 'web') {
                              setState(() => _activeSearchMode = mode);
                            }
                          },
                          itemBuilder: (context) => [
                            PopupMenuItem(
                              value: 'files',
                              child: Row(
                                children: [
                                  Icon(LucideIcons.paperclip,
                                      size: 13, color: widget.palette.textSec),
                                  const SizedBox(width: 8),
                                  Text('Upload files',
                                      style: UnoTypography.body(
                                          color: widget.palette.text,
                                          fontSize: 13)),
                                ],
                              ),
                            ),
                            PopupMenuItem(
                              value: 'project',
                              child: Row(
                                children: [
                                  Icon(LucideIcons.folderPlus,
                                      size: 13, color: widget.palette.textSec),
                                  const SizedBox(width: 8),
                                  Text('Add to project',
                                      style: UnoTypography.body(
                                          color: widget.palette.text,
                                          fontSize: 13)),
                                ],
                              ),
                            ),
                            PopupMenuItem(
                              value: 'web',
                              child: Row(
                                children: [
                                  Icon(LucideIcons.globe,
                                      size: 13, color: widget.palette.textSec),
                                  const SizedBox(width: 8),
                                  Text('Web search',
                                      style: UnoTypography.body(
                                          color: widget.palette.text,
                                          fontSize: 13)),
                                ],
                              ),
                            ),
                            PopupMenuItem(
                              value: 'research',
                              child: Row(
                                children: [
                                  Icon(LucideIcons.bookOpen,
                                      size: 13, color: widget.palette.textSec),
                                  const SizedBox(width: 8),
                                  Text('Deep research',
                                      style: UnoTypography.body(
                                          color: widget.palette.text,
                                          fontSize: 13)),
                                ],
                              ),
                            ),
                          ],
                          child: Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                              border: Border.all(color: widget.palette.div),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(
                              LucideIcons.plus,
                              size: 14,
                              color: widget.palette.textSec,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),

                        // Paperclip attach button
                        Tooltip(
                          message: 'Attach context file or ticket',
                          child: InkWell(
                            onTap: () {},
                            borderRadius: BorderRadius.circular(8),
                            child: Container(
                              width: 32,
                              height: 32,
                              decoration: BoxDecoration(
                                border: Border.all(color: widget.palette.div),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Icon(
                                LucideIcons.paperclip,
                                size: 14,
                                color: widget.palette.textSec,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),

                        // Thinking Tier Button
                        PopupMenuButton<String>(
                          tooltip: 'Select reasoning tier',
                          offset: const Offset(0, -130),
                          color: widget.palette.bgElevated,
                          shape: RoundedRectangleBorder(
                            side: BorderSide(color: widget.palette.div),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          onSelected: (tier) {
                            setState(() {
                              _thinkingMode = tier;
                              _thinkingEnabled = true;
                            });
                          },
                          itemBuilder: (context) => [
                            PopupMenuItem(
                              value: 'warm',
                              child: Row(
                                children: [
                                  Container(
                                    width: 8,
                                    height: 8,
                                    decoration: const BoxDecoration(
                                      color: UnoPalette.queryWarm,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Warm (Balanced reasoning)',
                                    style: UnoTypography.body(
                                      color: widget.palette.text,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            PopupMenuItem(
                              value: 'cold',
                              child: Row(
                                children: [
                                  Container(
                                    width: 8,
                                    height: 8,
                                    decoration: const BoxDecoration(
                                      color: UnoPalette.queryCold,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Cold (Deep multi-hop proof)',
                                    style: UnoTypography.body(
                                      color: widget.palette.text,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            PopupMenuItem(
                              value: 'hot',
                              child: Row(
                                children: [
                                  Container(
                                    width: 8,
                                    height: 8,
                                    decoration: const BoxDecoration(
                                      color: UnoPalette.queryHot,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Hot (Quick indexed answer)',
                                    style: UnoTypography.body(
                                      color: widget.palette.text,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          child: Container(
                            height: 30,
                            padding: const EdgeInsets.symmetric(horizontal: 11),
                            decoration: BoxDecoration(
                              color: _thinkingEnabled
                                  ? tierColor.withValues(alpha: 0.10)
                                  : Colors.transparent,
                              border: Border.all(
                                color: _thinkingEnabled
                                    ? tierColor.withValues(alpha: 0.5)
                                    : widget.palette.div,
                              ),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  LucideIcons.zap,
                                  size: 12,
                                  color: _thinkingEnabled
                                      ? tierColor
                                      : widget.palette.textSec,
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  _thinkingEnabled
                                      ? '$_thinkingMode tier'
                                      : 'Thinking',
                                  style: UnoTypography.body(
                                    color: _thinkingEnabled
                                        ? tierColor
                                        : widget.palette.textSec,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                Icon(
                                  LucideIcons.chevronDown,
                                  size: 11,
                                  color: _thinkingEnabled
                                      ? tierColor
                                      : widget.palette.textSec,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),

                    // Right buttons: Mic & Send
                    Row(
                      children: [
                        InkWell(
                          onTap: () {},
                          borderRadius: BorderRadius.circular(8),
                          child: SizedBox(
                            width: 32,
                            height: 32,
                            child: Center(
                              child: Icon(
                                LucideIcons.mic,
                                size: 14,
                                color: widget.palette.textSec,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        InkWell(
                          onTap: canSubmit ? widget.onSubmit : null,
                          borderRadius: BorderRadius.circular(16),
                          child: Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                              color: canSubmit
                                  ? widget.palette.accent
                                  : widget.palette.div,
                              shape: BoxShape.circle,
                            ),
                            child: Center(
                              child: Icon(
                                LucideIcons.arrowUp,
                                size: 14,
                                color: canSubmit
                                    ? Colors.white
                                    : widget.palette.textSec,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Autocomplete suggestions popup
          if (_showSuggestions) ...[
            Container(
              margin: const EdgeInsets.only(top: 8),
              decoration: BoxDecoration(
                color: widget.palette.bgElevated,
                border: Border.all(color: widget.palette.div),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.14),
                    blurRadius: 24,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: widget.suggestions
                    .where((s) => s.toLowerCase().contains(
                        widget.controller.text.trim().toLowerCase()))
                    .map((s) => InkWell(
                          onTap: () {
                            widget.onChipSelected(s);
                            setState(() => _showSuggestions = false);
                          },
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 10,
                            ),
                            child: Text(
                              s,
                              style: UnoTypography.body(
                                color: widget.palette.textSec,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ))
                    .toList(),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
