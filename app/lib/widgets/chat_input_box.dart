import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
  bool _thinkingEnabled = true;
  String _thinkingMode = 'warm'; // warm, cold, hot
  String? _activeSearchMode; // research, web
  bool _showSuggestions = false;
  final List<String> _attachedFileNames = [];

  Future<void> _handlePickFiles() async {
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.any,
      );
      if (result.isNotEmpty) {
        setState(() {
          for (final f in result) {
            if (f.name.isNotEmpty && !_attachedFileNames.contains(f.name)) {
              _attachedFileNames.add(f.name);
            }
          }
        });
      }
    } catch (e) {
      debugPrint('File picker error: $e');
    }
  }

  final LayerLink _layerLink = LayerLink();
  final LayerLink _thinkingButtonLink = LayerLink();
  OverlayEntry? _thinkingMenuOverlay;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _closeThinkingMenu();
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _toggleThinkingMenu() {
    if (_thinkingMenuOverlay != null) {
      _closeThinkingMenu();
    } else {
      _openThinkingMenu();
    }
  }

  void _closeThinkingMenu() {
    _thinkingMenuOverlay?.remove();
    _thinkingMenuOverlay = null;
  }

  void _openThinkingMenu() {
    _closeThinkingMenu();
    final overlay = Overlay.of(context);
    _thinkingMenuOverlay = OverlayEntry(
      builder: (context) {
        return Stack(
          children: [
            // Tap outside to dismiss
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: _closeThinkingMenu,
                child: const SizedBox.expand(),
              ),
            ),
            // Floating menu positioned right above the button
            CompositedTransformFollower(
              link: _thinkingButtonLink,
              showWhenUnlinked: false,
              targetAnchor: Alignment.topLeft,
              followerAnchor: Alignment.bottomLeft,
              offset: const Offset(0, -10),
              child: Material(
                color: Colors.transparent,
                child: StatefulBuilder(
                  builder: (context, setMenuState) {
                    return _buildThinkingMenuCard(setMenuState);
                  },
                ),
              ),
            ),
          ],
        );
      },
    );
    overlay.insert(_thinkingMenuOverlay!);
  }

  Widget _buildThinkingMenuCard(StateSetter setMenuState) {
    return Container(
      width: 210,
      decoration: BoxDecoration(
        color: const Color(0xFF232321),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF383835)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.5),
            blurRadius: 22,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header: "Thinking" + Toggle Switch
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Thinking',
                style: UnoTypography.body(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              // Custom iOS/pill style Switch matching Screenshot 2
              GestureDetector(
                onTap: () {
                  setState(() {
                    _thinkingEnabled = !_thinkingEnabled;
                  });
                  setMenuState(() {});
                },
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  width: 44,
                  height: 24,
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    color: _thinkingEnabled
                        ? const Color(0xFFDA7756)
                        : const Color(0xFF3F3F46),
                  ),
                  child: Align(
                    alignment: _thinkingEnabled
                        ? Alignment.centerRight
                        : Alignment.centerLeft,
                    child: Container(
                      width: 18,
                      height: 18,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _thinkingEnabled
                            ? const Color(0xFFFEF3C7)
                            : const Color(0xFFA1A1AA),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Options: Hot, Warm, Cold
          _buildTierOption(
            tier: 'hot',
            title: 'Hot',
            subtitle: 'Quick answers',
            dotColor: const Color(0xFFF87171),
            accentColor: const Color(0xFFEF4444),
            bgColor: const Color(0xFF4C2422),
            setMenuState: setMenuState,
          ),
          const SizedBox(height: 4),
          _buildTierOption(
            tier: 'warm',
            title: 'Warm',
            subtitle: 'Balanced',
            dotColor: const Color(0xFFFBBF24),
            accentColor: const Color(0xFFEAB308),
            bgColor: const Color(0xFF563F24),
            setMenuState: setMenuState,
          ),
          const SizedBox(height: 4),
          _buildTierOption(
            tier: 'cold',
            title: 'Cold',
            subtitle: 'Deep reasoning',
            dotColor: const Color(0xFF2DD4BF),
            accentColor: const Color(0xFF14B8A6),
            bgColor: const Color(0xFF1E3A37),
            setMenuState: setMenuState,
          ),
        ],
      ),
    );
  }

  Widget _buildTierOption({
    required String tier,
    required String title,
    required String subtitle,
    required Color dotColor,
    required Color accentColor,
    required Color bgColor,
    required StateSetter setMenuState,
  }) {
    final isSelected = _thinkingMode == tier && _thinkingEnabled;

    return InkWell(
      onTap: () {
        setState(() {
          _thinkingMode = tier;
          _thinkingEnabled = true;
        });
        setMenuState(() {});
      },
      borderRadius: BorderRadius.circular(8),
      child: Container(
        decoration: BoxDecoration(
          color: isSelected ? bgColor : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: Border(
            left: BorderSide(
              color: isSelected ? accentColor : Colors.transparent,
              width: 3.0,
            ),
          ),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: dotColor,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: UnoTypography.body(
                    color: isSelected ? dotColor : const Color(0xFFE4E4E7),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  subtitle,
                  style: UnoTypography.body(
                    color: isSelected
                        ? const Color(0xFFE4E4E7)
                        : const Color(0xFFA1A1AA),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
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
        return const Color(0xFFF87171);
      case 'cold':
        return const Color(0xFF2DD4BF);
      case 'warm':
      default:
        return const Color(0xFFE8A455);
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
                // Text input with Enter submission and Shift+Enter for newline
                Focus(
                  onKeyEvent: (node, event) {
                    if (event is KeyDownEvent) {
                      final isEnter = event.logicalKey == LogicalKeyboardKey.enter ||
                          event.logicalKey == LogicalKeyboardKey.numpadEnter;
                      if (isEnter) {
                        if (HardwareKeyboard.instance.isShiftPressed) {
                          // Allow multiline insertion on Shift+Enter
                          return KeyEventResult.ignored;
                        } else {
                          // Submit on Enter keydown
                          if (canSubmit) {
                            widget.onSubmit();
                            setState(() {
                              _showSuggestions = false;
                              _attachedFileNames.clear();
                            });
                          }
                          return KeyEventResult.handled;
                        }
                      }
                    }
                    return KeyEventResult.ignored;
                  },
                  child: TextField(
                    controller: widget.controller,
                    maxLines: 4,
                    minLines: 1,
                    textInputAction: TextInputAction.send,
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
                        setState(() {
                          _showSuggestions = false;
                          _attachedFileNames.clear();
                        });
                      }
                    },
                  ),
                ),

                if (_attachedFileNames.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: _attachedFileNames.map((name) {
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: widget.palette.accent.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: widget.palette.accent.withValues(alpha: 0.3)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(LucideIcons.paperclip, size: 12, color: widget.palette.accent),
                            const SizedBox(width: 4),
                            ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 160),
                              child: Text(
                                name,
                                style: UnoTypography.mono(fontSize: 11, color: widget.palette.text),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 4),
                            InkWell(
                              onTap: () => setState(() => _attachedFileNames.remove(name)),
                              child: Icon(LucideIcons.x, size: 12, color: widget.palette.textSec),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ],

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
                            onTap: _handlePickFiles,
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
                        CompositedTransformTarget(
                          link: _thinkingButtonLink,
                          child: InkWell(
                            onTap: _toggleThinkingMenu,
                            borderRadius: BorderRadius.circular(20),
                            child: Container(
                              height: 32,
                              padding: const EdgeInsets.symmetric(horizontal: 12),
                              decoration: BoxDecoration(
                                color: _thinkingEnabled
                                    ? tierColor.withValues(alpha: 0.12)
                                    : Colors.transparent,
                                border: Border.all(
                                  color: _thinkingEnabled
                                      ? tierColor
                                      : widget.palette.div,
                                  width: 1.2,
                                ),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
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
                                        ? '${_thinkingMode[0].toUpperCase()}${_thinkingMode.substring(1)} tier'
                                        : 'Thinking',
                                    style: UnoTypography.body(
                                      color: _thinkingEnabled
                                          ? tierColor
                                          : widget.palette.textSec,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                  const SizedBox(width: 5),
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
