import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';
import 'dialogs/archived_modal.dart';
import 'dialogs/help_modal.dart';
import 'dialogs/notifications_panel.dart';
import 'dialogs/settings_modal.dart';
import 'models/models.dart';
import 'screens/admin_screen.dart';
import 'screens/architecture_screen.dart';
import 'screens/auth_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/discoveries_screen.dart';
import 'screens/files_screen.dart';
import 'screens/ingestion_feed_screen.dart';
import 'screens/knowledge_screen.dart';
import 'screens/ontology_graph_screen.dart';
import 'screens/overview_screen.dart';
import 'screens/projects_screen.dart';
import 'screens/spec_history_screen.dart';
import 'services/api_service.dart';
import 'theme/app_theme.dart';
import 'widgets/sidebar.dart';
import 'widgets/top_nav_bar.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize window_manager for desktop platforms
  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    await windowManager.ensureInitialized();

    const windowOptions = WindowOptions(
      size: Size(1280, 720),
      minimumSize: Size(800, 500),
      center: true,
      backgroundColor: Colors.transparent,
      skipTaskbar: false,
      titleBarStyle: TitleBarStyle.hidden,
      windowButtonVisibility: false,
    );

    windowManager.waitUntilReadyToShow(windowOptions, () async {
      await windowManager.show();
      await windowManager.focus();
    });
  }

  runApp(const UnotuskApp());
}

class UnotuskApp extends StatefulWidget {
  const UnotuskApp({super.key});

  @override
  State<UnotuskApp> createState() => _UnotuskAppState();
}

class _UnotuskAppState extends State<UnotuskApp> {
  bool _isDark = true;

  void _toggleTheme() {
    setState(() {
      _isDark = !_isDark;
    });
  }

  void _setTheme(bool isDark) {
    setState(() {
      _isDark = isDark;
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = _isDark ? UnoPalette.dark : UnoPalette.light;

    return MaterialApp(
      title: '',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: _isDark ? Brightness.dark : Brightness.light,
        scaffoldBackgroundColor: palette.bgBase,
        canvasColor: palette.bgSurface,
        dividerColor: palette.div,
      ),
      home: AppShell(
        isDark: _isDark,
        onToggleTheme: _toggleTheme,
        onSetTheme: _setTheme,
      ),
    );
  }
}

class AppShell extends StatefulWidget {
  final bool isDark;
  final VoidCallback onToggleTheme;
  final Function(bool) onSetTheme;

  const AppShell({
    super.key,
    required this.isDark,
    required this.onToggleTheme,
    required this.onSetTheme,
  });

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  // Navigation stages: auth → oidc → projects → workspace
  String _appStage = 'auth';
  UserModel _user = const UserModel(
    name: 'Developer',
    org: 'Acme Corporation',
    email: '',
    role: 'Developer',
  );
  ProjectItem? _openedProject;
  String _openedProjectName = '';

  bool _sidebarOpen = true;
  String _activeView = 'chat'; // chat, spec-history, graph, feed, admin
  String _defaultSettingsTab = 'general';

  final List<ChatMessage> _messages = [];
  bool _isGenerating = false;
  final List<Timer> _generationTimers = [];

  bool _notificationsOpen = false;
  List<NotificationItem> _notifications = [];

  bool _settingsModalOpen = false;
  bool _archivedModalOpen = false;
  bool _helpModalOpen = false;

  @override
  void initState() {
    super.initState();
    _loadInitialTelemetry();
  }

  void _loadInitialTelemetry() async {
    await ApiService.checkHealth();
  }

  @override
  void dispose() {
    _clearTimers();
    super.dispose();
  }

  void _clearTimers() {
    for (final timer in _generationTimers) {
      timer.cancel();
    }
    _generationTimers.clear();
  }

  void _handleAuthenticated(UserModel user) async {
    setState(() {
      _user = user;
      _appStage = 'projects';
    });
    try {
      final notifs = await ApiService.fetchNotifications();
      if (mounted) {
        setState(() => _notifications = notifs);
      }
    } catch (_) {}
  }

  void _handleOpenProject(ProjectItem project) {
    setState(() {
      _openedProject = project;
      _openedProjectName = project.name;
      _messages.clear();
      _isGenerating = false;
      _activeView = 'overview';
      _appStage = 'workspace';
    });
    ApiService.setActiveProject(project);
    _loadProjectInitialChat(project);
  }

  void _loadProjectInitialChat(ProjectItem project) async {
    try {
      final chats = await ApiService.fetchRecentChats(projectId: project.id);
      if (chats.isNotEmpty && mounted) {
        _loadRecentChat(chats.first.id);
      }
    } catch (_) {}
  }

  void _handleBackToProjects() {
    _clearTimers();
    setState(() {
      _messages.clear();
      _isGenerating = false;
      _activeView = 'chat';
      _appStage = 'projects';
    });
  }

  void _handleLogOut() {
    _clearTimers();
    ApiService.logout();
    setState(() {
      _messages.clear();
      _openedProject = null;
      _openedProjectName = '';
      _user = const UserModel(
        name: 'Developer',
        org: 'Acme Corporation',
        email: '',
        role: 'Developer',
      );
      _appStage = 'auth';
    });
  }

  void _handleNewQuery() {
    _clearTimers();
    setState(() {
      _messages.clear();
      _isGenerating = false;
      _activeView = 'chat';
    });
  }

  void _handleSubmitQuery(String text) async {
    if (text.trim().isEmpty || _isGenerating) return;

    final queryId = 'q-${DateTime.now().millisecondsSinceEpoch}';
    final genId = 'g-${DateTime.now().millisecondsSinceEpoch + 1}';

    ApiService.recordRecentChat(RecentChat(
      id: queryId,
      title: text.trim(),
      ago: 'Just now',
      time: '${DateTime.now().hour.toString().padLeft(2, '0')}:${DateTime.now().minute.toString().padLeft(2, '0')}',
      projectId: _openedProject?.id,
    ));

    setState(() {
      _isGenerating = true;
      _messages.add(ChatMessage(
        id: queryId,
        kind: MessageKind.query,
        text: text.trim(),
      ));
      _messages.add(ChatMessage(
        id: genId,
        kind: MessageKind.generating,
        phase: 'ingesting',
      ));
    });

    try {
      final responseData = await ApiService.askQuestionDetailed(
        projectId: _openedProject?.id,
        question: text.trim(),
      );

      if (!mounted) return;
      setState(() {
        _isGenerating = false;
        final idx = _messages.indexWhere((m) => m.id == genId);
        if (idx != -1) {
          _messages[idx] = ChatMessage(
            id: genId,
            kind: MessageKind.response,
            data: responseData,
          );
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isGenerating = false;
        final idx = _messages.indexWhere((m) => m.id == genId);
        if (idx != -1) {
          _messages[idx] = ChatMessage(
            id: genId,
            kind: MessageKind.response,
            data: QueryResponseData(
              segments: [
                ResponseSegment(
                  text: 'Server Response (http://10.0.0.59:28000):\n$e',
                  tag: 'NOTICE',
                ),
              ],
              meta: 'http://10.0.0.59:28000 · verified response',
              queryType: 'hot',
              confidence: 'insufficient',
            ),
          );
        }
      });
    }
  }

  void _loadRecentChat(dynamic id) async {
    final convId = id.toString();
    _clearTimers();
    setState(() {
      _isGenerating = true;
      _messages.clear();
      _activeView = 'chat';
    });

    try {
      final msgs = await ApiService.fetchConversationMessages(
        convId,
        projectId: _openedProject?.id,
      );
      if (!mounted) return;
      if (msgs.isNotEmpty) {
        setState(() {
          _isGenerating = false;
          _messages.addAll(msgs);
        });
        return;
      }
    } catch (_) {}

    final chats = await ApiService.fetchRecentChats(projectId: _openedProject?.id);
    final recent = chats.firstWhere(
      (c) => c.id.toString() == convId,
      orElse: () => RecentChat(
        id: convId,
        title: 'Grounded Conversation Thread',
        ago: 'Just now',
        time: 'Active',
      ),
    );

    if (!mounted) return;
    setState(() {
      _isGenerating = false;
      _messages.add(ChatMessage(
        id: 'q-$convId',
        kind: MessageKind.query,
        text: recent.title,
      ));
    });
  }

  void _openSettingsTab(String tab) {
    if (tab == 'support') {
      setState(() => _helpModalOpen = true);
    } else {
      setState(() {
        _defaultSettingsTab = tab == 'settings' ? 'general' : tab;
        _settingsModalOpen = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.isDark ? UnoPalette.dark : UnoPalette.light;

    // ── Auth Screen ──
    if (_appStage == 'auth') {
      return AuthScreen(
        palette: palette,
        onAuthenticated: _handleAuthenticated,
      );
    }

    // ── Projects Dashboard ──
    if (_appStage == 'projects') {
      return ProjectsScreen(
        palette: palette,
        isDark: widget.isDark,
        onToggleTheme: widget.onToggleTheme,
        user: _user,
        userName: _user.name,
        onOpenProject: _handleOpenProject,
        onLogOut: _handleLogOut,
      );
    }

    // ── Workspace (existing chat/sidebar UI) ──

    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth < 768;
    final unreadCount = _notifications.where((n) => !n.read).length;

    return Scaffold(
      backgroundColor: palette.bgBase,
      body: Stack(
        children: [
          Row(
            children: [
                    // Sidebar (Desktop / Wide screen)
                    if (!isMobile)
                      UnoSidebar(
                        open: _sidebarOpen,
                        onToggle: () => setState(() => _sidebarOpen = !_sidebarOpen),
                        onNewQuery: _handleNewQuery,
                        palette: palette,
                        activeView: _activeView,
                        onViewChange: (v) => setState(() {
                          if (v == 'projects') {
                            _handleBackToProjects();
                          } else {
                            _activeView = v;
                            _notificationsOpen = false;
                          }
                        }),
                        onLoadRecentChat: _loadRecentChat,
                        user: _user,
                        onLogOut: _handleLogOut,
                        onNavigateSettings: _openSettingsTab,
                        onOpenArchivedModal: () =>
                            setState(() => _archivedModalOpen = true),
                      ),

              // Main Application Area
              Expanded(
                child: isMobile
                    ? SafeArea(
                        child: Column(
                          children: [
                            // Top sticky nav bar
                            TopNavBar(
                              palette: palette,
                              isDark: widget.isDark,
                              unreadCount: unreadCount,
                              notificationsOpen: _notificationsOpen,
                              onToggleNotifications: () => setState(
                                  () => _notificationsOpen = !_notificationsOpen),
                              onToggleTheme: widget.onToggleTheme,
                              showSidebarToggle: isMobile,
                              onToggleSidebar: () =>
                                  setState(() => _sidebarOpen = !_sidebarOpen),
                              projectName: _openedProjectName,
                              repoFullName:
                                  'Kushall-07/${_openedProjectName.isNotEmpty ? _openedProjectName : "SyncGuard"}',
                              branchName: 'main',
                              onBackToProjects: _handleBackToProjects,
                            ),

                            // Active Screen Content
                            Expanded(
                              child: _buildCurrentScreen(palette),
                            ),
                          ],
                        ),
                      )
                    : Column(
                        children: [
                          // Top sticky nav bar
                          TopNavBar(
                            palette: palette,
                            isDark: widget.isDark,
                            unreadCount: unreadCount,
                            notificationsOpen: _notificationsOpen,
                            onToggleNotifications: () => setState(
                                () => _notificationsOpen = !_notificationsOpen),
                            onToggleTheme: widget.onToggleTheme,
                            showSidebarToggle: isMobile,
                            onToggleSidebar: () =>
                                setState(() => _sidebarOpen = !_sidebarOpen),
                            projectName: _openedProjectName,
                            repoFullName:
                                'Kushall-07/${_openedProjectName.isNotEmpty ? _openedProjectName : "SyncGuard"}',
                            branchName: 'main',
                            onBackToProjects: _handleBackToProjects,
                          ),

                          // Active Screen Content
                          Expanded(
                            child: _buildCurrentScreen(palette),
                          ),
                        ],
                      ),
              ),
            ],
          ),

          // Mobile Drawer overlay (if mobile and sidebar open)
          if (isMobile && _sidebarOpen) ...[
            GestureDetector(
              onTap: () => setState(() => _sidebarOpen = false),
              child: Container(
                color: Colors.black.withValues(alpha: 0.5),
              ),
            ),
            Positioned(
              left: 0,
              top: 0,
              bottom: 0,
              child: UnoSidebar(
                open: true,
                onToggle: () => setState(() => _sidebarOpen = false),
                onNewQuery: () {
                  setState(() => _sidebarOpen = false);
                  _handleNewQuery();
                },
                palette: palette,
                activeView: _activeView,
                onViewChange: (v) => setState(() {
                  _sidebarOpen = false;
                  if (v == 'projects') {
                    _handleBackToProjects();
                  } else {
                    _activeView = v;
                    _notificationsOpen = false;
                  }
                }),
                onLoadRecentChat: (id) {
                  setState(() => _sidebarOpen = false);
                  _loadRecentChat(id);
                },
                user: _user,
                onLogOut: _handleLogOut,
                onNavigateSettings: (tab) {
                  setState(() => _sidebarOpen = false);
                  _openSettingsTab(tab);
                },
                onOpenArchivedModal: () {
                  setState(() {
                    _sidebarOpen = false;
                    _archivedModalOpen = true;
                  });
                },
              ),
            ),
          ],

          // Notifications Drawer Popup
          if (_notificationsOpen)
            Positioned(
              top: isMobile ? MediaQuery.of(context).padding.top + 52 : 62,
              right: 20,
              child: NotificationsPanel(
                palette: palette,
                notifications: _notifications,
                onClearAll: () {
                  setState(() {
                    for (var n in _notifications) {
                      n.read = true;
                    }
                  });
                },
                onClose: () => setState(() => _notificationsOpen = false),
              ),
            ),

          // Settings Modal Overlay
          if (_settingsModalOpen)
            SettingsModal(
              palette: palette,
              isDark: widget.isDark,
              onThemeChange: widget.onSetTheme,
              onClose: () => setState(() => _settingsModalOpen = false),
              defaultTab: _defaultSettingsTab,
              user: _user,
            ),

          // Archived Modal Overlay
          if (_archivedModalOpen)
            ArchivedModal(
              palette: palette,
              onClose: () => setState(() => _archivedModalOpen = false),
              onSelectChat: (id) {
                // optionally load chat
              },
            ),

          // Help & Support Modal Overlay
          if (_helpModalOpen)
            HelpModal(
              palette: palette,
              onClose: () => setState(() => _helpModalOpen = false),
            ),
        ],
      ),
    );
  }

  Widget _buildCurrentScreen(UnoPalette palette) {
    switch (_activeView) {
      case 'overview':
        return OverviewScreen(
          palette: palette,
          onNavigateView: (v) => setState(() => _activeView = v),
        );
      case 'files':
        return FilesScreen(palette: palette);
      case 'architecture':
        return ArchitectureScreen(
          palette: palette,
          onNavigateToFile: (path) => setState(() => _activeView = 'files'),
        );
      case 'discoveries':
        return DiscoveriesScreen(
          palette: palette,
          onAskAboutFinding: (query) {
            setState(() => _activeView = 'chat');
            _handleSubmitQuery(query);
          },
        );
      case 'knowledge':
        return KnowledgeScreen(
          palette: palette,
          onNavigateToFile: (path) => setState(() => _activeView = 'files'),
        );
      case 'spec-history':
        return SpecHistoryScreen(palette: palette);
      case 'graph':
        return OntologyGraphScreen(palette: palette);
      case 'feed':
        return IngestionFeedScreen(palette: palette);
      case 'admin':
        return AdminScreen(
          palette: palette,
          isDark: widget.isDark,
          onThemeChange: widget.onSetTheme,
          user: _user,
          defaultTab: _defaultSettingsTab,
        );
      case 'chat':
      default:
        return ChatScreen(
          palette: palette,
          messages: _messages,
          isGenerating: _isGenerating,
          onSubmitQuery: _handleSubmitQuery,
        );
    }
  }
}
