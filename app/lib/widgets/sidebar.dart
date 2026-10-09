import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:window_manager/window_manager.dart';
import '../models/models.dart';
import '../services/api_service.dart';
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
  List<RecentChat> _recentChats = [];

  @override
  void initState() {
    super.initState();
    _recentChats = List.of(ApiService.recentChatsNotifier.value.isNotEmpty
        ? ApiService.recentChatsNotifier.value
        : ApiService.recordedChats);
    ApiService.recentChatsNotifier.addListener(_onRecentChatsChanged);
    _loadRecentChats();
  }

  void _onRecentChatsChanged() {
    if (mounted) {
      setState(() {
        _recentChats = List.of(ApiService.recentChatsNotifier.value);
      });
    }
  }

  @override
  void dispose() {
    ApiService.recentChatsNotifier.removeListener(_onRecentChatsChanged);
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant UnoSidebar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.projectId != widget.projectId) {
      _loadRecentChats();
    }
  }

  void _loadRecentChats() async {
    try {
      final chats = await ApiService.fetchRecentChats(projectId: widget.projectId);
      if (mounted) {
        setState(() {
          _recentChats = chats;
        });
      }
    } catch (_) {
      debugPrint('[UnoSidebar] Failed to load recent chats');
    }
  }

  void _handleChatAction(String action, RecentChat chat) {
    switch (action) {
      case 'pin':
        ApiService.togglePinRecentChat(chat.id);
        break;
      case 'rename':
        _showRenameDialog(chat);
        break;
      case 'move':
        _showMoveToProjectDialog(chat);
        break;
      case 'archive':
        ApiService.removeRecentChat(chat.id);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('"${chat.title}" archived', style: const TextStyle(color: Colors.white)),
            backgroundColor: widget.palette.bgElevated,
            behavior: SnackBarBehavior.floating,
            action: SnackBarAction(
              label: 'Undo',
              textColor: widget.palette.accent,
              onPressed: () {
                ApiService.recordRecentChat(chat);
              },
            ),
          ),
        );
        break;
      case 'delete':
        _showDeleteConfirmation(chat);
        break;
    }
  }

  void _showRenameDialog(RecentChat chat) {
    final controller = TextEditingController(text: chat.title);
    final p = widget.palette;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: p.bgSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: p.div),
        ),
        title: Text(
          'Rename Chat',
          style: UnoTypography.body(
            color: p.text,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: UnoTypography.body(color: p.text, fontSize: 14),
          decoration: InputDecoration(
            hintText: 'Enter new name',
            hintStyle: UnoTypography.body(color: p.textSec, fontSize: 14),
            filled: true,
            fillColor: p.bgBase,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: p.div),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: p.div),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide(color: p.accent, width: 1.5),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          ),
          onSubmitted: (val) {
            if (val.trim().isNotEmpty) {
              ApiService.renameRecentChat(chat.id, val.trim());
            }
            Navigator.of(ctx).pop();
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel', style: UnoTypography.body(color: p.textSec, fontSize: 13)),
          ),
          TextButton(
            onPressed: () {
              final val = controller.text.trim();
              if (val.isNotEmpty) {
                ApiService.renameRecentChat(chat.id, val);
              }
              Navigator.of(ctx).pop();
            },
            child: Text('Save', style: UnoTypography.body(color: p.accent, fontSize: 13, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  void _showMoveToProjectDialog(RecentChat chat) {
    final projects = ApiService.cachedProjects;
    final p = widget.palette;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: p.bgSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: p.div),
        ),
        title: Text(
          'Move to Project',
          style: UnoTypography.body(
            color: p.text,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: SizedBox(
          width: 280,
          child: projects.isEmpty
              ? Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Text(
                    'No projects available.',
                    style: UnoTypography.body(color: p.textSec, fontSize: 13),
                  ),
                )
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: projects.map((proj) {
                    final isSelected = chat.projectId == proj.id;
                    return InkWell(
                      onTap: () {
                        setState(() => chat.projectId = proj.id);
                        Navigator.of(ctx).pop();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Moved "${chat.title}" to ${proj.name}', style: const TextStyle(color: Colors.white)),
                            backgroundColor: p.bgElevated,
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      },
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: isSelected ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.folder_outlined,
                              size: 16,
                              color: isSelected ? p.accent : p.textSec,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                proj.name,
                                style: UnoTypography.body(
                                  color: isSelected ? p.accent : p.text,
                                  fontSize: 13,
                                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                                ),
                              ),
                            ),
                            if (isSelected)
                              Icon(Icons.check, size: 16, color: p.accent),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel', style: UnoTypography.body(color: p.textSec, fontSize: 13)),
          ),
        ],
      ),
    );
  }

  void _showDeleteConfirmation(RecentChat chat) {
    final p = widget.palette;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: p.bgSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: p.div),
        ),
        title: Text(
          'Delete Chat',
          style: UnoTypography.body(
            color: p.text,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: Text(
          'Are you sure you want to delete "${chat.title}"? This action cannot be undone.',
          style: UnoTypography.body(color: p.textSec, fontSize: 13),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel', style: UnoTypography.body(color: p.textSec, fontSize: 13)),
          ),
          TextButton(
            onPressed: () {
              ApiService.removeRecentChat(chat.id);
              Navigator.of(ctx).pop();
            },
            child: Text(
              'Delete',
              style: UnoTypography.body(
                color: const Color(0xFFEF5350),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Nav items: Projects and workspace tabs
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
    // Web: Pc=264 for open, Ec=72 for closed
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
  //  EXPANDED — web: width Pc(264), padding "14px 0"
  // ═══════════════════════════════════════════════════════
  Widget _buildExpanded(bool isDark) {
    return SizedBox(
      width: 264.0,
      height: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
        // Brand Header — web: padding "0 14px", marginBottom "12px"
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: DragToMoveArea(
                  child: InkWell(
                    onTap: () => widget.onViewChange('projects'),
                    borderRadius: BorderRadius.circular(6),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                      child: Row(
                        children: [
                          UnotuskLogo(size: 22, onDark: isDark),
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
                ),
              ),
              // Collapse button
              InkWell(
                onTap: widget.onToggle,
                borderRadius: BorderRadius.circular(6),
                child: Container(
                  width: 28,
                  height: 28,
                  alignment: Alignment.center,
                  child: Icon(
                    LucideIcons.panelLeftClose,
                    size: 16,
                    color: widget.palette.textSec,
                  ),
                ),
              ),
            ],
          ),
        ),

        // New Query Button — warm subtle dark background, terracotta border, terracotta text
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
          child: InkWell(
            onTap: widget.onNewQuery,
            borderRadius: BorderRadius.circular(8),
            child: Container(
              height: 38,
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF261D1A) : const Color(0xFFFBF1EE),
                border: Border.all(
                  color: widget.palette.accent.withValues(alpha: isDark ? 0.35 : 0.4),
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(LucideIcons.plus,
                      size: 15, color: widget.palette.accent, weight: 2.5),
                  const SizedBox(width: 7),
                  Text(
                    'New Query',
                    style: UnoTypography.body(
                      color: widget.palette.accent,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        // ── Scrollable Navigation & Recent Chats ──
        Expanded(
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Nav items — rounded pills, highlighted when active
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
                  child: Column(
                    children: _navItems.map((item) {
                      final active = widget.activeView == item['id'];
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 1.5),
                        child: InkWell(
                          onTap: () => widget.onViewChange(item['id']),
                          borderRadius: BorderRadius.circular(8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 7,
                            ),
                            decoration: BoxDecoration(
                              color: active
                                  ? (isDark
                                      ? const Color(0xFF2B2521)
                                      : widget.palette.bgElevated)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  item['icon'] as IconData,
                                  size: 15,
                                  color: active
                                      ? (isDark ? Colors.white : widget.palette.text)
                                      : widget.palette.textSec,
                                ),
                                const SizedBox(width: 11),
                                Text(
                                  item['label'] as String,
                                  style: UnoTypography.body(
                                    color: active
                                        ? (isDark ? Colors.white : widget.palette.text)
                                        : widget.palette.textSec,
                                    fontSize: 13,
                                    fontWeight:
                                        active ? FontWeight.w600 : FontWeight.w400,
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

                // Divider
                Container(
                  height: 1,
                  color: widget.palette.div,
                  margin: const EdgeInsets.symmetric(vertical: 6),
                ),

                // Recent Chats — with zero vertical clipping or overflow
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(top: 2, bottom: 4),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'RECENT',
                              style: UnoTypography.mono(
                                color: widget.palette.textSec,
                                fontSize: 10,
                                letterSpacing: 0.6,
                              ),
                            ),
                            if (_recentChats.isNotEmpty)
                              Text(
                                '${_recentChats.length}',
                                style: UnoTypography.mono(
                                  color: widget.palette.textSec.withValues(alpha: 0.6),
                                  fontSize: 9.5,
                                ),
                              ),
                          ],
                        ),
                      ),
                      if (_recentChats.isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Text(
                            'No recent conversations',
                            style: UnoTypography.body(
                              color: widget.palette.textSec.withValues(alpha: 0.6),
                              fontSize: 12,
                            ),
                          ),
                        )
                      else
                        ..._recentChats.map((chat) {
                          return _RecentChatTile(
                            chat: chat,
                            palette: widget.palette,
                            isSelected: widget.activeConversationId == chat.id,
                            onTap: () => widget.onLoadRecentChat(chat.id),
                            onAction: (action) => _handleChatAction(action, chat),
                          );
                        }),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),

        // Archived Chats — web: padding "4px 12px 6px"
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 6),
          child: InkWell(
            onTap: widget.onOpenArchivedModal,
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  Icon(
                    LucideIcons.archive,
                    size: 15,
                    color: widget.palette.accent,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Archived chats',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        // User Footer — web: padding "8px 12px 4px", borderTop
        Container(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          decoration: BoxDecoration(
            border: Border(top: BorderSide(color: widget.palette.div)),
          ),
          child: InkWell(
            onTap: () => setState(() => _userMenuOpen = !_userMenuOpen),
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  // web: 30×30, borderRadius 50%, accent bg
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: widget.palette.accent,
                      shape: BoxShape.circle,
                    ),
                    child: const Center(
                      child: Icon(LucideIcons.user,
                          size: 14, color: Colors.white),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // web: Geist 13px, fontWeight 600
                        Text(
                          widget.user.name.isNotEmpty
                              ? widget.user.name
                              : 'User',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.body(
                            color: widget.palette.text,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (widget.user.org.isNotEmpty)
                          // web: Geist Mono 10px
                          Text(
                            widget.user.org,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: UnoTypography.mono(
                              color: widget.palette.textSec,
                              fontSize: 10,
                            ),
                          ),
                      ],
                    ),
                  ),
                  Icon(
                    _userMenuOpen
                        ? LucideIcons.chevronUp
                        : LucideIcons.chevronDown,
                    size: 13,
                    color: widget.palette.textSec,
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
      ],
    ),
  );
}

  // ═══════════════════════════════════════════════════════
  //  COLLAPSED — web: width Ec(72), padding "14px 0 16px"
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
          child: InkWell(
            onTap: () => widget.onViewChange('projects'),
            borderRadius: BorderRadius.circular(6),
            child: Tooltip(
              message: 'Projects',
              child: UnotuskLogo(size: 22, onDark: isDark),
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Expand button — web: tc component, 36×36, borderRadius 10, bgElevated, border div
        _buildCollapsedButton(
          onTap: widget.onToggle,
          tooltip: 'Expand sidebar',
          child: Icon(LucideIcons.chevronRight,
              size: 14, color: widget.palette.textSec),
        ),

        // Divider
        Container(
          width: 24,
          height: 1,
          color: widget.palette.div,
          margin: const EdgeInsets.symmetric(vertical: 10),
        ),

        // New Query — web: tc highlight, accent bg, white icon
        _buildCollapsedButton(
          onTap: widget.onNewQuery,
          tooltip: 'New Query',
          highlight: true,
          child: const Icon(LucideIcons.plus, size: 15, color: Colors.white),
        ),

        // Divider
        Container(
          width: 24,
          height: 1,
          color: widget.palette.div,
          margin: const EdgeInsets.symmetric(vertical: 10),
        ),

        // Nav items — scrollable when window is short
        Expanded(
          child: SingleChildScrollView(
            child: Column(
              children: _navItems.map((item) {
                final active = widget.activeView == item['id'];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: _buildCollapsedNavItem(
                    icon: item['icon'] as IconData,
                    label: item['label'] as String,
                    active: active,
                    onTap: () => widget.onViewChange(item['id']),
                  ),
                );
              }).toList(),
            ),
          ),
        ),

        // Archived chats — web: tc component
        _buildCollapsedButton(
          onTap: widget.onOpenArchivedModal,
          tooltip: 'Archived chats',
          child: Icon(LucideIcons.archive,
              size: 15, color: widget.palette.textSec),
        ),

        // Divider
        Container(
          width: 24,
          height: 1,
          color: widget.palette.div,
          margin: const EdgeInsets.symmetric(vertical: 10),
        ),

        // User avatar — web: mk component, 34×34, borderRadius 50%, accent bg
        InkWell(
          onTap: () => setState(() => _userMenuOpen = !_userMenuOpen),
          borderRadius: BorderRadius.circular(17),
          child: Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: widget.palette.accent,
              shape: BoxShape.circle,
              border: Border.all(
                color: _userMenuOpen
                    ? widget.palette.text
                    : widget.palette.div,
                width: 2,
              ),
            ),
            child: const Center(
              child: Icon(LucideIcons.user, size: 15, color: Colors.white),
            ),
          ),
        ),

        const SizedBox(height: 16),
      ],
    ),
  );
}

  // ─── Collapsed icon button (tc component from web) ─────────
  // web: 36×36, borderRadius 10, bgElevated (or accent if highlight), border div (or accent)
  Widget _buildCollapsedButton({
    required VoidCallback onTap,
    required Widget child,
    String? tooltip,
    bool highlight = false,
  }) {
    final button = InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: highlight
              ? widget.palette.accent
              : widget.palette.bgElevated,
          border: Border.all(
            color: highlight
                ? widget.palette.accent
                : widget.palette.div,
          ),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Center(child: child),
      ),
    );

    if (tooltip != null) {
      return Tooltip(
        message: tooltip,
        preferBelow: false,
        child: button,
      );
    }
    return button;
  }

  // ─── Collapsed nav item (hk component from web) ─────────
  // web: 36×36, borderRadius 10
  // active: bg accent20, border accent60, icon accent, strokeWidth 2.2
  // inactive: bg transparent, border transparent, icon textSec, strokeWidth 1.7
  Widget _buildCollapsedNavItem({
    required IconData icon,
    required String label,
    required bool active,
    required VoidCallback onTap,
  }) {
    return Tooltip(
      message: label,
      preferBelow: false,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: active
                ? widget.palette.accent.withValues(alpha: 0.125) // accent20
                : Colors.transparent,
            border: active
                ? Border.all(
                    color: widget.palette.accent.withValues(alpha: 0.375), // accent60
                  )
                : null,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Center(
            child: Icon(
              icon,
              size: 16,
              color: active
                  ? widget.palette.accent
                  : widget.palette.textSec,
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────
//  Recent Chat Tile with hover 3-dot menu
// ─────────────────────────────────────────────────
class _RecentChatTile extends StatefulWidget {
  final RecentChat chat;
  final UnoPalette palette;
  final VoidCallback onTap;
  final Function(String) onAction;
  final bool isSelected;

  const _RecentChatTile({
    required this.chat,
    required this.palette,
    required this.onTap,
    required this.onAction,
    this.isSelected = false,
  });

  @override
  State<_RecentChatTile> createState() => _RecentChatTileState();
}

class _RecentChatTileState extends State<_RecentChatTile> {
  bool _hovered = false;
  bool _menuOpen = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final chat = widget.chat;

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) {
        if (!_menuOpen) setState(() => _hovered = false);
      },
      child: Container(
        decoration: BoxDecoration(
          color: widget.isSelected
              ? p.accent.withValues(alpha: 0.12)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: InkWell(
          onTap: widget.onTap,
          borderRadius: BorderRadius.circular(6),
          hoverColor: p.bgElevated,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
            child: Row(
              children: [
                // Pin indicator
                if (chat.isPinned)
                  Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Icon(
                      Icons.push_pin,
                      size: 12,
                      color: p.accent,
                    ),
                  ),
                Expanded(
                  child: Text(
                    chat.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: UnoTypography.body(
                      color: widget.isSelected ? p.accent : p.text,
                      fontSize: 12,
                      fontWeight: (chat.isPinned || widget.isSelected)
                          ? FontWeight.w600
                          : FontWeight.w500,
                    ),
                  ),
                ),
              // 3-dot menu — visible on hover or when menu is open
              if (_hovered || _menuOpen)
                SizedBox(
                  width: 22,
                  height: 22,
                  child: PopupMenuButton<String>(
                    padding: EdgeInsets.zero,
                    iconSize: 16,
                    icon: Icon(
                      Icons.more_vert,
                      size: 16,
                      color: p.textSec,
                    ),
                    tooltip: '',
                    color: p.bgSurface,
                    surfaceTintColor: Colors.transparent,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                      side: BorderSide(color: p.div),
                    ),
                    onOpened: () => setState(() => _menuOpen = true),
                    onCanceled: () => setState(() {
                      _menuOpen = false;
                      _hovered = false;
                    }),
                    onSelected: (value) {
                      setState(() {
                        _menuOpen = false;
                        _hovered = false;
                      });
                      widget.onAction(value);
                    },
                    itemBuilder: (_) => [
                      _menuItem(
                        chat.isPinned ? Icons.push_pin : Icons.push_pin_outlined,
                        chat.isPinned ? 'Unpin' : 'Pin',
                        'pin',
                        p,
                      ),
                      _menuItem(Icons.edit_outlined, 'Rename', 'rename', p),
                      _menuItem(Icons.drive_file_move_outlined, 'Move to Project', 'move', p),
                      _menuItem(Icons.archive_outlined, 'Archive', 'archive', p),
                      _menuItem(Icons.delete_outline, 'Delete', 'delete', p,
                          color: const Color(0xFFEF5350)),
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

  PopupMenuItem<String> _menuItem(
    IconData icon,
    String label,
    String value,
    UnoPalette p, {
    Color? color,
  }) {
    final c = color ?? p.text;
    return PopupMenuItem<String>(
      value: value,
      height: 36,
      child: Row(
        children: [
          Icon(icon, size: 16, color: c),
          const SizedBox(width: 10),
          Text(
            label,
            style: UnoTypography.body(
              color: c,
              fontSize: 13,
              fontWeight: FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}
