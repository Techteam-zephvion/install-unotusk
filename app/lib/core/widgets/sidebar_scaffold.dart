import 'package:flutter/material.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import 'unotusk_mark.dart';
import 'notification_panel.dart';
import '../../features/settings/presentation/chatgpt_settings_modal.dart';

class SidebarScaffold extends StatefulWidget {
  final int activeIndex;
  final ValueChanged<int> onIndexChanged;
  final VoidCallback onNewQuery;
  final ValueChanged<String>? onLoadRecentChat;
  final List<String>? recentChats;
  final String? projectName;
  final String? projectBranch;
  final List<({String id, String name})>? availableProjects;
  final ValueChanged<String>? onSelectProject;
  final String userName;
  final String userOrg;
  final VoidCallback onLogOut;
  final Widget child;

  const SidebarScaffold({
    super.key,
    required this.activeIndex,
    required this.onIndexChanged,
    required this.onNewQuery,
    this.onLoadRecentChat,
    this.recentChats,
    this.projectName,
    this.projectBranch,
    this.availableProjects,
    this.onSelectProject,
    this.userName = 'Naren D',
    this.userOrg = 'Unotusk Corp',
    required this.onLogOut,
    required this.child,
  });

  @override
  State<SidebarScaffold> createState() => _SidebarScaffoldState();
}

class _SidebarScaffoldState extends State<SidebarScaffold> {
  bool _isSidebarOpen = true;
  bool _notifOpen = false;
  bool _isDarkTheme = true;

  static const List<Map<String, dynamic>> _navItems = [
    {'title': 'Ask', 'icon': Icons.chat_bubble_outline},
    {'title': 'Spec History', 'icon': Icons.description_outlined},
    {'title': 'Ontology Graph', 'icon': Icons.hub_outlined},
    {'title': 'Ingestion Feed', 'icon': Icons.sensors_outlined},
  ];

  static const List<String> _defaultRecentChats = [
    'Why choose Postgres over Mongo in March?',
    'Which team owns the auth service?',
    'Generate a BDD spec for rate-limiter',
    'FPR trend on auth service this month',
  ];

  void _openSettingsDialog(BuildContext context, {String tab = 'profile'}) {
    showDialog(
      context: context,
      builder: (ctx) => ChatGPTSettingsModal(
        onClose: () => Navigator.of(ctx).pop(),
        defaultTab: tab,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final double sidebarWidth = _isSidebarOpen ? 264.0 : 72.0;

    return Scaffold(
      backgroundColor: AppColors.bgBase,
      body: Stack(
        children: [
          Row(
            children: [
              // ── Collapsible Left Sidebar ──
              AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeInOut,
                width: sidebarWidth,
                decoration: const BoxDecoration(
                  color: AppColors.bgSurface,
                  border: Border(right: BorderSide(color: AppColors.divider, width: 1)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Top Logo & Collapse Toggle
                    Container(
                      height: 56,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        mainAxisAlignment: _isSidebarOpen
                            ? MainAxisAlignment.spaceBetween
                            : MainAxisAlignment.center,
                        children: [
                          Row(
                            children: [
                              const UnotuskMark(size: 26),
                              if (_isSidebarOpen) ...[
                                const SizedBox(width: 10),
                                Text(
                                  'Unotusk',
                                  style: AppTextStyles.logoWordmark,
                                ),
                              ],
                            ],
                          ),
                          if (_isSidebarOpen)
                            InkWell(
                              onTap: () => setState(() => _isSidebarOpen = false),
                              borderRadius: BorderRadius.circular(6),
                              child: const Padding(
                                padding: EdgeInsets.all(4),
                                child: Icon(
                                  Icons.menu_open,
                                  size: 18,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),

                    if (!_isSidebarOpen)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Center(
                          child: InkWell(
                            onTap: () => setState(() => _isSidebarOpen = true),
                            borderRadius: BorderRadius.circular(6),
                            child: const Padding(
                              padding: EdgeInsets.all(6),
                              child: Icon(
                                Icons.menu,
                                size: 18,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ),
                        ),
                      ),

                    const SizedBox(height: 8),

                    // "New Query" button
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      child: InkWell(
                        onTap: widget.onNewQuery,
                        borderRadius: BorderRadius.circular(10),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 12),
                          decoration: BoxDecoration(
                            color: AppColors.accent.withValues(alpha: 0.12),
                            border: Border.all(color: AppColors.accent.withValues(alpha: 0.3)),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            mainAxisAlignment: _isSidebarOpen
                                ? MainAxisAlignment.start
                                : MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.add, size: 16, color: AppColors.accent),
                              if (_isSidebarOpen) ...[
                                const SizedBox(width: 8),
                                Text(
                                  'New Query',
                                  style: AppTextStyles.inter(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.accent,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 12),

                    // Primary Navigation Items
                    ..._navItems.asMap().entries.map((entry) {
                      final index = entry.key;
                      final item = entry.value;
                      final bool isActive = widget.activeIndex == index;

                      return Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                        child: InkWell(
                          onTap: () => widget.onIndexChanged(index),
                          borderRadius: BorderRadius.circular(8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: isActive
                                  ? AppColors.bgElevated
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: isActive ? AppColors.divider : Colors.transparent,
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: _isSidebarOpen
                                  ? MainAxisAlignment.start
                                  : MainAxisAlignment.center,
                              children: [
                                Icon(
                                  item['icon'] as IconData,
                                  size: 16,
                                  color: isActive ? AppColors.accent : AppColors.textSecondary,
                                ),
                                if (_isSidebarOpen) ...[
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      item['title'] as String,
                                      style: AppTextStyles.inter(
                                        fontSize: 13,
                                        fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                                        color: isActive ? AppColors.textPrimary : AppColors.textSecondary,
                                      ),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      );
                    }),

                    if (_isSidebarOpen) ...[
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        child: Divider(color: AppColors.divider, height: 1),
                      ),

                      // "RECENT" header
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
                        child: Text('RECENT', style: AppTextStyles.sectionLabel),
                      ),

                      // Recent query items list
                      Expanded(
                        child: Builder(
                          builder: (context) {
                            final chatList = (widget.recentChats != null && widget.recentChats!.isNotEmpty)
                                ? widget.recentChats!
                                : _defaultRecentChats;
                            return ListView.builder(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              itemCount: chatList.length,
                              itemBuilder: (context, idx) {
                                final chatTitle = chatList[idx];
                                return InkWell(
                                  onTap: () {
                                    widget.onIndexChanged(0); // Switch to Ask Tab
                                    widget.onLoadRecentChat?.call(chatTitle);
                                  },
                                  borderRadius: BorderRadius.circular(6),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
                                    child: Text(
                                      chatTitle,
                                      style: AppTextStyles.inter(
                                        fontSize: 12,
                                        color: AppColors.textSecondary,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                );
                              },
                            );
                          },
                        ),
                      ),
                    ] else
                      const Spacer(),

                    // Bottom User Profile Pill button
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: const BoxDecoration(
                        border: Border(top: BorderSide(color: AppColors.divider)),
                      ),
                      child: PopupMenuButton<String>(
                        color: AppColors.bgElevated,
                        elevation: 12,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: const BorderSide(color: AppColors.divider),
                        ),
                        offset: const Offset(0, -180),
                        onSelected: (value) {
                          if (value == 'settings') {
                            _openSettingsDialog(context, tab: 'general');
                          } else if (value == 'profile') {
                            _openSettingsDialog(context, tab: 'profile');
                          } else if (value == 'logout') {
                            widget.onLogOut();
                          }
                        },
                        itemBuilder: (context) => [
                          PopupMenuItem(
                            value: 'profile',
                            child: Row(
                              children: [
                                const Icon(Icons.person_outline, size: 16, color: AppColors.textSecondary),
                                const SizedBox(width: 10),
                                Text('Profile', style: AppTextStyles.inter(fontSize: 13)),
                              ],
                            ),
                          ),
                          PopupMenuItem(
                            value: 'settings',
                            child: Row(
                              children: [
                                const Icon(Icons.settings_outlined, size: 16, color: AppColors.textSecondary),
                                const SizedBox(width: 10),
                                Text('Settings', style: AppTextStyles.inter(fontSize: 13)),
                              ],
                            ),
                          ),
                          const PopupMenuDivider(height: 1),
                          PopupMenuItem(
                            value: 'logout',
                            child: Row(
                              children: [
                                const Icon(Icons.logout, size: 16, color: AppColors.error),
                                const SizedBox(width: 10),
                                Text('Log out', style: AppTextStyles.inter(fontSize: 13, color: AppColors.error)),
                              ],
                            ),
                          ),
                        ],
                        child: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisAlignment: _isSidebarOpen
                                ? MainAxisAlignment.start
                                : MainAxisAlignment.center,
                            children: [
                              Container(
                                width: 28,
                                height: 28,
                                decoration: const BoxDecoration(
                                  color: AppColors.accent,
                                  shape: BoxShape.circle,
                                ),
                                child: const Center(
                                  child: Text(
                                    'ND',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ),
                              if (_isSidebarOpen) ...[
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        widget.userName,
                                        style: AppTextStyles.inter(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      Text(
                                        widget.userOrg,
                                        style: AppTextStyles.caption,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(
                                  Icons.more_horiz,
                                  size: 16,
                                  color: AppColors.textSecondary,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // ── Main Content Area ──
              Expanded(
                child: Column(
                  children: [
                    // Sticky Top Navigation Bar (52px height)
                    Container(
                      height: 52,
                      padding: const EdgeInsets.symmetric(horizontal: 28),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          // Left side: Project Context & Switcher
                          if (widget.projectName != null)
                            Row(
                              children: [
                                if (widget.availableProjects != null && widget.availableProjects!.length > 1)
                                  PopupMenuButton<String>(
                                    color: AppColors.bgElevated,
                                    offset: const Offset(0, 36),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(10),
                                      side: const BorderSide(color: AppColors.divider),
                                    ),
                                    onSelected: (id) => widget.onSelectProject?.call(id),
                                    itemBuilder: (context) => widget.availableProjects!.map((p) {
                                      return PopupMenuItem(
                                        value: p.id,
                                        child: Text(p.name, style: AppTextStyles.inter(fontSize: 13)),
                                      );
                                    }).toList(),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                      decoration: BoxDecoration(
                                        color: AppColors.bgSurface,
                                        border: Border.all(color: AppColors.divider),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          const Icon(Icons.folder_outlined, size: 14, color: AppColors.accent),
                                          const SizedBox(width: 8),
                                          Text(
                                            widget.projectName!,
                                            style: AppTextStyles.inter(fontSize: 12, fontWeight: FontWeight.w600),
                                          ),
                                          if (widget.projectBranch != null) ...[
                                            Text(
                                              ' · ${widget.projectBranch}',
                                              style: AppTextStyles.caption.copyWith(fontSize: 11),
                                            ),
                                          ],
                                          const SizedBox(width: 6),
                                          const Icon(Icons.unfold_more, size: 14, color: AppColors.textSecondary),
                                        ],
                                      ),
                                    ),
                                  )
                                else
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                    decoration: BoxDecoration(
                                      color: AppColors.bgSurface,
                                      border: Border.all(color: AppColors.divider),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        const Icon(Icons.folder_outlined, size: 14, color: AppColors.accent),
                                        const SizedBox(width: 8),
                                        Text(
                                          widget.projectName!,
                                          style: AppTextStyles.inter(fontSize: 12, fontWeight: FontWeight.w600),
                                        ),
                                        if (widget.projectBranch != null) ...[
                                          Text(
                                            ' · ${widget.projectBranch}',
                                            style: AppTextStyles.caption.copyWith(fontSize: 11),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                              ],
                            )
                          else
                            const SizedBox.shrink(),

                          // Right side: Notifications & Theme toggle
                          Row(
                            children: [
                          // Notification Bell
                          InkWell(
                            onTap: () => setState(() => _notifOpen = !_notifOpen),
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              width: 32,
                              height: 32,
                              decoration: BoxDecoration(
                                border: Border.all(
                                  color: _notifOpen ? AppColors.accent : AppColors.divider,
                                ),
                                borderRadius: BorderRadius.circular(6),
                                color: _notifOpen
                                    ? AppColors.accent.withValues(alpha: 0.12)
                                    : Colors.transparent,
                              ),
                              child: Stack(
                                alignment: Alignment.center,
                                children: [
                                  Icon(
                                    Icons.notifications_outlined,
                                    size: 15,
                                    color: _notifOpen ? AppColors.accent : AppColors.textSecondary,
                                  ),
                                  Positioned(
                                    top: 6,
                                    right: 6,
                                    child: Container(
                                      width: 6,
                                      height: 6,
                                      decoration: const BoxDecoration(
                                        color: AppColors.inferred,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),

                          // Theme Toggle (Sun / Moon)
                          InkWell(
                            onTap: () => setState(() => _isDarkTheme = !_isDarkTheme),
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              width: 32,
                              height: 32,
                              decoration: BoxDecoration(
                                border: Border.all(color: AppColors.divider),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Center(
                                child: Icon(
                                  _isDarkTheme ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                                  size: 15,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ),
                          ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // Active Tab Child View
                    Expanded(
                      child: widget.child,
                    ),
                  ],
                ),
              ),
            ],
          ),

          // Slide-in Notification Overlay anchored top right
          if (_notifOpen)
            Positioned(
              top: 56,
              right: 24,
              child: NotificationPanel(
                onClose: () => setState(() => _notifOpen = false),
              ),
            ),
        ],
      ),
    );
  }
}
