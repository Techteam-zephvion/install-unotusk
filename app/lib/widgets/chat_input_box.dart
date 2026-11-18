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
  final bool thinkingEnabled;
  final String thinkingTier;
  final ValueChanged<bool>? onThinkingEnabledChanged;
  final ValueChanged<String>? onThinkingTierChanged;

  const ChatInputBox({
    super.key,
    required this.controller,
    required this.palette,
    required this.onSubmit,
    required this.onChipSelected,
    this.suggestions = const [],
    this.placeholder,
    this.thinkingEnabled = true,
    this.thinkingTier = 'warm',
    this.onThinkingEnabledChanged,
    this.onThinkingTierChanged,
  });

  @override
  State<ChatInputBox> createState() => _ChatInputBoxState();
}

class _ChatInputBoxState extends State<ChatInputBox>
    with TickerProviderStateMixin {
  late bool _thinkingEnabled;
  late String _selectedModel; // hot, warm, cold
  String? _activeSearchMode; // research, web
  bool _showSuggestions = false;
  final List<String> _attachedFileNames = [];

  final FocusNode _focusNode = FocusNode();
  bool _isCardHovered = false;
  bool _sendBtnHovered = false;
  bool _plusBtnHovered = false;
  bool _attachBtnHovered = false;
  bool _thinkingToggleHovered = false;
  bool _modelBtnHovered = false;

  // Model Dropdown Animation & Overlay
  late final AnimationController _modelAnim;
  late final Animation<double> _modelFade;
  late final Animation<double> _modelScale;
  late final Animation<Offset> _modelSlide;
  OverlayEntry? _modelMenuOverlay;

  // Plus Menu Animation & Overlay
  late final AnimationController _plusAnim;
  late final Animation<double> _plusFade;
  late final Animation<double> _plusScale;
  late final Animation<Offset> _plusSlide;
  late final Animation<double> _plusRotate;
  OverlayEntry? _plusMenuOverlay;

  final LayerLink _layerLink = LayerLink();
  final LayerLink _modelButtonLink = LayerLink();
  final LayerLink _plusButtonLink = LayerLink();

  static const List<Map<String, String>> _models = [
    {'id': 'hot', 'label': 'Hot'},
    {'id': 'warm', 'label': 'Warm'},
    {'id': 'cold', 'label': 'Cold'},
  ];

  String get _selectedModelLabel {
    for (final m in _models) {
      if (m['id'] == _selectedModel) return m['label']!;
    }
    return 'Warm';
  }

  @override
  void initState() {
    super.initState();
    _thinkingEnabled = widget.thinkingEnabled;
    _selectedModel = widget.thinkingTier;
    widget.controller.addListener(_onTextChanged);
    _focusNode.addListener(_onFocusChanged);

    // Model Menu Animations
    _modelAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 190),
      reverseDuration: const Duration(milliseconds: 140),
    );
    _modelFade = CurvedAnimation(
      parent: _modelAnim,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    _modelScale = Tween<double>(begin: 0.95, end: 1.0).animate(
      CurvedAnimation(
        parent: _modelAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );
    _modelSlide = Tween<Offset>(
      begin: const Offset(0, 0.05),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _modelAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );

    // Plus Menu Animations
    _plusAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 190),
      reverseDuration: const Duration(milliseconds: 140),
    );
    _plusFade = CurvedAnimation(
      parent: _plusAnim,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    _plusScale = Tween<double>(begin: 0.95, end: 1.0).animate(
      CurvedAnimation(
        parent: _plusAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );
    _plusSlide = Tween<Offset>(
      begin: const Offset(0, 0.05),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _plusAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );
    _plusRotate = Tween<double>(begin: 0.0, end: 0.125).animate(
      CurvedAnimation(
        parent: _plusAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );
  }

  @override
  void didUpdateWidget(covariant ChatInputBox oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.thinkingEnabled != oldWidget.thinkingEnabled) {
      _thinkingEnabled = widget.thinkingEnabled;
    }
    if (widget.thinkingTier != oldWidget.thinkingTier) {
      _selectedModel = widget.thinkingTier;
    }
  }

  @override
  void dispose() {
    _closeModelMenu(animated: false);
    _closePlusMenu(animated: false);
    _modelAnim.dispose();
    _plusAnim.dispose();
    _focusNode.removeListener(_onFocusChanged);
    _focusNode.dispose();
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _onFocusChanged() {
    if (mounted) setState(() {});
  }

  void _onTextChanged() {
    final text = widget.controller.text.trim();
    if (mounted) {
      setState(() {
        _showSuggestions = text.isNotEmpty && widget.suggestions.isNotEmpty;
      });
    }
  }

  Future<void> _handlePickFiles() async {
    try {
      final result = await FilePicker.pickFiles(type: FileType.any);
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

  // --- Model Dropdown Overlay ---
  void _toggleModelMenu() {
    if (_modelMenuOverlay != null) {
      _closeModelMenu();
    } else {
      _closePlusMenu(animated: false);
      _openModelMenu();
    }
  }

  void _openModelMenu() {
    _closeModelMenu(animated: false);
    final overlay = Overlay.of(context);
    _modelMenuOverlay = OverlayEntry(
      builder: (context) {
        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () => _closeModelMenu(),
                child: const SizedBox.expand(),
              ),
            ),
            CompositedTransformFollower(
              link: _modelButtonLink,
              showWhenUnlinked: false,
              targetAnchor: Alignment.topLeft,
              followerAnchor: Alignment.bottomLeft,
              offset: const Offset(0, -8),
              child: Material(
                color: Colors.transparent,
                child: _buildModelMenuCard(),
              ),
            ),
          ],
        );
      },
    );
    overlay.insert(_modelMenuOverlay!);
    _modelAnim.forward(from: 0.0);
    setState(() {});
  }

  Future<void> _closeModelMenu({bool animated = true}) async {
    if (_modelMenuOverlay == null) return;
    if (animated) {
      await _modelAnim.reverse();
    }
    _modelMenuOverlay?.remove();
    _modelMenuOverlay = null;
    if (mounted) setState(() {});
  }

  Widget _buildModelMenuCard() {
    final isDark = widget.palette.isDark;
    final menuBg = isDark ? widget.palette.bgElevated : const Color(0xFFFFFFFF);
    final menuBorder = widget.palette.div;

    return AnimatedBuilder(
      animation: _modelAnim,
      builder: (context, child) {
        return FadeTransition(
          opacity: _modelFade,
          child: SlideTransition(
            position: _modelSlide,
            child: ScaleTransition(
              scale: _modelScale,
              alignment: Alignment.bottomLeft,
              child: child,
            ),
          ),
        );
      },
      child: Container(
        width: 156,
        decoration: BoxDecoration(
          color: menuBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: menuBorder, width: 1),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF0A0F20)
                  .withValues(alpha: isDark ? 0.45 : 0.12),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        padding: const EdgeInsets.all(5),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: _models.map((m) {
            final id = m['id']!;
            final label = m['label']!;
            final isSelected = _selectedModel == id && _thinkingEnabled;
            return _MinimalMenuTile(
              isSelected: isSelected,
              palette: widget.palette,
              onTap: () {
                setState(() {
                  _selectedModel = id;
                  _thinkingEnabled = true;
                });
                widget.onThinkingTierChanged?.call(id);
                widget.onThinkingEnabledChanged?.call(true);
                _closeModelMenu();
              },
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      label,
                      style: UnoTypography.body(
                        color: isSelected
                            ? widget.palette.text
                            : widget.palette.textSec,
                        fontSize: 13,
                        fontWeight:
                            isSelected ? FontWeight.w600 : FontWeight.w400,
                      ),
                    ),
                  ),
                  if (isSelected)
                    Icon(
                      LucideIcons.check,
                      size: 13.5,
                      color: widget.palette.accent,
                    ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  // --- Plus Menu Overlay ---
  void _togglePlusMenu() {
    if (_plusMenuOverlay != null) {
      _closePlusMenu();
    } else {
      _closeModelMenu(animated: false);
      _openPlusMenu();
    }
  }

  void _openPlusMenu() {
    _closePlusMenu(animated: false);
    final overlay = Overlay.of(context);
    _plusMenuOverlay = OverlayEntry(
      builder: (context) {
        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () => _closePlusMenu(),
                child: const SizedBox.expand(),
              ),
            ),
            CompositedTransformFollower(
              link: _plusButtonLink,
              showWhenUnlinked: false,
              targetAnchor: Alignment.topLeft,
              followerAnchor: Alignment.bottomLeft,
              offset: const Offset(0, -8),
              child: Material(
                color: Colors.transparent,
                child: _buildPlusMenuCard(),
              ),
            ),
          ],
        );
      },
    );
    overlay.insert(_plusMenuOverlay!);
    _plusAnim.forward(from: 0.0);
    setState(() {});
  }

  Future<void> _closePlusMenu({bool animated = true}) async {
    if (_plusMenuOverlay == null) return;
    if (animated) {
      await _plusAnim.reverse();
    }
    _plusMenuOverlay?.remove();
    _plusMenuOverlay = null;
    if (mounted) setState(() {});
  }

  Widget _buildPlusMenuCard() {
    final isDark = widget.palette.isDark;
    final menuBg = isDark ? widget.palette.bgElevated : const Color(0xFFFFFFFF);
    final menuBorder = widget.palette.div;

    return AnimatedBuilder(
      animation: _plusAnim,
      builder: (context, child) {
        return FadeTransition(
          opacity: _plusFade,
          child: SlideTransition(
            position: _plusSlide,
            child: ScaleTransition(
              scale: _plusScale,
              alignment: Alignment.bottomLeft,
              child: child,
            ),
          ),
        );
      },
      child: Container(
        width: 192,
        decoration: BoxDecoration(
          color: menuBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: menuBorder, width: 1),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF0A0F20)
                  .withValues(alpha: isDark ? 0.45 : 0.12),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        padding: const EdgeInsets.all(5),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildPlusMenuItem(
              icon: LucideIcons.folderPlus,
              title: 'Add to project',
              isActive: false,
              onTap: () {
                _closePlusMenu();
                _handlePickFiles();
              },
            ),
            _buildPlusMenuItem(
              icon: LucideIcons.globe,
              title: 'Web search',
              isActive: _activeSearchMode == 'web',
              onTap: () {
                setState(() {
                  _activeSearchMode =
                      _activeSearchMode == 'web' ? null : 'web';
                });
                _closePlusMenu();
              },
            ),
            _buildPlusMenuItem(
              icon: LucideIcons.bookOpen,
              title: 'Deep research',
              isActive: _activeSearchMode == 'research',
              onTap: () {
                setState(() {
                  _activeSearchMode =
                      _activeSearchMode == 'research' ? null : 'research';
                });
                _closePlusMenu();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlusMenuItem({
    required IconData icon,
    required String title,
    required bool isActive,
    required VoidCallback onTap,
  }) {
    return _MinimalMenuTile(
      isSelected: isActive,
      palette: widget.palette,
      onTap: onTap,
      child: Row(
        children: [
          Icon(
            icon,
            size: 14.5,
            color: isActive ? widget.palette.accent : widget.palette.textSec,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: UnoTypography.body(
                color: isActive ? widget.palette.text : widget.palette.textSec,
                fontSize: 13,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
          if (isActive)
            Icon(LucideIcons.check, size: 13.5, color: widget.palette.accent),
        ],
      ),
    );
  }

  void _handleSubmit() {
    if (widget.controller.text.trim().isEmpty) return;
    _closeModelMenu(animated: false);
    _closePlusMenu(animated: false);
    widget.onSubmit();
    setState(() {
      _showSuggestions = false;
      _attachedFileNames.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final canSubmit = widget.controller.text.trim().isNotEmpty;
    final isFocused = _focusNode.hasFocus;
    final isDark = widget.palette.isDark;
    final p = widget.palette;

    // Zero-alpha matched base color to prevent muddy grey lerp artifacts
    final accentBase = p.accent;
    final composerBg = isDark ? const Color(0xFF151D30) : const Color(0xFFFFFFFF);
    final controlPillBg = isDark ? const Color(0xFF1C2438) : const Color(0xFFF4EFE7);
    final sendBg = canSubmit
        ? (_sendBtnHovered
            ? Color.lerp(p.accent, isDark ? Colors.white : const Color(0xFF1E263D), 0.14)!
            : p.accent)
        : p.accent.withValues(alpha: isDark ? 0.55 : 0.45);
    final sendIconColor =
        isDark ? const Color(0xFF0B1020) : const Color(0xFFF4F1EC);

    return CompositedTransformTarget(
      link: _layerLink,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Active Search Mode Badge (if any)
          if (_activeSearchMode != null) ...[
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: p.accent.withValues(alpha: 0.12),
                border: Border.all(
                  color: p.accent.withValues(alpha: 0.34),
                  width: 1,
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
                    size: 12,
                    color: p.accent,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _activeSearchMode == 'research'
                        ? 'Deep Research Active'
                        : 'Web Search Active',
                    style: UnoTypography.body(
                      color: p.accent,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 6),
                  InkWell(
                    onTap: () => setState(() => _activeSearchMode = null),
                    borderRadius: BorderRadius.circular(10),
                    child: Padding(
                      padding: const EdgeInsets.all(2),
                      child: Icon(
                        LucideIcons.x,
                        size: 12,
                        color: p.accent,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Main Integrated Composer Surface
          MouseRegion(
            onEnter: (_) => setState(() => _isCardHovered = true),
            onExit: (_) => setState(() => _isCardHovered = false),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOutCubic,
              decoration: BoxDecoration(
                color: composerBg,
                border: Border.all(
                  color: isFocused
                      ? accentBase.withValues(alpha: isDark ? 0.38 : 0.34)
                      : (_isCardHovered
                          ? accentBase.withValues(alpha: isDark ? 0.22 : 0.20)
                          : p.div.withValues(alpha: 0.9)),
                  width: 1.0,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF050814).withValues(
                      alpha: isDark
                          ? (isFocused ? 0.34 : 0.24)
                          : (isFocused ? 0.09 : 0.05),
                    ),
                    blurRadius: isFocused ? 18 : 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              padding: const EdgeInsets.fromLTRB(16, 13, 12, 11),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Text input with Enter submission and Shift+Enter for newline
                  Focus(
                    onKeyEvent: (node, event) {
                      if (event is KeyDownEvent) {
                        final isEnter = event.logicalKey ==
                                LogicalKeyboardKey.enter ||
                            event.logicalKey == LogicalKeyboardKey.numpadEnter;
                        if (isEnter) {
                          if (HardwareKeyboard.instance.isShiftPressed) {
                            return KeyEventResult.ignored;
                          } else {
                            if (canSubmit) {
                              _handleSubmit();
                            }
                            return KeyEventResult.handled;
                          }
                        }
                      }
                      return KeyEventResult.ignored;
                    },
                    child: TextField(
                      focusNode: _focusNode,
                      controller: widget.controller,
                      maxLines: 5,
                      minLines: 1,
                      textInputAction: TextInputAction.send,
                      style: UnoTypography.body(
                        color: p.text,
                        fontSize: 15,
                        height: 1.5,
                      ),
                      decoration: InputDecoration(
                        hintText: widget.placeholder ??
                            'Ask about a merge, a ticket, or a decision on your project…',
                        hintStyle: UnoTypography.body(
                          color: p.textMuted,
                          fontSize: 15,
                        ),
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding:
                            const EdgeInsets.symmetric(vertical: 4),
                      ),
                      onSubmitted: (_) {
                        if (canSubmit) {
                          _handleSubmit();
                        }
                      },
                    ),
                  ),

                  // Animated Attached Files Chips
                  AnimatedSize(
                    duration: const Duration(milliseconds: 220),
                    curve: Curves.easeOutCubic,
                    child: _attachedFileNames.isNotEmpty
                        ? Padding(
                            padding: const EdgeInsets.only(top: 8, bottom: 2),
                            child: Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: _attachedFileNames.map((name) {
                                return AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: p.accent.withValues(alpha: 0.10),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: p.accent.withValues(alpha: 0.28),
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(LucideIcons.paperclip,
                                          size: 12, color: p.accent),
                                      const SizedBox(width: 5),
                                      ConstrainedBox(
                                        constraints:
                                            const BoxConstraints(maxWidth: 180),
                                        child: Text(
                                          name,
                                          style: UnoTypography.mono(
                                            fontSize: 11,
                                            color: p.text,
                                          ),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      const SizedBox(width: 5),
                                      InkWell(
                                        onTap: () => setState(() =>
                                            _attachedFileNames.remove(name)),
                                        borderRadius: BorderRadius.circular(4),
                                        child: Padding(
                                          padding: const EdgeInsets.all(2),
                                          child: Icon(
                                            LucideIcons.x,
                                            size: 12,
                                            color: p.textSec,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }).toList(),
                            ),
                          )
                        : const SizedBox.shrink(),
                  ),

                  const SizedBox(height: 12),

                  // Clean Bottom Toolbar (no inner divider line)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Left controls: Plus, Attach, Thinking Toggle, Model Selector
                      Row(
                        children: [
                          // Plus Button (quiet icon button, understated hover)
                          CompositedTransformTarget(
                            link: _plusButtonLink,
                            child: MouseRegion(
                              cursor: SystemMouseCursors.click,
                              onEnter: (_) =>
                                  setState(() => _plusBtnHovered = true),
                              onExit: (_) =>
                                  setState(() => _plusBtnHovered = false),
                              child: Tooltip(
                                message: 'Add context',
                                child: GestureDetector(
                                  onTap: _togglePlusMenu,
                                  behavior: HitTestBehavior.opaque,
                                  child: AnimatedContainer(
                                    duration: const Duration(milliseconds: 160),
                                    curve: Curves.easeOutCubic,
                                    width: 32,
                                    height: 32,
                                    decoration: BoxDecoration(
                                      color: accentBase.withValues(
                                        alpha: (_plusMenuOverlay != null ||
                                                _plusBtnHovered)
                                            ? 0.08
                                            : 0.0,
                                      ),
                                      borderRadius: BorderRadius.circular(9),
                                    ),
                                    child: Center(
                                      child: RotationTransition(
                                        turns: _plusRotate,
                                        child: Icon(
                                          LucideIcons.plus,
                                          size: 16,
                                          color: _plusMenuOverlay != null ||
                                                  _plusBtnHovered
                                              ? p.accent
                                              : p.textSec,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),

                          // Paperclip attach button (quiet icon button)
                          MouseRegion(
                            cursor: SystemMouseCursors.click,
                            onEnter: (_) =>
                                setState(() => _attachBtnHovered = true),
                            onExit: (_) =>
                                setState(() => _attachBtnHovered = false),
                            child: Tooltip(
                              message: 'Attach files',
                              child: GestureDetector(
                                onTap: _handlePickFiles,
                                behavior: HitTestBehavior.opaque,
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 160),
                                  curve: Curves.easeOutCubic,
                                  width: 32,
                                  height: 32,
                                  decoration: BoxDecoration(
                                    color: accentBase.withValues(
                                      alpha: _attachBtnHovered ? 0.08 : 0.0,
                                    ),
                                    borderRadius: BorderRadius.circular(9),
                                  ),
                                  child: Center(
                                    child: Icon(
                                      LucideIcons.paperclip,
                                      size: 15,
                                      color: _attachBtnHovered
                                          ? p.accent
                                          : p.textSec,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),

                          // Thinking Toggle Pill
                          MouseRegion(
                            cursor: SystemMouseCursors.click,
                            onEnter: (_) =>
                                setState(() => _thinkingToggleHovered = true),
                            onExit: (_) =>
                                setState(() => _thinkingToggleHovered = false),
                            child: Tooltip(
                              message: _thinkingEnabled
                                  ? 'Deep reasoning enabled (click to disable)'
                                  : 'Fast mode (click to enable deep reasoning)',
                              child: GestureDetector(
                                onTap: () {
                                  final next = !_thinkingEnabled;
                                  setState(() => _thinkingEnabled = next);
                                  widget.onThinkingEnabledChanged?.call(next);
                                },
                                behavior: HitTestBehavior.opaque,
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  curve: Curves.easeOutCubic,
                                  height: 32,
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10),
                                  decoration: BoxDecoration(
                                    color: _thinkingToggleHovered
                                        ? p.bgInteractive
                                        : controlPillBg,
                                    border: Border.all(
                                      color: _thinkingEnabled
                                          ? accentBase.withValues(
                                              alpha: isDark ? 0.30 : 0.28)
                                          : (_thinkingToggleHovered
                                              ? accentBase.withValues(
                                                  alpha: 0.22)
                                              : p.div.withValues(alpha: 0.85)),
                                      width: 1,
                                    ),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        LucideIcons.brain,
                                        size: 13.5,
                                        color: _thinkingEnabled
                                            ? p.accent
                                            : (_thinkingToggleHovered
                                                ? p.text
                                                : p.textSec),
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        'Thinking',
                                        style: UnoTypography.body(
                                          color: _thinkingEnabled
                                              ? p.text
                                              : (_thinkingToggleHovered
                                                  ? p.text
                                                  : p.textSec),
                                          fontSize: 12.5,
                                          fontWeight: _thinkingEnabled
                                              ? FontWeight.w500
                                              : FontWeight.w400,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      AnimatedContainer(
                                        duration:
                                            const Duration(milliseconds: 180),
                                        curve: Curves.easeOutCubic,
                                        width: 24,
                                        height: 14,
                                        padding: const EdgeInsets.all(2),
                                        decoration: BoxDecoration(
                                          borderRadius:
                                              BorderRadius.circular(7),
                                          color: _thinkingEnabled
                                              ? p.accent
                                              : p.div,
                                        ),
                                        child: AnimatedAlign(
                                          duration:
                                              const Duration(milliseconds: 180),
                                          curve: Curves.easeOutCubic,
                                          alignment: _thinkingEnabled
                                              ? Alignment.centerRight
                                              : Alignment.centerLeft,
                                          child: Container(
                                            width: 10,
                                            height: 10,
                                            decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              color: _thinkingEnabled
                                                  ? (isDark
                                                      ? const Color(0xFF0B1020)
                                                      : Colors.white)
                                                  : p.bgElevated,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),

                          // Minimal Model Dropdown Pill
                          CompositedTransformTarget(
                            link: _modelButtonLink,
                            child: MouseRegion(
                              cursor: SystemMouseCursors.click,
                              onEnter: (_) =>
                                  setState(() => _modelBtnHovered = true),
                              onExit: (_) =>
                                  setState(() => _modelBtnHovered = false),
                              child: Tooltip(
                                message: 'Select model',
                                child: GestureDetector(
                                  onTap: _toggleModelMenu,
                                  behavior: HitTestBehavior.opaque,
                                  child: AnimatedContainer(
                                    duration:
                                        const Duration(milliseconds: 160),
                                    curve: Curves.easeOutCubic,
                                    height: 32,
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 11),
                                    decoration: BoxDecoration(
                                      color: (_modelBtnHovered ||
                                              _modelMenuOverlay != null)
                                          ? p.bgInteractive
                                          : controlPillBg,
                                      border: Border.all(
                                        color: (_modelBtnHovered ||
                                                _modelMenuOverlay != null)
                                            ? accentBase.withValues(alpha: 0.30)
                                            : p.div.withValues(alpha: 0.85),
                                        width: 1,
                                      ),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Text(
                                          _thinkingEnabled
                                              ? _selectedModelLabel
                                              : 'Fast',
                                          style: UnoTypography.body(
                                            color: _thinkingEnabled
                                                ? p.text
                                                : p.textSec,
                                            fontSize: 12.5,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        AnimatedRotation(
                                          turns: _modelMenuOverlay != null
                                              ? 0.5
                                              : 0.0,
                                          duration: const Duration(
                                              milliseconds: 180),
                                          curve: Curves.easeOutCubic,
                                          child: Icon(
                                            LucideIcons.chevronDown,
                                            size: 12.5,
                                            color: p.textSec,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),

                      // Right toolbar: Warm Ivory Rounded-Square Primary Send Button
                      MouseRegion(
                        cursor: canSubmit
                            ? SystemMouseCursors.click
                            : SystemMouseCursors.basic,
                        onEnter: (_) => setState(() => _sendBtnHovered = true),
                        onExit: (_) => setState(() => _sendBtnHovered = false),
                        child: AnimatedScale(
                          scale: canSubmit && _sendBtnHovered ? 1.05 : 1.0,
                          duration: const Duration(milliseconds: 150),
                          curve: Curves.easeOutCubic,
                          child: GestureDetector(
                            onTap: canSubmit ? _handleSubmit : null,
                            behavior: HitTestBehavior.opaque,
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              curve: Curves.easeOutCubic,
                              width: 34,
                              height: 34,
                              decoration: BoxDecoration(
                                color: sendBg,
                                borderRadius: BorderRadius.circular(10),
                                boxShadow: canSubmit
                                    ? [
                                        BoxShadow(
                                          color: const Color(0xFF050814)
                                              .withValues(
                                                  alpha: isDark ? 0.30 : 0.14),
                                          blurRadius: 8,
                                          offset: const Offset(0, 2),
                                        ),
                                      ]
                                    : const [],
                              ),
                              child: Center(
                                child: Icon(
                                  LucideIcons.arrowUp,
                                  size: 16,
                                  color: sendIconColor,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Autocomplete suggestions popup
          if (_showSuggestions) ...[
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.only(top: 8),
              decoration: BoxDecoration(
                color: p.bgElevated,
                border: Border.all(color: p.div),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.18),
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
                                color: p.textSec,
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

class _MinimalMenuTile extends StatefulWidget {
  final bool isSelected;
  final UnoPalette palette;
  final VoidCallback onTap;
  final Widget child;

  const _MinimalMenuTile({
    required this.isSelected,
    required this.palette,
    required this.onTap,
    required this.child,
  });

  @override
  State<_MinimalMenuTile> createState() => _MinimalMenuTileState();
}

class _MinimalMenuTileState extends State<_MinimalMenuTile> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.palette.isDark;
    final hoverBase =
        isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    final bgColor = widget.isSelected
        ? hoverBase.withValues(alpha: isDark ? 0.08 : 0.06)
        : hoverBase.withValues(alpha: _isHovered ? 0.05 : 0.0);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          curve: Curves.easeOutCubic,
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          child: widget.child,
        ),
      ),
    );
  }
}
