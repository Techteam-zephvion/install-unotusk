import 'dart:io';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:window_manager/window_manager.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'unotusk_logo.dart';
import 'user_menu_popup.dart';

String _computeUserInitials(String name) {
  final parts =
      name.trim().split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
  if (parts.isEmpty) return 'U';
  if (parts.length == 1) {
    return parts[0].substring(0, parts[0].length >= 2 ? 2 : 1).toUpperCase();
  }
  return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
}

class UnoSidebar extends StatefulWidget {
  final bool open;
  final VoidCallback onToggle;
  final VoidCallback onNewQuery;
  final UnoPalette palette;
  final String activeView;
  final Function(String) onViewChange;
  final Function(dynamic) onLoadRecentChat;
  final UserModel user;
  final VoidCallback onLogOut;
  final Function(String) onNavigateSettings;
  final VoidCallback onOpenArchivedModal;
  final String? activeConversationId;
  final String? projectId;

  const UnoSidebar({
    super.key,
    required this.open,
    required this.onToggle,
    required this.onNewQuery,
    required this.palette,
    required this.activeView,
    required this.onViewChange,
    required this.onLoadRecentChat,
    required this.user,
    required this.onLogOut,
    required this.onNavigateSettings,
    required this.onOpenArchivedModal,
    this.activeConversationId,
    this.projectId,
  });

  @override
  State<UnoSidebar> createState() => _UnoSidebarState();
}

class _UnoSidebarState extends State<UnoSidebar>
    with SingleTickerProviderStateMixin {
  static const double _collapsedWidth = 72.0;
  static const double _expandedWidth = 264.0;
  static const double _horizontalPad = 16.0;
  static const double _expandedInnerWidth = _expandedWidth - _horizontalPad * 2;

  bool _userMenuOpen = false;
  late final AnimationController _expandController;
  late final Animation<double> _expandAnim;

  // Nav items: Projects + 5 core workspace views
  final List<Map<String, dynamic>> _navItems = const [
    {'id': 'projects', 'label': 'Projects', 'icon': LucideIcons.folder},
    {'id': 'overview', 'label': 'Overview', 'icon': LucideIcons.layoutDashboard},
    {'id': 'chat', 'label': 'Ask AI', 'icon': LucideIcons.sparkles},
    {'id': 'files', 'label': 'Files', 'icon': LucideIcons.folderTree},
    {'id': 'graph', 'label': 'Architecture', 'icon': LucideIcons.gitFork},
    {'id': 'feed', 'label': 'Ingestion Feed', 'icon': LucideIcons.radio},
  ];

  @override
  void initState() {
    super.initState();
    _expandController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
      value: widget.open ? 1.0 : 0.0,
    );
    _expandAnim = CurvedAnimation(
      parent: _expandController,
      curve: const Cubic(0.22, 1.0, 0.36, 1.0),
      reverseCurve: const Cubic(0.22, 1.0, 0.36, 1.0),
    );
  }

  @override
  void didUpdateWidget(covariant UnoSidebar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.open != oldWidget.open) {
      if (widget.open) {
        _expandController.forward();
      } else {
        _expandController.reverse();
      }
    }
  }

  @override
  void dispose() {
    _expandController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = p.isDark;
    final isCollapsed = !widget.open;

    return AnimatedBuilder(
      animation: _expandAnim,
      builder: (context, _) {
        final t = _expandAnim.value;
        final width = lerpDouble(_collapsedWidth, _expandedWidth, t)!;
        final innerWidth = width - _horizontalPad * 2;
        // Labels fade in cleanly during the upper portion of expansion
        final labelOpacity = ((t - 0.28) / 0.56).clamp(0.0, 1.0);

        return Container(
          width: width,
          decoration: BoxDecoration(
            gradient: p.sidebarGradient,
            border: Border(
              right: BorderSide(color: p.div.withValues(alpha: 0.65)),
            ),
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              // ── Single Unified Fluid Layout (Icons locked at x = 36.0) ──
              SizedBox(
                width: width,
                height: double.infinity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // 1. Header: Unotusk Brand (morphs to Open button on hover when collapsed)
                    Padding(
                      padding: EdgeInsets.fromLTRB(
                        _horizontalPad,
                        (!kIsWeb && Platform.isMacOS) ? 36 : 14,
                        _horizontalPad,
                        14,
                      ),
                      child: _UnifiedBrandHeader(
                        palette: p,
                        isDark: isDark,
                        isCollapsed: isCollapsed,
                        expandT: t,
                        labelOpacity: labelOpacity,
                        innerWidth: innerWidth,
                        expandedInnerWidth: _expandedInnerWidth,
                        onBrandTap: () => widget.onViewChange('projects'),
                        onToggle: widget.onToggle,
                      ),
                    ),

                    // 2. Unified Morphing "New Query" Button
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        _horizontalPad,
                        0,
                        _horizontalPad,
                        16,
                      ),
                      child: _UnifiedNewQueryButton(
                        palette: p,
                        isCollapsed: isCollapsed,
                        expandT: t,
                        labelOpacity: labelOpacity,
                        innerWidth: innerWidth,
                        onTap: widget.onNewQuery,
                      ),
                    ),

                    // 3. Scrollable Unified Navigation List
                    Expanded(
                      child: ScrollConfiguration(
                        behavior: ScrollConfiguration.of(context).copyWith(
                          scrollbars: false,
                        ),
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.symmetric(
                            horizontal: _horizontalPad,
                            vertical: 2,
                          ),
                          physics: const BouncingScrollPhysics(),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              for (int i = 0; i < _navItems.length; i++) ...[
                                Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 2.5),
                                  child: _UnifiedNavItem(
                                    icon: _navItems[i]['icon'] as IconData,
                                    label: _navItems[i]['label'] as String,
                                    active:
                                        widget.activeView == _navItems[i]['id'],
                                    isDark: isDark,
                                    isCollapsed: isCollapsed,
                                    expandT: t,
                                    labelOpacity: labelOpacity,
                                    innerWidth: innerWidth,
                                    expandedInnerWidth: _expandedInnerWidth,
                                    palette: p,
                                    onTap: () => widget.onViewChange(
                                        _navItems[i]['id'] as String),
                                  ),
                                ),
                                if (i == 0) const SizedBox(height: 10),
                              ],
                              if (t > 0.05) ...[
                                Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 10),
                                  child: Divider(
                                    height: 1,
                                    thickness: 1,
                                    color: p.div.withValues(alpha: 0.5),
                                  ),
                                ),
                                Opacity(
                                  opacity: labelOpacity,
                                  child: Padding(
                                    padding: const EdgeInsets.fromLTRB(6, 4, 4, 6),
                                    child: Row(
                                      children: [
                                        Text(
                                          'Recent chats',
                                          style: UnoTypography.mono(
                                            color: p.textMuted,
                                            fontSize: 10.5,
                                            fontWeight: FontWeight.w600,
                                            letterSpacing: 0.4,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                                ValueListenableBuilder<List<RecentChat>>(
                                  valueListenable: ApiService.recentChatsNotifier,
                                  builder: (context, chats, _) {
                                    if (chats.isEmpty) {
                                      return Opacity(
                                        opacity: labelOpacity,
                                        child: Padding(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 8, vertical: 8),
                                          child: Text(
                                            'No recent chats',
                                            style: UnoTypography.body(
                                              color: p.textMuted,
                                              fontSize: 12,
                                            ),
                                          ),
                                        ),
                                      );
                                    }
                                    return Column(
                                      crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: chats.map((chat) {
                                        final isActive = widget.activeConversationId ==
                                            chat.id.toString();
                                        return Padding(
                                          key: ValueKey('pad_${chat.id}_${chat.isPinned}_${chat.title}'),
                                          padding: const EdgeInsets.symmetric(
                                              vertical: 1.5),
                                          child: _RecentChatRow(
                                            key: ValueKey('row_${chat.id}_${chat.isPinned}_${chat.title}'),
                                            chat: chat,
                                            isActive: isActive,
                                            palette: p,
                                            isDark: isDark,
                                            expandT: t,
                                            labelOpacity: labelOpacity,
                                            innerWidth: innerWidth,
                                            expandedInnerWidth:
                                                _expandedInnerWidth,
                                            onTap: () => widget
                                                .onLoadRecentChat(chat.id),
                                            onRename: (newTitle) =>
                                                ApiService.renameConversation(
                                              chat.id.toString(),
                                              newTitle,
                                              projectId: chat.projectId ?? widget.projectId,
                                            ),
                                            onTogglePin: () =>
                                                ApiService.togglePinConversation(
                                              chat.id.toString(),
                                              !chat.isPinned,
                                              projectId: chat.projectId ?? widget.projectId,
                                            ),
                                            onArchive: () {
                                              if (widget.activeConversationId ==
                                                  chat.id.toString()) {
                                                widget.onNewQuery();
                                              }
                                              ApiService.archiveConversation(
                                                chat.id.toString(),
                                                archive: true,
                                                projectId: chat.projectId ?? widget.projectId,
                                              );
                                            },
                                            onDelete: () {
                                              if (widget.activeConversationId ==
                                                  chat.id.toString()) {
                                                widget.onNewQuery();
                                              }
                                              ApiService.deleteConversation(
                                                chat.id.toString(),
                                                projectId: chat.projectId ?? widget.projectId,
                                              );
                                            },
                                          ),
                                        );
                                      }).toList(),
                                    );
                                  },
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),

                    // 4. Archived Chats Button (Exact same x = 36.0 icon axis)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        _horizontalPad,
                        4,
                        _horizontalPad,
                        6,
                      ),
                      child: _UnifiedNavItem(
                        icon: LucideIcons.archive,
                        label: 'Archived chats',
                        active: false,
                        isDark: isDark,
                        isCollapsed: isCollapsed,
                        expandT: t,
                        labelOpacity: labelOpacity,
                        innerWidth: innerWidth,
                        expandedInnerWidth: _expandedInnerWidth,
                        palette: p,
                        onTap: widget.onOpenArchivedModal,
                      ),
                    ),

                    // 5. Unified Morphing User Profile Footer
                    Padding(
                      padding: EdgeInsets.fromLTRB(
                        lerpDouble(_horizontalPad, 12.0, t)!,
                        6,
                        lerpDouble(_horizontalPad, 12.0, t)!,
                        14,
                      ),
                      child: _UnifiedUserFooter(
                        palette: p,
                        user: widget.user,
                        isOpen: _userMenuOpen,
                        isCollapsed: isCollapsed,
                        expandT: t,
                        labelOpacity: labelOpacity,
                        onTap: () =>
                            setState(() => _userMenuOpen = !_userMenuOpen),
                      ),
                    ),
                  ],
                ),
              ),

              // ── Animated User Profile Menu Popup ──
              Positioned(
                left: lerpDouble(80.0, 12.0, t)!,
                bottom: lerpDouble(16.0, 74.0, t)!,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 180),
                  switchInCurve: Curves.easeOutCubic,
                  switchOutCurve: Curves.easeInCubic,
                  transitionBuilder: (child, animation) {
                    return FadeTransition(
                      opacity: animation,
                      child: SlideTransition(
                        position: Tween<Offset>(
                          begin: const Offset(0, 0.05),
                          end: Offset.zero,
                        ).animate(animation),
                        child: ScaleTransition(
                          scale: Tween<double>(begin: 0.96, end: 1.0)
                              .animate(animation),
                          alignment: Alignment.bottomLeft,
                          child: child,
                        ),
                      ),
                    );
                  },
                  child: _userMenuOpen
                      ? UserMenuPopup(
                          key: const ValueKey('user-menu-open'),
                          palette: p,
                          user: widget.user,
                          onNavigateSettings: widget.onNavigateSettings,
                          onLogOut: widget.onLogOut,
                          onClose: () => setState(() => _userMenuOpen = false),
                        )
                      : const SizedBox.shrink(key: ValueKey('user-menu-closed')),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Right-Side Floating Hover Tooltip (Never covers adjacent icons)
// ─────────────────────────────────────────────────────────
class _SidebarRightTooltip extends StatefulWidget {
  final String label;
  final bool enabled;
  final UnoPalette palette;
  final Widget child;

  const _SidebarRightTooltip({
    required this.label,
    required this.enabled,
    required this.palette,
    required this.child,
  });

  @override
  State<_SidebarRightTooltip> createState() => _SidebarRightTooltipState();
}

class _SidebarRightTooltipState extends State<_SidebarRightTooltip> {
  final LayerLink _layerLink = LayerLink();
  OverlayEntry? _overlayEntry;
  bool _hovered = false;

  void _showOverlay() {
    if (!widget.enabled || _overlayEntry != null || !mounted) return;
    final overlay = Overlay.maybeOf(context);
    if (overlay == null) return;

    final p = widget.palette;
    final bgColor =
        p.isDark ? const Color(0xFF182238) : const Color(0xFF111728);
    final borderColor =
        p.isDark ? const Color(0xFF2B3754) : const Color(0xFF232C42);

    _overlayEntry = OverlayEntry(
      builder: (context) {
        return Positioned(
          left: 0,
          top: 0,
          child: IgnorePointer(
            child: CompositedTransformFollower(
              link: _layerLink,
              showWhenUnlinked: false,
              targetAnchor: Alignment.centerRight,
              followerAnchor: Alignment.centerLeft,
              offset: const Offset(18, 0),
              child: Material(
                color: Colors.transparent,
                child: TweenAnimationBuilder<double>(
                  tween: Tween<double>(begin: 0.0, end: 1.0),
                  duration: const Duration(milliseconds: 150),
                  curve: Curves.easeOutCubic,
                  builder: (context, v, child) {
                    return Opacity(
                      opacity: v,
                      child: Transform.translate(
                        offset: Offset(-5.0 * (1.0 - v), 0.0),
                        child: child,
                      ),
                    );
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 11,
                      vertical: 6.5,
                    ),
                    decoration: BoxDecoration(
                      color: bgColor,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: borderColor, width: 1),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF040712)
                              .withValues(alpha: p.isDark ? 0.42 : 0.20),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Text(
                      widget.label,
                      style: UnoTypography.body(
                        color: const Color(0xFFF4F1EC),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                        height: 1.15,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );

    overlay.insert(_overlayEntry!);
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  @override
  void didUpdateWidget(covariant _SidebarRightTooltip oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.enabled ||
        widget.label != oldWidget.label ||
        widget.palette != oldWidget.palette) {
      _removeOverlay();
      if (_hovered && widget.enabled) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted && _hovered && widget.enabled) {
            _showOverlay();
          }
        });
      }
    }
  }

  @override
  void dispose() {
    _removeOverlay();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CompositedTransformTarget(
      link: _layerLink,
      child: MouseRegion(
        onEnter: (_) {
          _hovered = true;
          if (widget.enabled) _showOverlay();
        },
        onExit: (_) {
          _hovered = false;
          _removeOverlay();
        },
        child: widget.child,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Unified Brand Header — Logo morphs to Open Button on hover when collapsed
// ─────────────────────────────────────────────────────────
class _UnifiedBrandHeader extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final bool isCollapsed;
  final double expandT;
  final double labelOpacity;
  final double innerWidth;
  final double expandedInnerWidth;
  final VoidCallback onBrandTap;
  final VoidCallback onToggle;

  const _UnifiedBrandHeader({
    required this.palette,
    required this.isDark,
    required this.isCollapsed,
    required this.expandT,
    required this.labelOpacity,
    required this.innerWidth,
    required this.expandedInnerWidth,
    required this.onBrandTap,
    required this.onToggle,
  });

  @override
  State<_UnifiedBrandHeader> createState() => _UnifiedBrandHeaderState();
}

class _UnifiedBrandHeaderState extends State<_UnifiedBrandHeader> {
  bool _logoHovered = false;
  bool _logoPressed = false;
  bool _collapseHovered = false;
  bool _collapsePressed = false;

  @override
  void didUpdateWidget(covariant _UnifiedBrandHeader oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isCollapsed != oldWidget.isCollapsed) {
      _logoHovered = false;
      _logoPressed = false;
      _collapseHovered = false;
      _collapsePressed = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = widget.isDark;
    final isCollapsed = widget.isCollapsed;
    final showOpenOnHover = isCollapsed && widget.expandT < 0.15 && _logoHovered;

    return SizedBox(
      height: 40,
      width: widget.innerWidth,
      child: ClipRect(
        child: OverflowBox(
          alignment: Alignment.centerLeft,
          minWidth: widget.expandedInnerWidth,
          maxWidth: widget.expandedInnerWidth,
          child: Row(
            children: [
              // ── Leading 40×40 Logo / Borderless Hover-to-Open Slot (Locked at x = 36.0) ──
              _SidebarRightTooltip(
                label: 'Open sidebar',
                enabled: isCollapsed,
                palette: p,
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  onEnter: (_) => setState(() => _logoHovered = true),
                  onExit: (_) => setState(() {
                    _logoHovered = false;
                    _logoPressed = false;
                  }),
                  child: GestureDetector(
                    onTapDown: (_) => setState(() => _logoPressed = true),
                    onTapUp: (_) => setState(() => _logoPressed = false),
                    onTapCancel: () => setState(() => _logoPressed = false),
                    onTap: isCollapsed ? widget.onToggle : widget.onBrandTap,
                    behavior: HitTestBehavior.opaque,
                    child: AnimatedScale(
                      scale: _logoPressed ? 0.90 : 1.0,
                      duration: const Duration(milliseconds: 100),
                      curve: Curves.easeOutCubic,
                      child: SizedBox(
                        width: 40,
                        height: 40,
                        child: TweenAnimationBuilder<double>(
                          tween: Tween<double>(
                            end: showOpenOnHover ? 1.0 : 0.0,
                          ),
                          duration: const Duration(milliseconds: 240),
                          curve: Curves.easeInOutCubic,
                          builder: (context, morph, _) {
                            return Stack(
                              alignment: Alignment.center,
                              children: [
                                if (morph < 0.99)
                                  Opacity(
                                    opacity: (1.0 - morph).clamp(0.0, 1.0),
                                    child: Transform.scale(
                                      scale: lerpDouble(1.0, 0.82, morph)!,
                                      child: UnotuskLogo(
                                        size: 22,
                                        onDark: isDark,
                                      ),
                                    ),
                                  ),
                                if (morph > 0.01)
                                  Opacity(
                                    opacity: morph.clamp(0.0, 1.0),
                                    child: Transform.scale(
                                      scale: lerpDouble(0.82, 1.0, morph)!,
                                      child: Icon(
                                        LucideIcons.panelLeftOpen,
                                        size: 18,
                                        color: p.accent,
                                      ),
                                    ),
                                  ),
                              ],
                            );
                          },
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              // ── Wordmark & Draggable Area (fades smoothly during collapse) ──
              Expanded(
                child: IgnorePointer(
                  ignoring: widget.expandT < 0.5,
                  child: Opacity(
                    opacity: widget.labelOpacity,
                    child: DragToMoveArea(
                      child: GestureDetector(
                        onTap: widget.onBrandTap,
                        behavior: HitTestBehavior.opaque,
                        child: Padding(
                          padding: const EdgeInsets.only(left: 4),
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'Unotusk',
                              maxLines: 1,
                              overflow: TextOverflow.clip,
                              style: UnoTypography.brandSerif(
                                palette: p,
                                fontSize: 17,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              // ── Collapse Sidebar Button (Right side when expanded) ──
              IgnorePointer(
                ignoring: widget.expandT < 0.5,
                child: Opacity(
                  opacity: widget.labelOpacity,
                  child: Tooltip(
                    message: 'Collapse sidebar',
                    child: MouseRegion(
                      cursor: SystemMouseCursors.click,
                      onEnter: (_) => setState(() => _collapseHovered = true),
                      onExit: (_) => setState(() {
                        _collapseHovered = false;
                        _collapsePressed = false;
                      }),
                      child: GestureDetector(
                        onTapDown: (_) =>
                            setState(() => _collapsePressed = true),
                        onTapUp: (_) =>
                            setState(() => _collapsePressed = false),
                        onTapCancel: () =>
                            setState(() => _collapsePressed = false),
                        onTap: widget.onToggle,
                        behavior: HitTestBehavior.opaque,
                        child: AnimatedScale(
                          scale: _collapsePressed
                              ? 0.90
                              : (_collapseHovered ? 1.08 : 1.0),
                          duration: const Duration(milliseconds: 140),
                          curve: Curves.easeOutCubic,
                          child: SizedBox(
                            width: 32,
                            height: 32,
                            child: Center(
                              child: Icon(
                                LucideIcons.panelLeftClose,
                                size: 17,
                                color: _collapseHovered ? p.accent : p.textSec,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Unified Morphing "New Query" Button (40x40 '+' <-> Full Pill)
// ─────────────────────────────────────────────────────────
class _UnifiedNewQueryButton extends StatefulWidget {
  final UnoPalette palette;
  final bool isCollapsed;
  final double expandT;
  final double labelOpacity;
  final double innerWidth;
  final VoidCallback onTap;

  const _UnifiedNewQueryButton({
    required this.palette,
    required this.isCollapsed,
    required this.expandT,
    required this.labelOpacity,
    required this.innerWidth,
    required this.onTap,
  });

  @override
  State<_UnifiedNewQueryButton> createState() => _UnifiedNewQueryButtonState();
}

class _UnifiedNewQueryButtonState extends State<_UnifiedNewQueryButton> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = p.isDark;
    final accent = p.accent;
    final fgColor =
        isDark ? const Color(0xFF0B1020) : const Color(0xFFF4F1EC);
    final bgColor = _pressed
        ? Color.lerp(accent, Colors.black, 0.10)!
        : _hovered
            ? Color.lerp(
                accent, isDark ? Colors.white : const Color(0xFF1E263D), 0.14)!
            : accent;

    return _SidebarRightTooltip(
      label: 'New Query',
      enabled: widget.isCollapsed,
      palette: p,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() {
          _hovered = false;
          _pressed = false;
        }),
        child: GestureDetector(
          onTapDown: (_) => setState(() => _pressed = true),
          onTapUp: (_) => setState(() => _pressed = false),
          onTapCancel: () => setState(() => _pressed = false),
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedScale(
            scale: _pressed ? 0.97 : 1.0,
            duration: const Duration(milliseconds: 95),
            curve: Curves.easeOutCubic,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 170),
              curve: Curves.easeOutCubic,
              width: widget.innerWidth,
              height: 40,
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(10),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF050814).withValues(
                      alpha: isDark
                          ? (_hovered ? 0.30 : 0.16)
                          : (_hovered ? 0.14 : 0.07),
                    ),
                    blurRadius: _hovered ? 10 : 5,
                    offset: Offset(0, _hovered ? 3 : 1.5),
                  ),
                ],
              ),
              child: ClipRect(
                child: Center(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      AnimatedScale(
                        scale: _hovered ? 1.08 : 1.0,
                        duration: const Duration(milliseconds: 170),
                        curve: Curves.easeOutCubic,
                        child: Icon(
                          LucideIcons.plus,
                          size: 16,
                          color: fgColor,
                        ),
                      ),
                      ClipRect(
                        child: Align(
                          alignment: Alignment.centerLeft,
                          widthFactor: widget.expandT.clamp(0.0, 1.0),
                          child: Opacity(
                            opacity: widget.labelOpacity,
                            child: Padding(
                              padding: const EdgeInsets.only(left: 8),
                              child: Text(
                                'New Query',
                                maxLines: 1,
                                softWrap: false,
                                style: UnoTypography.body(
                                  color: fgColor,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
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
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Unified Sidebar Nav Item — Single Tree, Pixel-Locked Icons, Right Tooltip
// ─────────────────────────────────────────────────────────
class _UnifiedNavItem extends StatefulWidget {
  final IconData icon;
  final String label;
  final bool active;
  final bool isDark;
  final bool isCollapsed;
  final double expandT;
  final double labelOpacity;
  final double innerWidth;
  final double expandedInnerWidth;
  final UnoPalette palette;
  final VoidCallback onTap;

  const _UnifiedNavItem({
    required this.icon,
    required this.label,
    required this.active,
    required this.isDark,
    required this.isCollapsed,
    required this.expandT,
    required this.labelOpacity,
    required this.innerWidth,
    required this.expandedInnerWidth,
    required this.palette,
    required this.onTap,
  });

  @override
  State<_UnifiedNavItem> createState() => _UnifiedNavItemState();
}

class _UnifiedNavItemState extends State<_UnifiedNavItem> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final active = widget.active;
    final p = widget.palette;

    // Zero-alpha matched RGB base prevents muddy grey lerp flashes
    final hoverBase =
        isDark ? const Color(0xFFE9DFD0) : const Color(0xFF0B1020);

    final Gradient? bgGradient = active
        ? (isDark
            ? const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF1E2840),
                  Color(0xFF141C30),
                ],
              )
            : const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFFFFFFFF),
                  Color(0xFFF6F3EC),
                ],
              ))
        : null;

    final bgColor = active
        ? null
        : hoverBase.withValues(alpha: _hovered ? 0.055 : 0.0);

    final borderColor = active
        ? (isDark ? p.accent.withValues(alpha: 0.26) : const Color(0xFFDCD4C6))
        : (_hovered
            ? (isDark ? p.div.withValues(alpha: 0.8) : const Color(0xFFE2DDD2))
            : Colors.transparent);

    final iconColor = active
        ? p.accent
        : (_hovered
            ? p.accent
            : (isDark ? p.accentMuted.withValues(alpha: 0.78) : p.textSec));

    final textColor = active ? p.text : (_hovered ? p.text : p.textSec);

    final shadows = active
        ? [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.32 : 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
            if (isDark)
              BoxShadow(
                color: p.accent.withValues(alpha: 0.05),
                blurRadius: 1,
                offset: const Offset(0, 1),
              ),
          ]
        : <BoxShadow>[];

    return _SidebarRightTooltip(
      label: widget.label,
      enabled: widget.isCollapsed,
      palette: p,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() {
          _hovered = false;
          _pressed = false;
        }),
        child: GestureDetector(
          onTapDown: (_) => setState(() => _pressed = true),
          onTapUp: (_) => setState(() => _pressed = false),
          onTapCancel: () => setState(() => _pressed = false),
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedScale(
            scale: _pressed ? 0.975 : 1.0,
            duration: const Duration(milliseconds: 95),
            curve: Curves.easeOutCubic,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              curve: Curves.easeOutCubic,
              width: widget.innerWidth,
              height: 40,
              decoration: BoxDecoration(
                gradient: bgGradient,
                color: bgColor,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: borderColor, width: 1),
                boxShadow: shadows,
              ),
              child: ClipRect(
                child: OverflowBox(
                  alignment: Alignment.centerLeft,
                  minWidth: widget.expandedInnerWidth,
                  maxWidth: widget.expandedInnerWidth,
                  child: Row(
                    children: [
                      // Leading 40×40 slot with centered 28×28 icon badge (axis locked at x = 36.0)
                      SizedBox(
                        width: 40,
                        height: 40,
                        child: Center(
                          child: AnimatedScale(
                            scale: (widget.isCollapsed && _hovered)
                                ? 1.08
                                : 1.0,
                            duration: const Duration(milliseconds: 160),
                            curve: Curves.easeOutCubic,
                            child: Container(
                              width: 28,
                              height: 28,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(7),
                                color: active
                                    ? (isDark
                                        ? p.accent.withValues(alpha: 0.12)
                                        : p.accent.withValues(alpha: 0.08))
                                    : Colors.transparent,
                              ),
                              child: Center(
                                child: Icon(
                                  widget.icon,
                                  size: 16.0,
                                  color: iconColor,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Opacity(
                          opacity: widget.labelOpacity,
                          child: AnimatedDefaultTextStyle(
                            duration: const Duration(milliseconds: 160),
                            curve: Curves.easeOutCubic,
                            style: UnoTypography.body(
                              color: textColor,
                              fontSize: 13.5,
                              fontWeight: active
                                  ? FontWeight.w600
                                  : (_hovered
                                      ? FontWeight.w500
                                      : FontWeight.w400),
                            ),
                            child: Text(
                              widget.label,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                      ),
                      // Modern luminous right-side active indicator
                      if (active)
                        Opacity(
                          opacity: widget.labelOpacity,
                          child: Container(
                            width: 3.5,
                            height: 14.0,
                            margin: const EdgeInsets.only(right: 12),
                            decoration: BoxDecoration(
                              color: p.accent,
                              borderRadius: BorderRadius.circular(2),
                              boxShadow: [
                                BoxShadow(
                                  color: p.accent.withValues(alpha: 0.5),
                                  blurRadius: 4,
                                ),
                              ],
                            ),
                          ),
                        )
                      else
                        const SizedBox(width: 10),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Unified Morphing User Profile Footer (Avatar <-> Full Card)
// ─────────────────────────────────────────────────────────
class _UnifiedUserFooter extends StatefulWidget {
  final UnoPalette palette;
  final UserModel user;
  final bool isOpen;
  final bool isCollapsed;
  final double expandT;
  final double labelOpacity;
  final VoidCallback onTap;

  const _UnifiedUserFooter({
    required this.palette,
    required this.user,
    required this.isOpen,
    required this.isCollapsed,
    required this.expandT,
    required this.labelOpacity,
    required this.onTap,
  });

  @override
  State<_UnifiedUserFooter> createState() => _UnifiedUserFooterState();
}

class _UnifiedUserFooterState extends State<_UnifiedUserFooter> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = p.isDark;
    final isActive = widget.isOpen || _hovered;
    final t = widget.expandT;

    final displayName =
        widget.user.name.isNotEmpty ? widget.user.name : 'User';
    final subtitle =
        widget.user.org.isNotEmpty ? widget.user.org : widget.user.email;
    final initials = _computeUserInitials(displayName);

    final cardBgExpanded = isDark
        ? (isActive ? const Color(0xFF1D263E) : const Color(0xFF141C2F))
        : (isActive ? const Color(0xFFFFFFFF) : const Color(0xFFFAF7F2));
    final cardBg = Color.lerp(
      cardBgExpanded.withValues(alpha: 0.0),
      cardBgExpanded,
      t,
    )!;

    final cardCutout = isDark
        ? (t > 0.5
            ? (isActive ? const Color(0xFF1D263E) : const Color(0xFF141C2F))
            : p.bgSidebar)
        : (t > 0.5 ? const Color(0xFFFAF7F2) : p.bgSidebar);

    final cardBorderBase = isDark
        ? (isActive
            ? p.accent.withValues(alpha: 0.28)
            : p.div.withValues(alpha: 0.85))
        : (isActive
            ? const Color(0xFF0B1020).withValues(alpha: 0.24)
            : const Color(0xFFE2DBD0));
    final cardBorder = Color.lerp(
      cardBorderBase.withValues(alpha: 0.0),
      cardBorderBase,
      t,
    )!;

    final avatarBg = isDark ? p.accent : const Color(0xFF0B1020);
    final avatarFg =
        isDark ? const Color(0xFF0B1020) : const Color(0xFFE9DFD0);
    final menuIndicatorBase = isDark ? p.accent : const Color(0xFF0B1020);

    return _SidebarRightTooltip(
      label: displayName,
      enabled: widget.isCollapsed && !widget.isOpen,
      palette: p,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() {
          _hovered = false;
          _pressed = false;
        }),
        child: GestureDetector(
          onTapDown: (_) => setState(() => _pressed = true),
          onTapUp: (_) => setState(() => _pressed = false),
          onTapCancel: () => setState(() => _pressed = false),
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedScale(
            scale: _pressed ? 0.97 : 1.0,
            duration: const Duration(milliseconds: 95),
            curve: Curves.easeOutCubic,
            child: Container(
              height: 54,
              padding: EdgeInsets.symmetric(
                horizontal: lerpDouble(0.0, 9.0, t)!,
              ),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: cardBorder, width: 1),
              ),
              child: ClipRect(
                child: OverflowBox(
                  alignment: Alignment.centerLeft,
                  minWidth: 222,
                  maxWidth: 222,
                  child: Row(
                    children: [
                      // Circular Monogram Avatar (centered inside 40px slot at x = 36.0)
                      SizedBox(
                        width: 40,
                        height: 40,
                        child: Center(
                          child: AnimatedScale(
                            scale: isActive ? 1.06 : 1.0,
                            duration: const Duration(milliseconds: 170),
                            curve: Curves.easeOutCubic,
                            child: Stack(
                              clipBehavior: Clip.none,
                              children: [
                                Container(
                                  width: 34,
                                  height: 34,
                                  decoration: BoxDecoration(
                                    color: avatarBg,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: isActive
                                          ? avatarBg.withValues(alpha: 0.45)
                                          : avatarBg.withValues(alpha: 0.0),
                                      width: 1.5,
                                    ),
                                  ),
                                  alignment: Alignment.center,
                                  child: Text(
                                    initials,
                                    style: UnoTypography.body(
                                      color: avatarFg,
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                                Positioned(
                                  right: -1,
                                  bottom: -1,
                                  child: Container(
                                    width: 9.5,
                                    height: 9.5,
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF22C55E),
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: cardCutout,
                                        width: 1.8,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(width: 8),

                      // Name & Organization (fades cleanly out on collapse)
                      Expanded(
                        child: Opacity(
                          opacity: widget.labelOpacity,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                displayName,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: UnoTypography.body(
                                  color: p.text,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              if (subtitle.isNotEmpty) ...[
                                const SizedBox(height: 1.5),
                                Text(
                                  subtitle,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: UnoTypography.body(
                                    color: p.textSec,
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w400,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(width: 4),

                      // Quiet three-dot overflow indicator (zero up/down arrows)
                      Opacity(
                        opacity: widget.labelOpacity,
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 160),
                          curve: Curves.easeOutCubic,
                          width: 24,
                          height: 24,
                          decoration: BoxDecoration(
                            color: menuIndicatorBase.withValues(
                                alpha: isActive ? 0.10 : 0.0),
                            borderRadius: BorderRadius.circular(7),
                          ),
                          alignment: Alignment.center,
                          child: Icon(
                            LucideIcons.ellipsis,
                            size: 14,
                            color: isActive
                                ? p.accent
                                : p.textMuted.withValues(alpha: 0.7),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Recent Chat Item Row with Hover Actions and Context Menu
// ─────────────────────────────────────────────────────────
class _RecentChatRow extends StatefulWidget {
  final RecentChat chat;
  final bool isActive;
  final UnoPalette palette;
  final bool isDark;
  final double expandT;
  final double labelOpacity;
  final double innerWidth;
  final double expandedInnerWidth;
  final VoidCallback onTap;
  final Function(String) onRename;
  final VoidCallback onTogglePin;
  final VoidCallback onArchive;
  final VoidCallback onDelete;

  const _RecentChatRow({
    super.key,
    required this.chat,
    required this.isActive,
    required this.palette,
    required this.isDark,
    required this.expandT,
    required this.labelOpacity,
    required this.innerWidth,
    required this.expandedInnerWidth,
    required this.onTap,
    required this.onRename,
    required this.onTogglePin,
    required this.onArchive,
    required this.onDelete,
  });

  @override
  State<_RecentChatRow> createState() => _RecentChatRowState();
}

class _RecentChatRowState extends State<_RecentChatRow> {
  bool _hovered = false;
  bool _btnHovered = false;
  bool _menuOpen = false;

  void _showRenameDialog() {
    final textController = TextEditingController(text: widget.chat.title);
    final isDark = widget.isDark;
    final cardBg = isDark ? const Color(0xFF161A29) : const Color(0xFFFFFFFF);
    final borderColor =
        isDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6);

    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: cardBg,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: borderColor),
        ),
        title: Text(
          'Rename conversation',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
        content: TextField(
          controller: textController,
          autofocus: true,
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 13,
          ),
          decoration: InputDecoration(
            hintText: 'Enter chat title',
            hintStyle: UnoTypography.body(
              color: widget.palette.textSec,
              fontSize: 13,
            ),
            filled: true,
            fillColor: widget.palette.bgElevated,
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: widget.palette.div),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: widget.palette.accent, width: 1.5),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          ),
          onSubmitted: (val) {
            final t = val.trim();
            if (t.isNotEmpty) {
              Navigator.of(ctx).pop();
              widget.onRename(t);
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(
              'Cancel',
              style: UnoTypography.body(
                  color: widget.palette.textSec, fontSize: 13),
            ),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: widget.palette.accent,
              foregroundColor:
                  widget.isDark ? const Color(0xFF0B1020) : Colors.white,
            ),
            onPressed: () {
              final t = textController.text.trim();
              if (t.isNotEmpty) {
                Navigator.of(ctx).pop();
                widget.onRename(t);
              }
            },
            child: Text(
              'Save',
              style: UnoTypography.body(
                color: widget.isDark ? const Color(0xFF0B1020) : Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showDeleteDialog() {
    final isDark = widget.isDark;
    final cardBg = isDark ? const Color(0xFF161A29) : const Color(0xFFFFFFFF);
    final borderColor =
        isDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6);

    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: cardBg,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: borderColor),
        ),
        title: Text(
          'Delete chat?',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
        content: Text(
          'Are you sure you want to delete "${widget.chat.title}"? This cannot be undone.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 13,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(
              'Cancel',
              style: UnoTypography.body(
                  color: widget.palette.textSec, fontSize: 13),
            ),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFEF4444),
            ),
            onPressed: () {
              Navigator.of(ctx).pop();
              widget.onDelete();
            },
            child: Text(
              'Delete',
              style: UnoTypography.body(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<PopupMenuEntry<String>> _buildMenuItems(dynamic p, bool isPinned) {
    return [
      PopupMenuItem<String>(
        value: 'pin',
        height: 36,
        child: Row(
          children: [
            Icon(LucideIcons.pin, size: 14, color: p.text),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                isPinned ? 'Unpin' : 'Pin to top',
                style: UnoTypography.body(color: p.text, fontSize: 13),
              ),
            ),
            Text(
              'P',
              style: UnoTypography.mono(color: p.textMuted, fontSize: 11),
            ),
          ],
        ),
      ),
      PopupMenuItem<String>(
        value: 'rename',
        height: 36,
        child: Row(
          children: [
            Icon(LucideIcons.pencil, size: 14, color: p.text),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                'Rename',
                style: UnoTypography.body(color: p.text, fontSize: 13),
              ),
            ),
            Text(
              'R',
              style: UnoTypography.mono(color: p.textMuted, fontSize: 11),
            ),
          ],
        ),
      ),
      PopupMenuItem<String>(
        value: 'archive',
        height: 36,
        child: Row(
          children: [
            Icon(LucideIcons.archive, size: 14, color: p.text),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                'Archive',
                style: UnoTypography.body(color: p.text, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
      const PopupMenuDivider(height: 8),
      PopupMenuItem<String>(
        value: 'delete',
        height: 36,
        child: Row(
          children: [
            const Icon(LucideIcons.trash2, size: 14, color: Color(0xFFEF4444)),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                'Delete',
                style: UnoTypography.body(
                  color: const Color(0xFFEF4444),
                  fontSize: 13,
                ),
              ),
            ),
            Text(
              'D',
              style: UnoTypography.mono(
                color: const Color(0xFFEF4444).withValues(alpha: 0.7),
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    ];
  }

  void _handleMenuAction(String value) {
    switch (value) {
      case 'pin':
        widget.onTogglePin();
        break;
      case 'rename':
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _showRenameDialog();
        });
        break;
      case 'archive':
        widget.onArchive();
        break;
      case 'delete':
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _showDeleteDialog();
        });
        break;
    }
  }

  void _showContextMenuAt(Offset globalPosition) async {
    final isDark = widget.isDark;
    final p = widget.palette;
    final isPinned = widget.chat.isPinned;

    setState(() => _menuOpen = true);

    final overlay =
        Overlay.of(context).context.findRenderObject() as RenderBox?;
    if (overlay == null) {
      setState(() => _menuOpen = false);
      return;
    }

    final RelativeRect position = RelativeRect.fromRect(
      Rect.fromPoints(globalPosition, globalPosition),
      Offset.zero & overlay.size,
    );

    final selected = await showMenu<String>(
      context: context,
      position: position,
      color: isDark ? const Color(0xFF161A29) : const Color(0xFFFFFFFF),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6),
        ),
      ),
      elevation: 14,
      shadowColor: Colors.black.withValues(alpha: isDark ? 0.5 : 0.18),
      items: _buildMenuItems(p, isPinned),
    );

    if (mounted) {
      setState(() => _menuOpen = false);
    }

    if (selected != null) {
      _handleMenuAction(selected);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = widget.isDark;
    final active = widget.isActive;
    final isPinned = widget.chat.isPinned;

    final hoverBase =
        isDark ? const Color(0xFFE9DFD0) : const Color(0xFF0B1020);
    final bgColor = active
        ? p.bgElevated
        : hoverBase.withValues(alpha: _hovered ? 0.055 : 0.0);

    final borderColor = active
        ? (isDark ? p.accent.withValues(alpha: 0.20) : p.div)
        : Colors.transparent;

    final textColor = active ? p.text : (_hovered ? p.text : p.textSec);

    final showBtn = _hovered || _btnHovered || active || _menuOpen;
    final btnOpacity = showBtn ? 1.0 : 0.35;

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onSecondaryTapUp: (details) =>
            _showContextMenuAt(details.globalPosition),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          curve: Curves.easeOutCubic,
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: borderColor, width: 1),
          ),
          child: Row(
            children: [
              // Left clickable area: Icon + Title (Left-click opens chat)
              Expanded(
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: widget.onTap,
                    behavior: HitTestBehavior.opaque,
                    child: Row(
                      children: [
                        // Pin indicator or chat icon
                        if (isPinned)
                          Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: Icon(
                              LucideIcons.pin,
                              size: 13,
                              color: p.accent,
                            ),
                          )
                        else
                          Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: Icon(
                              LucideIcons.messageSquare,
                              size: 13,
                              color: active
                                  ? p.accent
                                  : p.textMuted.withValues(alpha: 0.6),
                            ),
                          ),

                        // Title
                        Expanded(
                          child: Text(
                            widget.chat.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: UnoTypography.body(
                              color: textColor,
                              fontSize: 12.5,
                              fontWeight:
                                  active ? FontWeight.w500 : FontWeight.w400,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              // Contextual Action Button (...) - ALWAYS INTERACTIVE & INDEPENDENT
              MouseRegion(
                cursor: SystemMouseCursors.click,
                onEnter: (_) => setState(() => _btnHovered = true),
                onExit: (_) => setState(() => _btnHovered = false),
                child: SizedBox(
                  width: 28,
                  height: 28,
                  child: AnimatedOpacity(
                    duration: const Duration(milliseconds: 120),
                    opacity: btnOpacity,
                    child: Theme(
                      data: Theme.of(context).copyWith(
                        popupMenuTheme: PopupMenuThemeData(
                          color: isDark
                              ? const Color(0xFF161A29)
                              : const Color(0xFFFFFFFF),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                            side: BorderSide(
                              color: isDark
                                  ? const Color(0xFF2E313C)
                                  : const Color(0xFFE4DFD6),
                            ),
                          ),
                          elevation: 14,
                          shadowColor: Colors.black
                              .withValues(alpha: isDark ? 0.5 : 0.18),
                        ),
                      ),
                      child: PopupMenuButton<String>(
                        tooltip: '',
                        padding: EdgeInsets.zero,
                        position: PopupMenuPosition.under,
                        offset: const Offset(0, 4),
                        onOpened: () => setState(() => _menuOpen = true),
                        onCanceled: () => setState(() => _menuOpen = false),
                        onSelected: (value) {
                          setState(() => _menuOpen = false);
                          _handleMenuAction(value);
                        },
                        child: Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            color: (_menuOpen || _btnHovered)
                                ? (isDark
                                    ? const Color(0xFF2E313C)
                                    : const Color(0xFFE4DFD6))
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          alignment: Alignment.center,
                          child: Icon(
                            LucideIcons.ellipsis,
                            size: 15,
                            color: (_hovered || _btnHovered || _menuOpen || active)
                                ? p.text
                                : p.textSec,
                          ),
                        ),
                        itemBuilder: (context) => _buildMenuItems(p, isPinned),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
