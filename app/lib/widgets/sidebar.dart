import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:window_manager/window_manager.dart';
import '../models/models.dart';
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

class _UnoSidebarState extends State<UnoSidebar> {
  bool _userMenuOpen = false;

  // Nav items: Projects + 6 core workspace views
  final List<Map<String, dynamic>> _navItems = const [
    {'id': 'projects', 'label': 'Projects', 'icon': LucideIcons.folder},
    {'id': 'overview', 'label': 'Overview', 'icon': LucideIcons.layoutDashboard},
    {'id': 'chat', 'label': 'Ask AI', 'icon': LucideIcons.sparkles},
    {'id': 'files', 'label': 'Files', 'icon': LucideIcons.folderTree},
    {'id': 'architecture', 'label': 'Architecture', 'icon': LucideIcons.boxes},
    {'id': 'graph', 'label': 'Ontology Graph', 'icon': LucideIcons.gitFork},
    {'id': 'feed', 'label': 'Ingestion Feed', 'icon': LucideIcons.radio},
  ];

  @override
  Widget build(BuildContext context) {
    final width = widget.open ? 264.0 : 72.0;
    final isDark = widget.palette.isDark;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: const Cubic(0.4, 0.0, 0.2, 1.0),
      width: width,
      decoration: BoxDecoration(
        gradient: widget.palette.sidebarGradient,
        border: Border(right: BorderSide(color: widget.palette.div)),
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          ClipRect(
            child: SizedBox(
              width: width,
              height: double.infinity,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 180),
                switchInCurve: Curves.easeIn,
                switchOutCurve: Curves.easeOut,
                layoutBuilder: (currentChild, previousChildren) {
                  return Stack(
                    alignment: Alignment.topLeft,
                    children: [
                      ...previousChildren,
                      ?currentChild,
                    ],
                  );
                },
                child: widget.open
                    ? KeyedSubtree(
                        key: const ValueKey('expanded'),
                        child: OverflowBox(
                          alignment: Alignment.topLeft,
                          minWidth: 264.0,
                          maxWidth: 264.0,
                          child: _buildExpanded(isDark),
                        ),
                      )
                    : KeyedSubtree(
                        key: const ValueKey('narrow'),
                        child: OverflowBox(
                          alignment: Alignment.topLeft,
                          minWidth: 72.0,
                          maxWidth: 72.0,
                          child: _buildNarrow(isDark),
                        ),
                      ),
              ),
            ),
          ),
          Positioned(
            left: widget.open ? 12 : 80,
            bottom: widget.open ? 74 : 16,
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
                      palette: widget.palette,
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
  }

  // ═══════════════════════════════════════════════════════
  //  EXPANDED — 264px width, crisp Swiss-grid alignment
  // ═══════════════════════════════════════════════════════
  Widget _buildExpanded(bool isDark) {
    final isMacOS = !kIsWeb && Platform.isMacOS;

    return SizedBox(
      width: 264.0,
      height: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Header (Logo + Title + Collapse Button)
          Padding(
            padding: EdgeInsets.fromLTRB(12, isMacOS ? 36 : 12, 12, 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: DragToMoveArea(
                    child: _HoverableBrandLogo(
                      palette: widget.palette,
                      isDark: isDark,
                      onTap: () => widget.onViewChange('projects'),
                    ),
                  ),
                ),
                _HoverableIconButton(
                  onTap: widget.onToggle,
                  tooltip: 'Collapse sidebar',
                  palette: widget.palette,
                  icon: LucideIcons.panelLeftClose,
                  size: 16,
                ),
              ],
            ),
          ),

          // 2. Solid Filled "New Query" Button
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 14),
            child: _SolidNewQueryButton(
              palette: widget.palette,
              onTap: widget.onNewQuery,
            ),
          ),

          // 3. Scrollable Navigation List (Pixel-aligned icons, zero lerp artifacts)
          Expanded(
            child: ScrollConfiguration(
              behavior: ScrollConfiguration.of(context).copyWith(
                scrollbars: false,
              ),
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                physics: const BouncingScrollPhysics(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (int i = 0; i < _navItems.length; i++) ...[
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2.0),
                        child: _SidebarNavItem(
                          icon: _navItems[i]['icon'] as IconData,
                          label: _navItems[i]['label'] as String,
                          active: widget.activeView == _navItems[i]['id'],
                          isDark: isDark,
                          palette: widget.palette,
                          onTap: () =>
                              widget.onViewChange(_navItems[i]['id'] as String),
                        ),
                      ),
                      if (i == 0)
                        Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 8),
                          child: Divider(
                            height: 1,
                            thickness: 1,
                            color: widget.palette.div.withValues(alpha: 0.7),
                          ),
                        ),
                    ],
                  ],
                ),
              ),
            ),
          ),

          // 4. Archived Chats Button (Aligned identically to nav buttons)
          _ArchivedChatsButton(
            palette: widget.palette,
            onTap: widget.onOpenArchivedModal,
          ),

          // 5. Elevated Interactive User Profile Footer
          _HoverableUserFooter(
            palette: widget.palette,
            user: widget.user,
            isOpen: _userMenuOpen,
            onTap: () => setState(() => _userMenuOpen = !_userMenuOpen),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════
  //  COLLAPSED — 72px width, centered icons & smooth micro-interactions
  // ═══════════════════════════════════════════════════════
  Widget _buildNarrow(bool isDark) {
    final isMacOS = !kIsWeb && Platform.isMacOS;

    return SizedBox(
      width: 72.0,
      height: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(height: isMacOS ? 36 : 12),
          // Logo
          DragToMoveArea(
            child: MouseRegion(
              cursor: SystemMouseCursors.click,
              child: InkWell(
                onTap: () => widget.onViewChange('projects'),
                borderRadius: BorderRadius.circular(6),
                child: Tooltip(
                  message: 'Projects',
                  child: UnotuskLogo(size: 22, onDark: isDark),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Expand button (36x36, centered)
          _CollapsedIconButton(
            onTap: widget.onToggle,
            tooltip: 'Expand sidebar',
            palette: widget.palette,
            child: Icon(
              LucideIcons.chevronRight,
              size: 14,
              color: widget.palette.textSec,
            ),
          ),

          // Divider
          Container(
            width: 24,
            height: 1,
            color: widget.palette.div,
            margin: const EdgeInsets.symmetric(vertical: 10),
          ),

          // Solid New Query Button in Collapsed Mode (36x36, centered)
          _CollapsedIconButton(
            onTap: widget.onNewQuery,
            tooltip: 'New Query',
            highlight: true,
            palette: widget.palette,
            child: Icon(
              LucideIcons.plus,
              size: 15,
              color: isDark ? const Color(0xFF0A0F20) : Colors.white,
            ),
          ),

          // Divider
          Container(
            width: 24,
            height: 1,
            color: widget.palette.div,
            margin: const EdgeInsets.symmetric(vertical: 10),
          ),

          // Scrollable Nav Items
          Expanded(
            child: ScrollConfiguration(
              behavior: ScrollConfiguration.of(context).copyWith(
                scrollbars: false,
              ),
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Column(
                  children: _navItems.map((item) {
                    final active = widget.activeView == item['id'];
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: _CollapsedNavItem(
                        icon: item['icon'] as IconData,
                        label: item['label'] as String,
                        active: active,
                        palette: widget.palette,
                        onTap: () => widget.onViewChange(item['id'] as String),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),
          ),

          // Archived Chats Button in Collapsed Mode
          _CollapsedIconButton(
            onTap: widget.onOpenArchivedModal,
            tooltip: 'Archived chats',
            palette: widget.palette,
            child: Icon(
              LucideIcons.archive,
              size: 15,
              color: widget.palette.textSec,
            ),
          ),

          // Divider
          Container(
            width: 24,
            height: 1,
            color: widget.palette.div,
            margin: const EdgeInsets.symmetric(vertical: 10),
          ),

          // User Monogram Avatar
          _HoverableCollapsedUserAvatar(
            palette: widget.palette,
            user: widget.user,
            isOpen: _userMenuOpen,
            onTap: () => setState(() => _userMenuOpen = !_userMenuOpen),
          ),

          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Interactive Brand Header Logo with Hover Highlight
// ─────────────────────────────────────────────────────────
class _HoverableBrandLogo extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final VoidCallback onTap;

  const _HoverableBrandLogo({
    required this.palette,
    required this.isDark,
    required this.onTap,
  });

  @override
  State<_HoverableBrandLogo> createState() => _HoverableBrandLogoState();
}

class _HoverableBrandLogoState extends State<_HoverableBrandLogo> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final hoverBase =
        widget.isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          decoration: BoxDecoration(
            color: hoverBase.withValues(alpha: _hovered ? 0.05 : 0.0),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedScale(
                scale: _hovered ? 1.05 : 1.0,
                duration: const Duration(milliseconds: 160),
                curve: Curves.easeOutCubic,
                child: UnotuskLogo(size: 22, onDark: widget.isDark),
              ),
              const SizedBox(width: 9),
              Text(
                'Unotusk',
                style: UnoTypography.brandSerif(
                  palette: widget.palette,
                  fontSize: 17,
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
//  Hoverable Icon Button (Collapse & Action Icons)
// ─────────────────────────────────────────────────────────
class _HoverableIconButton extends StatefulWidget {
  final VoidCallback onTap;
  final String? tooltip;
  final UnoPalette palette;
  final IconData icon;
  final double size;

  const _HoverableIconButton({
    required this.onTap,
    this.tooltip,
    required this.palette,
    required this.icon,
    this.size = 16,
  });

  @override
  State<_HoverableIconButton> createState() => _HoverableIconButtonState();
}

class _HoverableIconButtonState extends State<_HoverableIconButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final hoverBase =
        p.isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    final button = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: hoverBase.withValues(alpha: _hovered ? 0.07 : 0.0),
            borderRadius: BorderRadius.circular(7),
          ),
          alignment: Alignment.center,
          child: Icon(
            widget.icon,
            size: widget.size,
            color: _hovered ? p.text : p.textSec,
          ),
        ),
      ),
    );

    if (widget.tooltip != null) {
      return Tooltip(message: widget.tooltip!, child: button);
    }
    return button;
  }
}

// ─────────────────────────────────────────────────────────
//  Solid Filled "New Query" Button with Smooth Hover Dynamics
// ─────────────────────────────────────────────────────────
class _SolidNewQueryButton extends StatefulWidget {
  final UnoPalette palette;
  final VoidCallback onTap;

  const _SolidNewQueryButton({
    required this.palette,
    required this.onTap,
  });

  @override
  State<_SolidNewQueryButton> createState() => _SolidNewQueryButtonState();
}

class _SolidNewQueryButtonState extends State<_SolidNewQueryButton> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.palette.isDark;
    final accent = widget.palette.accent;
    final fgColor = isDark ? const Color(0xFF0A0F20) : Colors.white;
    final bgColor = _pressed
        ? Color.lerp(accent, Colors.black, 0.12)!
        : _hovered
            ? Color.lerp(accent, isDark ? Colors.white : Colors.white, 0.08)!
            : accent;

    return MouseRegion(
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
        child: AnimatedScale(
          scale: _pressed ? 0.985 : 1.0,
          duration: const Duration(milliseconds: 100),
          curve: Curves.easeOutCubic,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            height: 40,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(10),
              boxShadow: [
                BoxShadow(
                  color: accent.withValues(alpha: _hovered ? 0.34 : 0.18),
                  blurRadius: _hovered ? 12 : 6,
                  offset: Offset(0, _hovered ? 3 : 1.5),
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                AnimatedScale(
                  scale: _hovered ? 1.1 : 1.0,
                  duration: const Duration(milliseconds: 180),
                  curve: Curves.easeOutCubic,
                  child: Icon(
                    LucideIcons.plus,
                    size: 16,
                    color: fgColor,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'New Query',
                  style: UnoTypography.body(
                    color: fgColor,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
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

// ─────────────────────────────────────────────────────────
//  Sidebar Navigation Item — Pixel-Aligned & Smooth Transitions
// ─────────────────────────────────────────────────────────
class _SidebarNavItem extends StatefulWidget {
  final IconData icon;
  final String label;
  final bool active;
  final bool isDark;
  final UnoPalette palette;
  final VoidCallback onTap;

  const _SidebarNavItem({
    required this.icon,
    required this.label,
    required this.active,
    required this.isDark,
    required this.palette,
    required this.onTap,
  });

  @override
  State<_SidebarNavItem> createState() => _SidebarNavItemState();
}

class _SidebarNavItemState extends State<_SidebarNavItem> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final active = widget.active;
    final p = widget.palette;

    // Avoid Colors.transparent (0x00000000) lerping artifacts by matching RGB base
    final hoverBase =
        isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    final bgColor = active
        ? (isDark ? const Color(0xFF1E2336) : const Color(0xFFFFFFFF))
        : hoverBase.withValues(alpha: _hovered ? 0.055 : 0.0);

    final borderColor = active
        ? (isDark
            ? const Color(0xFFCBC1B4).withValues(alpha: 0.28)
            : const Color(0xFFE4DFD6))
        : (isDark
            ? const Color(0xFFCBC1B4).withValues(alpha: 0.0)
            : const Color(0xFFE4DFD6).withValues(alpha: 0.0));

    final iconColor = active
        ? (isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20))
        : (_hovered ? p.text : p.textSec);

    final textColor = active ? p.text : (_hovered ? p.text : p.textSec);

    return MouseRegion(
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
          scale: _pressed ? 0.985 : 1.0,
          duration: const Duration(milliseconds: 100),
          curve: Curves.easeOutCubic,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 170),
            curve: Curves.easeOutCubic,
            height: 38,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(9),
              border: Border.all(color: borderColor, width: 1),
              boxShadow: active
                  ? [
                      BoxShadow(
                        color: const Color(0xFF0A0F20)
                            .withValues(alpha: isDark ? 0.22 : 0.05),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ]
                  : const [],
            ),
            child: Stack(
              alignment: Alignment.centerLeft,
              children: [
                // Left edge active pill — positioned independently so icons never shift
                Positioned(
                  left: 0,
                  top: 0,
                  bottom: 0,
                  child: Center(
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      curve: Curves.easeOutCubic,
                      width: active ? 3.0 : 0.0,
                      height: active ? 18.0 : 0.0,
                      decoration: BoxDecoration(
                        color: p.accent,
                        borderRadius: const BorderRadius.horizontal(
                          right: Radius.circular(3),
                        ),
                      ),
                    ),
                  ),
                ),
                // Uniformly aligned icon + label row
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 20,
                        height: 20,
                        child: Center(
                          child: Icon(
                            widget.icon,
                            size: 16,
                            color: iconColor,
                          ),
                        ),
                      ),
                      const SizedBox(width: 11),
                      Expanded(
                        child: AnimatedDefaultTextStyle(
                          duration: const Duration(milliseconds: 170),
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
                    ],
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

// ─────────────────────────────────────────────────────────
//  Archived Chats Action Button — Exact Same Alignment Grid
// ─────────────────────────────────────────────────────────
class _ArchivedChatsButton extends StatefulWidget {
  final UnoPalette palette;
  final VoidCallback onTap;

  const _ArchivedChatsButton({
    required this.palette,
    required this.onTap,
  });

  @override
  State<_ArchivedChatsButton> createState() => _ArchivedChatsButtonState();
}

class _ArchivedChatsButtonState extends State<_ArchivedChatsButton> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final hoverBase =
        p.isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 6),
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
            scale: _pressed ? 0.985 : 1.0,
            duration: const Duration(milliseconds: 100),
            curve: Curves.easeOutCubic,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              curve: Curves.easeOutCubic,
              height: 38,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: hoverBase.withValues(alpha: _hovered ? 0.055 : 0.0),
                border: Border.all(
                  color: hoverBase.withValues(alpha: 0.0),
                  width: 1,
                ),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Row(
                children: [
                  SizedBox(
                    width: 20,
                    height: 20,
                    child: Center(
                      child: Icon(
                        LucideIcons.archive,
                        size: 16,
                        color: _hovered ? p.text : p.textSec,
                      ),
                    ),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Text(
                      'Archived chats',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: UnoTypography.body(
                        color: _hovered ? p.text : p.textSec,
                        fontSize: 13.5,
                        fontWeight:
                            _hovered ? FontWeight.w500 : FontWeight.w400,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Professional Elevated User Profile Footer Card
// ─────────────────────────────────────────────────────────
class _HoverableUserFooter extends StatefulWidget {
  final UnoPalette palette;
  final UserModel user;
  final bool isOpen;
  final VoidCallback onTap;

  const _HoverableUserFooter({
    required this.palette,
    required this.user,
    required this.isOpen,
    required this.onTap,
  });

  @override
  State<_HoverableUserFooter> createState() => _HoverableUserFooterState();
}

class _HoverableUserFooterState extends State<_HoverableUserFooter> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = p.isDark;
    final isActive = widget.isOpen || _hovered;

    final displayName =
        widget.user.name.isNotEmpty ? widget.user.name : 'User';
    final subtitle =
        widget.user.org.isNotEmpty ? widget.user.org : widget.user.email;
    final initials = _computeUserInitials(displayName);

    final cardBg = isDark
        ? (isActive ? const Color(0xFF232940) : const Color(0xFF1E2336))
        : (isActive ? const Color(0xFFFFFFFF) : const Color(0xFFFAF8F4));

    final cardBorder = isDark
        ? (isActive
            ? const Color(0xFFCBC1B4).withValues(alpha: 0.38)
            : const Color(0xFF2E313C))
        : (isActive ? const Color(0xFFCBC1B4) : const Color(0xFFE4DFD6));

    final avatarBg =
        isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20);
    final avatarFg =
        isDark ? const Color(0xFF0A0F20) : const Color(0xFFCBC1B4);

    final chevronPillBase =
        isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: p.div.withValues(alpha: 0.75)),
        ),
      ),
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
            scale: _pressed ? 0.98 : 1.0,
            duration: const Duration(milliseconds: 110),
            curve: Curves.easeOutCubic,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOutCubic,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(11),
                border: Border.all(color: cardBorder, width: 1),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF0A0F20).withValues(
                      alpha: isDark
                          ? (isActive ? 0.34 : 0.18)
                          : (isActive ? 0.09 : 0.04),
                    ),
                    blurRadius: isActive ? 14 : 6,
                    offset: Offset(0, isActive ? 4 : 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  // Squircle Monogram Avatar + Online Status Dot
                  AnimatedScale(
                    scale: isActive ? 1.04 : 1.0,
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOutCubic,
                    child: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Container(
                          width: 34,
                          height: 34,
                          decoration: BoxDecoration(
                            color: avatarBg,
                            borderRadius: BorderRadius.circular(9),
                            boxShadow: [
                              BoxShadow(
                                color: avatarBg.withValues(alpha: 0.22),
                                blurRadius: 6,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            initials,
                            style: UnoTypography.body(
                              color: avatarFg,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        Positioned(
                          right: -2,
                          bottom: -2,
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: const Color(0xFF22C55E),
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: cardBg,
                                width: 1.8,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(width: 11),

                  // Name & Organization (clean sans-serif)
                  Expanded(
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

                  const SizedBox(width: 6),

                  // Interactive Dual-Chevron Indicator
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOutCubic,
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: chevronPillBase.withValues(
                          alpha: isActive ? 0.08 : 0.0),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    alignment: Alignment.center,
                    child: AnimatedRotation(
                      turns: widget.isOpen ? 0.5 : 0.0,
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeOutCubic,
                      child: Icon(
                        LucideIcons.chevronsUpDown,
                        size: 13.5,
                        color: isActive ? p.text : p.textSec,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Collapsed Mode: Hoverable Icon Button (36x36)
// ─────────────────────────────────────────────────────────
class _CollapsedIconButton extends StatefulWidget {
  final VoidCallback onTap;
  final Widget child;
  final String? tooltip;
  final bool highlight;
  final UnoPalette palette;

  const _CollapsedIconButton({
    required this.onTap,
    required this.child,
    this.tooltip,
    this.highlight = false,
    required this.palette,
  });

  @override
  State<_CollapsedIconButton> createState() => _CollapsedIconButtonState();
}

class _CollapsedIconButtonState extends State<_CollapsedIconButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final highlight = widget.highlight;

    final bgColor = highlight
        ? (_hovered ? Color.lerp(p.accent, Colors.white, 0.08)! : p.accent)
        : (_hovered ? p.bgElevated : p.bgElevated.withValues(alpha: 0.7));

    final borderColor = highlight
        ? p.accent
        : (_hovered ? p.textSec.withValues(alpha: 0.3) : p.div);

    final button = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 170),
          curve: Curves.easeOutCubic,
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: bgColor,
            border: Border.all(color: borderColor),
            borderRadius: BorderRadius.circular(10),
            boxShadow: highlight
                ? [
                    BoxShadow(
                      color: p.accent.withValues(alpha: _hovered ? 0.38 : 0.20),
                      blurRadius: _hovered ? 10 : 5,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : const [],
          ),
          child: Center(
            child: AnimatedScale(
              scale: _hovered ? 1.08 : 1.0,
              duration: const Duration(milliseconds: 170),
              curve: Curves.easeOutCubic,
              child: widget.child,
            ),
          ),
        ),
      ),
    );

    if (widget.tooltip != null) {
      return Tooltip(
        message: widget.tooltip!,
        preferBelow: false,
        child: button,
      );
    }
    return button;
  }
}

// ─────────────────────────────────────────────────────────
//  Collapsed Mode: Nav Item (36x36)
// ─────────────────────────────────────────────────────────
class _CollapsedNavItem extends StatefulWidget {
  final IconData icon;
  final String label;
  final bool active;
  final UnoPalette palette;
  final VoidCallback onTap;

  const _CollapsedNavItem({
    required this.icon,
    required this.label,
    required this.active,
    required this.palette,
    required this.onTap,
  });

  @override
  State<_CollapsedNavItem> createState() => _CollapsedNavItemState();
}

class _CollapsedNavItemState extends State<_CollapsedNavItem> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final active = widget.active;
    final hoverBase =
        p.isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    final bgColor = active
        ? (p.isDark ? const Color(0xFF1E2336) : const Color(0xFFFFFFFF))
        : hoverBase.withValues(alpha: _hovered ? 0.06 : 0.0);

    final borderColor = active
        ? (p.isDark
            ? const Color(0xFFCBC1B4).withValues(alpha: 0.35)
            : const Color(0xFFE4DFD6))
        : (p.isDark
            ? const Color(0xFFCBC1B4).withValues(alpha: 0.0)
            : const Color(0xFFE4DFD6).withValues(alpha: 0.0));

    final iconColor = active
        ? (p.isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20))
        : (_hovered ? p.text : p.textSec);

    return Tooltip(
      message: widget.label,
      preferBelow: false,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 170),
            curve: Curves.easeOutCubic,
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: bgColor,
              border: Border.all(color: borderColor),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(
              child: AnimatedScale(
                scale: _hovered ? 1.08 : 1.0,
                duration: const Duration(milliseconds: 170),
                curve: Curves.easeOutCubic,
                child: Icon(
                  widget.icon,
                  size: 16,
                  color: iconColor,
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
//  Collapsed Mode: Hoverable Squircle User Avatar (36x36)
// ─────────────────────────────────────────────────────────
class _HoverableCollapsedUserAvatar extends StatefulWidget {
  final UnoPalette palette;
  final UserModel user;
  final bool isOpen;
  final VoidCallback onTap;

  const _HoverableCollapsedUserAvatar({
    required this.palette,
    required this.user,
    required this.isOpen,
    required this.onTap,
  });

  @override
  State<_HoverableCollapsedUserAvatar> createState() =>
      _HoverableCollapsedUserAvatarState();
}

class _HoverableCollapsedUserAvatarState
    extends State<_HoverableCollapsedUserAvatar> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = p.isDark;
    final displayName =
        widget.user.name.isNotEmpty ? widget.user.name : 'User';
    final initials = _computeUserInitials(displayName);
    final avatarBg =
        isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20);
    final avatarFg =
        isDark ? const Color(0xFF0A0F20) : const Color(0xFFCBC1B4);

    return Tooltip(
      message: displayName,
      preferBelow: false,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedScale(
            scale: _hovered ? 1.07 : 1.0,
            duration: const Duration(milliseconds: 170),
            curve: Curves.easeOutCubic,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 170),
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: avatarBg,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: widget.isOpen
                          ? p.text
                          : (_hovered
                              ? p.textSec.withValues(alpha: 0.6)
                              : p.div.withValues(alpha: 0.4)),
                      width: widget.isOpen ? 1.8 : 1.0,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: avatarBg.withValues(
                            alpha: _hovered ? 0.35 : 0.18),
                        blurRadius: _hovered ? 10 : 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    initials,
                    style: UnoTypography.body(
                      color: avatarFg,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Positioned(
                  right: -2,
                  bottom: -2,
                  child: Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: const Color(0xFF22C55E),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: p.bgSurface,
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
    );
  }
}
