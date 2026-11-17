import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:window_manager/window_manager.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import 'unotusk_logo.dart';
import 'user_menu_popup.dart';

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

  // Nav items: Projects and 9 workspace tabs
  final List<Map<String, dynamic>> _navItems = const [
    {'id': 'projects', 'label': 'Projects', 'icon': LucideIcons.folder},
    {'id': 'overview', 'label': 'Overview', 'icon': LucideIcons.layoutDashboard},
    {'id': 'chat', 'label': 'Ask AI', 'icon': LucideIcons.sparkles},
    {'id': 'files', 'label': 'Files', 'icon': LucideIcons.folderTree},
    {'id': 'architecture', 'label': 'Architecture', 'icon': LucideIcons.boxes},
    {'id': 'discoveries', 'label': 'Discoveries', 'icon': LucideIcons.radar},
    {'id': 'knowledge', 'label': 'Knowledge', 'icon': LucideIcons.bookOpen},
    {'id': 'spec-history', 'label': 'Spec History', 'icon': LucideIcons.fileText},
    {'id': 'graph', 'label': 'Ontology Graph', 'icon': LucideIcons.gitFork},
    {'id': 'feed', 'label': 'Ingestion Feed', 'icon': LucideIcons.radio},
  ];

  @override
  Widget build(BuildContext context) {
    final width = widget.open ? 264.0 : 72.0;
    final isDark = widget.palette.bgBase == const Color(0xFF181816);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: const Cubic(0.4, 0.0, 0.2, 1.0),
      width: width,
      decoration: BoxDecoration(
        color: widget.palette.bgSurface,
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
          if (_userMenuOpen)
            Positioned(
              left: widget.open ? 12 : 80,
              bottom: widget.open ? 64 : 16,
              child: UserMenuPopup(
                palette: widget.palette,
                user: widget.user,
                onNavigateSettings: widget.onNavigateSettings,
                onLogOut: widget.onLogOut,
                onClose: () => setState(() => _userMenuOpen = false),
              ),
            ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════
  //  EXPANDED — 264px width, professional padding & animations
  // ═══════════════════════════════════════════════════════
  Widget _buildExpanded(bool isDark) {
    return SizedBox(
      width: 264.0,
      height: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Header (Logo + Title + Collapse Button)
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
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
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: _SolidNewQueryButton(
              palette: widget.palette,
              onTap: widget.onNewQuery,
            ),
          ),

          // 3. Scrollable Navigation List (Clean spacing, buttery smooth hover & click feedback)
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
              physics: const BouncingScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: _navItems.map((item) {
                  final active = widget.activeView == item['id'];
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2.0),
                    child: _SidebarNavItem(
                      icon: item['icon'] as IconData,
                      label: item['label'] as String,
                      active: active,
                      isDark: isDark,
                      palette: widget.palette,
                      onTap: () => widget.onViewChange(item['id']),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),

          // 4. Archived Chats Button
          _ArchivedChatsButton(
            palette: widget.palette,
            onTap: widget.onOpenArchivedModal,
          ),

          // 5. User Profile Footer
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
    return SizedBox(
      width: 72.0,
      height: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const SizedBox(height: 12),
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
            child: const Icon(LucideIcons.plus, size: 15, color: Colors.white),
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
                      onTap: () => widget.onViewChange(item['id']),
                    ),
                  );
                }).toList(),
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

          // User Avatar
          _HoverableCollapsedUserAvatar(
            palette: widget.palette,
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
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          decoration: BoxDecoration(
            color: _hovered
                ? widget.palette.bgElevated.withValues(alpha: 0.6)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(7),
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
    final button = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: _hovered ? p.bgElevated : Colors.transparent,
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
    final accent = widget.palette.accent;
    final bgColor = _pressed
        ? Color.lerp(accent, Colors.black, 0.12)!
        : _hovered
            ? Color.lerp(accent, Colors.white, 0.08)!
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
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          height: 40,
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(9),
            boxShadow: [
              BoxShadow(
                color: accent.withValues(alpha: _hovered ? 0.38 : 0.20),
                blurRadius: _hovered ? 12 : 6,
                offset: Offset(0, _hovered ? 3 : 1.5),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedScale(
                scale: _hovered ? 1.12 : 1.0,
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOutCubic,
                child: const Icon(
                  LucideIcons.plus,
                  size: 16,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'New Query',
                style: UnoTypography.body(
                  color: Colors.white,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
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
//  Sidebar Navigation Item with Indicator & Tactile Micro-Interactions
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

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final active = widget.active;
    final p = widget.palette;

    final bgColor = active
        ? (isDark ? const Color(0xFF282522) : p.bgElevated)
        : (_hovered
            ? (isDark ? const Color(0xFF22201D) : p.bgElevated.withValues(alpha: 0.6))
            : Colors.transparent);

    final borderColor = active
        ? p.accent.withValues(alpha: isDark ? 0.35 : 0.28)
        : (_hovered
            ? p.div.withValues(alpha: isDark ? 0.45 : 0.6)
            : Colors.transparent);

    final iconColor = active
        ? (isDark ? Colors.white : p.accent)
        : (_hovered
            ? (isDark ? const Color(0xFFEDEDEB) : p.text)
            : p.textSec);

    final textColor = active
        ? (isDark ? Colors.white : p.text)
        : (_hovered
            ? (isDark ? const Color(0xFFEDEDEB) : p.text)
            : p.textSec);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 170),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7.5),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: borderColor, width: 1),
          ),
          child: Row(
            children: [
              // Subtle active indicator pill
              AnimatedContainer(
                duration: const Duration(milliseconds: 170),
                curve: Curves.easeOutCubic,
                width: active ? 3.0 : 0.0,
                height: active ? 14.0 : 0.0,
                margin: EdgeInsets.only(right: active ? 7.0 : 0.0),
                decoration: BoxDecoration(
                  color: p.accent,
                  borderRadius: BorderRadius.circular(1.5),
                ),
              ),
              AnimatedSlide(
                duration: const Duration(milliseconds: 170),
                curve: Curves.easeOutCubic,
                offset: Offset(_hovered && !active ? 0.08 : 0.0, 0),
                child: Icon(
                  widget.icon,
                  size: 15.5,
                  color: iconColor,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: AnimatedDefaultTextStyle(
                  duration: const Duration(milliseconds: 170),
                  curve: Curves.easeOutCubic,
                  style: UnoTypography.body(
                    color: textColor,
                    fontSize: 13,
                    fontWeight: active
                        ? FontWeight.w600
                        : (_hovered ? FontWeight.w500 : FontWeight.w400),
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
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────
//  Archived Chats Action Button
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

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 4, 10, 6),
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 170),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _hovered ? p.bgElevated : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(
                  LucideIcons.archive,
                  size: 15,
                  color: _hovered ? p.accent : p.accent.withValues(alpha: 0.8),
                ),
                const SizedBox(width: 10),
                Text(
                  'Archived chats',
                  style: UnoTypography.body(
                    color: _hovered ? p.text : p.textSec,
                    fontSize: 13,
                    fontWeight: _hovered ? FontWeight.w500 : FontWeight.w400,
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
//  Hoverable User Footer with Smooth Chevron Flip
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

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: p.div)),
      ),
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 170),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(
              color:
                  (widget.isOpen || _hovered) ? p.bgElevated : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                AnimatedScale(
                  scale: _hovered ? 1.06 : 1.0,
                  duration: const Duration(milliseconds: 170),
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: p.accent,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: p.accent.withValues(alpha: 0.25),
                          blurRadius: 4,
                          offset: const Offset(0, 1),
                        ),
                      ],
                    ),
                    child: const Center(
                      child:
                          Icon(LucideIcons.user, size: 14, color: Colors.white),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        widget.user.name.isNotEmpty ? widget.user.name : 'User',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: UnoTypography.body(
                          color: p.text,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (widget.user.org.isNotEmpty)
                        Text(
                          widget.user.org,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.mono(
                            color: p.textSec,
                            fontSize: 10,
                          ),
                        ),
                    ],
                  ),
                ),
                AnimatedRotation(
                  turns: widget.isOpen ? 0.5 : 0.0,
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeOutCubic,
                  child: Icon(
                    LucideIcons.chevronDown,
                    size: 14,
                    color: _hovered ? p.text : p.textSec,
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
        : (_hovered ? p.bgElevated.withValues(alpha: 0.6) : p.bgElevated);

    final borderColor = highlight
        ? p.accent
        : (_hovered ? p.textSec.withValues(alpha: 0.3) : p.div);

    final button = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
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
                : null,
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

    final bgColor = active
        ? p.accent.withValues(alpha: 0.16)
        : (_hovered ? p.bgElevated : Colors.transparent);

    final borderColor = active
        ? p.accent.withValues(alpha: 0.45)
        : (_hovered ? p.div.withValues(alpha: 0.5) : Colors.transparent);

    final iconColor = active
        ? p.accent
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
//  Collapsed Mode: Hoverable User Avatar (34x34)
// ─────────────────────────────────────────────────────────
class _HoverableCollapsedUserAvatar extends StatefulWidget {
  final UnoPalette palette;
  final bool isOpen;
  final VoidCallback onTap;

  const _HoverableCollapsedUserAvatar({
    required this.palette,
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

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedScale(
          scale: _hovered ? 1.08 : 1.0,
          duration: const Duration(milliseconds: 170),
          curve: Curves.easeOutCubic,
          child: Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: p.accent,
              shape: BoxShape.circle,
              border: Border.all(
                color: widget.isOpen
                    ? p.text
                    : (_hovered ? p.textSec : p.div),
                width: 2,
              ),
              boxShadow: [
                BoxShadow(
                  color: p.accent.withValues(alpha: _hovered ? 0.35 : 0.15),
                  blurRadius: _hovered ? 8 : 4,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: const Center(
              child: Icon(LucideIcons.user, size: 15, color: Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}
