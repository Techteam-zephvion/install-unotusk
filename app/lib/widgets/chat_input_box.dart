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

class _ChatInputBoxState extends State<ChatInputBox>
    with TickerProviderStateMixin {
  bool _thinkingEnabled = true;
  String _thinkingMode = 'warm'; // warm, cold, hot
  String? _activeSearchMode; // research, web, project
  bool _showSuggestions = false;
  final List<String> _attachedFileNames = [];

  final FocusNode _focusNode = FocusNode();
  bool _isCardHovered = false;
  bool _sendBtnHovered = false;
  bool _plusBtnHovered = false;
  bool _attachBtnHovered = false;
  bool _thinkingToggleHovered = false;
  bool _tierBtnHovered = false;

  // Thinking Dropdown Animation & Overlay
  late final AnimationController _thinkingAnim;
  late final Animation<double> _thinkingFade;
  late final Animation<double> _thinkingScale;
  late final Animation<Offset> _thinkingSlide;
  OverlayEntry? _thinkingMenuOverlay;

  // Plus Menu Animation & Overlay
  late final AnimationController _plusAnim;
  late final Animation<double> _plusFade;
  late final Animation<double> _plusScale;
  late final Animation<Offset> _plusSlide;
  late final Animation<double> _plusRotate;
  OverlayEntry? _plusMenuOverlay;

  final LayerLink _layerLink = LayerLink();
  final LayerLink _thinkingButtonLink = LayerLink();
  final LayerLink _plusButtonLink = LayerLink();

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
    _focusNode.addListener(_onFocusChanged);

    // Thinking Menu Animations
    _thinkingAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
      reverseDuration: const Duration(milliseconds: 160),
    );
    _thinkingFade = CurvedAnimation(
      parent: _thinkingAnim,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    _thinkingScale = Tween<double>(begin: 0.94, end: 1.0).animate(
      CurvedAnimation(
        parent: _thinkingAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );
    _thinkingSlide = Tween<Offset>(
      begin: const Offset(0, 0.05),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _thinkingAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );

    // Plus Menu Animations
    _plusAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
      reverseDuration: const Duration(milliseconds: 150),
    );
    _plusFade = CurvedAnimation(
      parent: _plusAnim,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    _plusScale = Tween<double>(begin: 0.93, end: 1.0).animate(
      CurvedAnimation(
        parent: _plusAnim,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      ),
    );
    _plusSlide = Tween<Offset>(
      begin: const Offset(0, 0.06),
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
  void dispose() {
    _closeThinkingMenu(animated: false);
    _closePlusMenu(animated: false);
    _thinkingAnim.dispose();
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

  // --- Thinking Menu Overlay ---
  void _toggleThinkingMenu() {
    if (_thinkingMenuOverlay != null) {
      _closeThinkingMenu();
    } else {
      _closePlusMenu(animated: false);
      _openThinkingMenu();
    }
  }

  void _openThinkingMenu() {
    _closeThinkingMenu(animated: false);
    final overlay = Overlay.of(context);
    _thinkingMenuOverlay = OverlayEntry(
      builder: (context) {
        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () => _closeThinkingMenu(),
                child: const SizedBox.expand(),
              ),
            ),
            CompositedTransformFollower(
              link: _thinkingButtonLink,
              showWhenUnlinked: false,
              targetAnchor: Alignment.topLeft,
              followerAnchor: Alignment.bottomLeft,
              offset: const Offset(0, -10),
              child: Material(
                color: Colors.transparent,
                child: _buildThinkingMenuCard(),
              ),
            ),
          ],
        );
      },
    );
    overlay.insert(_thinkingMenuOverlay!);
    _thinkingAnim.forward(from: 0.0);
    setState(() {});
  }

  Future<void> _closeThinkingMenu({bool animated = true}) async {
    if (_thinkingMenuOverlay == null) return;
    if (animated) {
      await _thinkingAnim.reverse();
    }
    _thinkingMenuOverlay?.remove();
    _thinkingMenuOverlay = null;
    if (mounted) setState(() {});
  }

  Widget _buildThinkingMenuCard() {
    return AnimatedBuilder(
      animation: _thinkingAnim,
      builder: (context, child) {
        return FadeTransition(
          opacity: _thinkingFade,
          child: SlideTransition(
            position: _thinkingSlide,
            child: ScaleTransition(
              scale: _thinkingScale,
              alignment: Alignment.bottomLeft,
              child: child,
            ),
          ),
        );
      },
      child: Container(
        width: 230,
        decoration: BoxDecoration(
          color: widget.palette.bgElevated,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: widget.palette.div,
            width: 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.45),
              blurRadius: 28,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        padding: const EdgeInsets.all(8),
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
                child: Row(
                  children: [
                    Icon(LucideIcons.cpu, size: 12, color: widget.palette.accent),
                    const SizedBox(width: 6),
                    Text(
                      'REASONING MODEL',
                      style: UnoTypography.mono(
                        color: widget.palette.textSec,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
              ),
              _buildTierOption(
                tier: 'hot',
                title: 'Hot',
                subtitle: 'Quick answers · Lowest latency',
              ),
              const SizedBox(height: 3),
              _buildTierOption(
                tier: 'warm',
                title: 'Warm',
                subtitle: 'Balanced · Standard depth',
              ),
              const SizedBox(height: 3),
              _buildTierOption(
                tier: 'cold',
                title: 'Cold',
                subtitle: 'Deep reasoning · Maximum facts',
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTierOption({
    required String tier,
    required String title,
    required String subtitle,
  }) {
    final isSelected = _thinkingMode == tier && _thinkingEnabled;

    return _HoverableTile(
      isSelected: isSelected,
      selectedBgColor: widget.palette.bgSurface,
      accentColor: widget.palette.accent,
      palette: widget.palette,
      onTap: () {
        setState(() {
          _thinkingMode = tier;
          _thinkingEnabled = true;
        });
        _closeThinkingMenu();
      },
      child: Row(
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              color: isSelected
                  ? widget.palette.accent
                  : widget.palette.textSec.withValues(alpha: 0.35),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: UnoTypography.body(
                    color: isSelected
                        ? widget.palette.text
                        : widget.palette.text.withValues(alpha: 0.9),
                    fontSize: 13,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  ),
                ),
                Text(
                  subtitle,
                  style: UnoTypography.body(
                    color: widget.palette.textSec,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          if (isSelected)
            Icon(LucideIcons.check, size: 14, color: widget.palette.accent),
        ],
      ),
    );
  }

  // --- Plus Menu Overlay ---
  void _togglePlusMenu() {
    if (_plusMenuOverlay != null) {
      _closePlusMenu();
    } else {
      _closeThinkingMenu(animated: false);
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
              offset: const Offset(0, -10),
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
        width: 200,
        decoration: BoxDecoration(
          color: widget.palette.bgElevated,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: widget.palette.div, width: 1.2),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.45),
              blurRadius: 28,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        padding: const EdgeInsets.all(8),
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
            _buildPlusMenuItem(
              icon: LucideIcons.folderPlus,
              title: 'Add to project',
              subtitle: 'Link external repo folder',
              isActive: false,
              onTap: () {
                _closePlusMenu();
                _handlePickFiles();
              },
            ),
            const SizedBox(height: 3),
            _buildPlusMenuItem(
              icon: LucideIcons.globe,
              title: 'Web search',
              subtitle: 'Ground with internet search',
              isActive: _activeSearchMode == 'web',
              onTap: () {
                setState(() {
                  _activeSearchMode =
                      _activeSearchMode == 'web' ? null : 'web';
                });
                _closePlusMenu();
              },
            ),
            const SizedBox(height: 3),
            _buildPlusMenuItem(
              icon: LucideIcons.bookOpen,
              title: 'Deep research',
              subtitle: 'Multi-signal code graph probe',
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
      ),
    );
  }

  Widget _buildPlusMenuItem({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool isActive,
    required VoidCallback onTap,
  }) {
    return _HoverableTile(
      isSelected: isActive,
      selectedBgColor: widget.palette.accent.withValues(alpha: 0.15),
      accentColor: widget.palette.accent,
      palette: widget.palette,
      onTap: onTap,
      child: Row(
        children: [
          Icon(
            icon,
            size: 15,
            color: isActive ? widget.palette.accent : widget.palette.textSec,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: UnoTypography.body(
                    color: isActive ? widget.palette.accent : widget.palette.text,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  subtitle,
                  style: UnoTypography.body(
                    color: widget.palette.textSec,
                    fontSize: 10.5,
                  ),
                ),
              ],
            ),
          ),
          if (isActive)
            Icon(LucideIcons.check, size: 13, color: widget.palette.accent),
        ],
      ),
    );
  }

  void _handleSubmit() {
    if (widget.controller.text.trim().isEmpty) return;
    _closeThinkingMenu(animated: false);
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
                color: widget.palette.accent.withValues(alpha: 0.14),
                border: Border.all(
                  color: widget.palette.accent.withValues(alpha: 0.4),
                  width: 1.2,
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
                    color: widget.palette.accent,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _activeSearchMode == 'research'
                        ? 'Deep Research Active'
                        : 'Web Search Active',
                    style: UnoTypography.body(
                      color: widget.palette.accent,
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
                        color: widget.palette.accent,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Main Card with Smooth Animated Container Focus & Hover States
          MouseRegion(
            onEnter: (_) => setState(() => _isCardHovered = true),
            onExit: (_) => setState(() => _isCardHovered = false),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOutCubic,
              decoration: BoxDecoration(
                color: widget.palette.bgElevated,
                border: Border.all(
                  color: isFocused
                      ? widget.palette.accent.withValues(alpha: 0.7)
                      : (_isCardHovered
                          ? widget.palette.accent.withValues(alpha: 0.35)
                          : widget.palette.div),
                  width: isFocused ? 1.4 : 1.0,
                ),
                borderRadius: BorderRadius.circular(22),
                boxShadow: [
                  BoxShadow(
                    color: isFocused
                        ? widget.palette.accent.withValues(alpha: 0.08)
                        : Colors.black.withValues(alpha: 0.06),
                    blurRadius: isFocused ? 32 : 24,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              padding: const EdgeInsets.fromLTRB(16, 14, 14, 10),
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
                        color: widget.palette.text,
                        fontSize: 15,
                        height: 1.45,
                      ),
                      decoration: InputDecoration(
                        hintText: widget.placeholder ??
                            'Ask about a merge, a ticket, or a decision on your project…',
                        hintStyle: UnoTypography.body(
                          color: widget.palette.textSec.withValues(alpha: 0.8),
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
                            padding: const EdgeInsets.only(top: 8, bottom: 4),
                            child: Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: _attachedFileNames.map((name) {
                                return AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: widget.palette.accent
                                        .withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: widget.palette.accent
                                          .withValues(alpha: 0.35),
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(LucideIcons.paperclip,
                                          size: 12,
                                          color: widget.palette.accent),
                                      const SizedBox(width: 5),
                                      ConstrainedBox(
                                        constraints:
                                            const BoxConstraints(maxWidth: 180),
                                        child: Text(
                                          name,
                                          style: UnoTypography.mono(
                                            fontSize: 11,
                                            color: widget.palette.text,
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
                                            color: widget.palette.textSec,
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

                  const SizedBox(height: 10),
                  Divider(
                    height: 1,
                    thickness: 1,
                    color: widget.palette.div.withValues(alpha: 0.55),
                  ),
                  const SizedBox(height: 8),

                  // Bottom toolbar inside card
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Left controls: Plus, Attach, Thinking Toggle, Model Dropdown
                      Row(
                        children: [
                          // Plus Button with Smooth Rotate and Animated Dropdown
                          CompositedTransformTarget(
                            link: _plusButtonLink,
                            child: MouseRegion(
                              onEnter: (_) =>
                                  setState(() => _plusBtnHovered = true),
                              onExit: (_) =>
                                  setState(() => _plusBtnHovered = false),
                              child: Tooltip(
                                message: 'Add external context or search mode',
                                child: InkWell(
                                  onTap: _togglePlusMenu,
                                  borderRadius: BorderRadius.circular(10),
                                  child: AnimatedContainer(
                                    duration: const Duration(milliseconds: 180),
                                    width: 32,
                                    height: 32,
                                    decoration: BoxDecoration(
                                      color: _plusMenuOverlay != null ||
                                              _plusBtnHovered
                                          ? widget.palette.accent
                                              .withValues(alpha: 0.12)
                                          : Colors.transparent,
                                      border: Border.all(
                                        color: _plusMenuOverlay != null ||
                                                _plusBtnHovered
                                            ? widget.palette.accent
                                                .withValues(alpha: 0.4)
                                            : widget.palette.div,
                                        width: 1.1,
                                      ),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Center(
                                      child: RotationTransition(
                                        turns: _plusRotate,
                                        child: Icon(
                                          LucideIcons.plus,
                                          size: 15,
                                          color: _plusMenuOverlay != null ||
                                                  _plusBtnHovered
                                              ? widget.palette.accent
                                              : widget.palette.textSec,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),

                          // Paperclip attach button
                          MouseRegion(
                            onEnter: (_) =>
                                setState(() => _attachBtnHovered = true),
                            onExit: (_) =>
                                setState(() => _attachBtnHovered = false),
                            child: Tooltip(
                              message: 'Attach files or context',
                              child: InkWell(
                                onTap: _handlePickFiles,
                                borderRadius: BorderRadius.circular(10),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  width: 32,
                                  height: 32,
                                  decoration: BoxDecoration(
                                    color: _attachBtnHovered
                                        ? widget.palette.accent
                                            .withValues(alpha: 0.12)
                                        : Colors.transparent,
                                    border: Border.all(
                                      color: _attachBtnHovered
                                          ? widget.palette.accent
                                              .withValues(alpha: 0.4)
                                          : widget.palette.div,
                                      width: 1.1,
                                    ),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Center(
                                    child: Icon(
                                      LucideIcons.paperclip,
                                      size: 14,
                                      color: _attachBtnHovered
                                          ? widget.palette.accent
                                          : widget.palette.textSec,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),

                          // Thinking Toggle Button (Placed NEXT to the dropdown menu)
                          MouseRegion(
                            onEnter: (_) =>
                                setState(() => _thinkingToggleHovered = true),
                            onExit: (_) =>
                                setState(() => _thinkingToggleHovered = false),
                            child: Tooltip(
                              message: _thinkingEnabled
                                  ? 'Deep thinking is ON (Click to toggle)'
                                  : 'Deep thinking is OFF (Click to toggle)',
                              child: InkWell(
                                onTap: () {
                                  setState(() {
                                    _thinkingEnabled = !_thinkingEnabled;
                                  });
                                },
                                borderRadius: BorderRadius.circular(20),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 200),
                                  height: 32,
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10),
                                  decoration: BoxDecoration(
                                    color: _thinkingEnabled
                                        ? widget.palette.bgSurface
                                        : (_thinkingToggleHovered
                                            ? widget.palette.bgElevated
                                            : Colors.transparent),
                                    border: Border.all(
                                      color: _thinkingEnabled
                                          ? widget.palette.accent
                                              .withValues(alpha: 0.5)
                                          : (_thinkingToggleHovered
                                              ? widget.palette.textSec
                                                  .withValues(alpha: 0.4)
                                              : widget.palette.div),
                                      width: 1.1,
                                    ),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        LucideIcons.brain,
                                        size: 13,
                                        color: _thinkingEnabled
                                            ? widget.palette.accent
                                            : widget.palette.textSec,
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        'Thinking',
                                        style: UnoTypography.body(
                                          color: _thinkingEnabled
                                              ? widget.palette.text
                                              : widget.palette.textSec,
                                          fontSize: 12,
                                          fontWeight: _thinkingEnabled
                                              ? FontWeight.w600
                                              : FontWeight.w400,
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                      // Micro-pill switch indicator
                                      AnimatedContainer(
                                        duration:
                                            const Duration(milliseconds: 200),
                                        width: 24,
                                        height: 14,
                                        padding: const EdgeInsets.all(2),
                                        decoration: BoxDecoration(
                                          borderRadius:
                                              BorderRadius.circular(7),
                                          color: _thinkingEnabled
                                              ? widget.palette.accent
                                              : widget.palette.div,
                                        ),
                                        child: Align(
                                          alignment: _thinkingEnabled
                                              ? Alignment.centerRight
                                              : Alignment.centerLeft,
                                          child: Container(
                                            width: 10,
                                            height: 10,
                                            decoration: const BoxDecoration(
                                              shape: BoxShape.circle,
                                              color: Colors.white,
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

                          // Model / Tier Dropdown Capsule
                          CompositedTransformTarget(
                            link: _thinkingButtonLink,
                            child: MouseRegion(
                              onEnter: (_) =>
                                  setState(() => _tierBtnHovered = true),
                              onExit: (_) =>
                                  setState(() => _tierBtnHovered = false),
                              child: Tooltip(
                                message: 'Select reasoning model tier',
                                child: InkWell(
                                  onTap: _toggleThinkingMenu,
                                  borderRadius: BorderRadius.circular(20),
                                  child: AnimatedContainer(
                                    duration:
                                        const Duration(milliseconds: 200),
                                    height: 32,
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 11),
                                    decoration: BoxDecoration(
                                      color: _tierBtnHovered ||
                                              _thinkingMenuOverlay != null
                                          ? widget.palette.bgElevated
                                          : widget.palette.bgSurface,
                                      border: Border.all(
                                        color: _tierBtnHovered ||
                                                _thinkingMenuOverlay != null
                                            ? widget.palette.textSec
                                                .withValues(alpha: 0.45)
                                            : widget.palette.div,
                                        width: 1.1,
                                      ),
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(
                                          LucideIcons.sparkles,
                                          size: 12,
                                          color: widget.palette.textSec,
                                        ),
                                        const SizedBox(width: 6),
                                        Text(
                                          '${_thinkingMode[0].toUpperCase()}${_thinkingMode.substring(1)} tier',
                                          style: UnoTypography.body(
                                            color: widget.palette.text,
                                            fontSize: 12,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                        const SizedBox(width: 5),
                                        AnimatedRotation(
                                          turns:
                                              _thinkingMenuOverlay != null
                                                  ? 0.5
                                                  : 0.0,
                                          duration: const Duration(
                                              milliseconds: 200),
                                          child: Icon(
                                            LucideIcons.chevronDown,
                                            size: 12,
                                            color: widget.palette.textSec,
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

                      // Right toolbar: Mic button is removed, only smooth send button
                      MouseRegion(
                        onEnter: (_) => setState(() => _sendBtnHovered = true),
                        onExit: (_) => setState(() => _sendBtnHovered = false),
                        child: AnimatedScale(
                          scale: canSubmit && _sendBtnHovered
                              ? 1.08
                              : (canSubmit ? 1.0 : 0.92),
                          duration: const Duration(milliseconds: 180),
                          child: InkWell(
                            onTap: canSubmit ? _handleSubmit : null,
                            borderRadius: BorderRadius.circular(17),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              width: 34,
                              height: 34,
                              decoration: BoxDecoration(
                                color: canSubmit
                                    ? widget.palette.accent
                                    : widget.palette.div.withValues(alpha: 0.45),
                                shape: BoxShape.circle,
                                boxShadow: canSubmit
                                    ? [
                                        BoxShadow(
                                          color: widget.palette.accent
                                              .withValues(alpha: 0.4),
                                          blurRadius: 12,
                                          offset: const Offset(0, 3),
                                        ),
                                      ]
                                    : null,
                              ),
                              child: Center(
                                child: Icon(
                                  LucideIcons.arrowUp,
                                  size: 15,
                                  color: canSubmit
                                      ? Colors.white
                                      : widget.palette.textSec
                                          .withValues(alpha: 0.6),
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
                color: widget.palette.bgElevated,
                border: Border.all(color: widget.palette.div),
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

class _HoverableTile extends StatefulWidget {
  final bool isSelected;
  final Color selectedBgColor;
  final Color accentColor;
  final UnoPalette palette;
  final VoidCallback onTap;
  final Widget child;

  const _HoverableTile({
    required this.isSelected,
    required this.selectedBgColor,
    required this.accentColor,
    required this.palette,
    required this.onTap,
    required this.child,
  });

  @override
  State<_HoverableTile> createState() => _HoverableTileState();
}

class _HoverableTileState extends State<_HoverableTile> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(10),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          decoration: BoxDecoration(
            color: widget.isSelected
                ? widget.selectedBgColor
                : (_isHovered
                    ? widget.palette.accent.withValues(alpha: 0.08)
                    : Colors.transparent),
            borderRadius: BorderRadius.circular(10),
            border: Border(
              left: BorderSide(
                color: widget.isSelected
                    ? widget.accentColor
                    : (_isHovered
                        ? widget.palette.accent.withValues(alpha: 0.5)
                        : Colors.transparent),
                width: 3.0,
              ),
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          child: widget.child,
        ),
      ),
    );
  }
}
