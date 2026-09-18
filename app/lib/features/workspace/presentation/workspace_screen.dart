import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/widgets/sidebar_scaffold.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../projects/presentation/projects_controller.dart';
import 'workspace_controller.dart';
import 'tabs/ask_tab.dart';
import 'tabs/spec_history_tab.dart';
import 'tabs/ontology_tab.dart';
import 'tabs/ingestion_feed_tab.dart';

class WorkspaceScreen extends ConsumerStatefulWidget {
  final String projectId;

  const WorkspaceScreen({
    super.key,
    required this.projectId,
  });

  @override
  ConsumerState<WorkspaceScreen> createState() => _WorkspaceScreenState();
}

class _WorkspaceScreenState extends ConsumerState<WorkspaceScreen> {
  int _activeTabIndex = 0;
  Key _askTabKey = UniqueKey();
  String? _pendingQuery;

  void _handleNewQuery() {
    setState(() {
      _activeTabIndex = 0;
      _pendingQuery = null;
      _askTabKey = UniqueKey();
    });
  }

  void _handleLoadRecentChat(String query) {
    setState(() {
      _activeTabIndex = 0;
      _pendingQuery = query;
      _askTabKey = UniqueKey();
    });
  }

  void _handleLogOut() async {
    await ref.read(authControllerProvider.notifier).logout();
    if (mounted) {
      context.go('/login');
    }
  }

  void _handleSelectProject(String newProjectId) {
    context.go('/projects/$newProjectId');
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final userName = authState.user?.name ?? 'Naren D';
    final userOrg = 'Unotusk Corp';

    // Watch project context and available projects
    final contextAsync = ref.watch(projectContextProvider(widget.projectId));
    final projectsAsync = ref.watch(projectsProvider);
    final conversationsAsync = ref.watch(projectConversationsProvider(widget.projectId));

    final projectName = contextAsync.whenOrNull(data: (ctx) => ctx.repository?.fullName ?? ctx.repository?.name) ??
        'Unotusk Core API';
    final projectBranch = contextAsync.whenOrNull(data: (ctx) => ctx.repository?.defaultBranch ?? ctx.activeSnapshot?.branch ?? 'main');

    final availableProjects = projectsAsync.whenOrNull(
      data: (projects) => projects.map((p) => (id: p.id, name: p.name)).toList(),
    );

    final recentChats = conversationsAsync.whenOrNull(
      data: (threads) => threads.map((t) => t.title.isNotEmpty ? t.title : 'Investigation').toList(),
    );

    return SidebarScaffold(
      activeIndex: _activeTabIndex,
      onIndexChanged: (idx) => setState(() => _activeTabIndex = idx),
      onNewQuery: _handleNewQuery,
      onLoadRecentChat: _handleLoadRecentChat,
      recentChats: recentChats,
      projectName: projectName,
      projectBranch: projectBranch,
      availableProjects: availableProjects,
      onSelectProject: _handleSelectProject,
      userName: userName,
      userOrg: userOrg,
      onLogOut: _handleLogOut,
      child: IndexedStack(
        index: _activeTabIndex,
        children: [
          AskTab(key: _askTabKey, projectId: widget.projectId, initialQuery: _pendingQuery),
          SpecHistoryTab(projectId: widget.projectId),
          OntologyTab(projectId: widget.projectId),
          IngestionFeedTab(projectId: widget.projectId),
        ],
      ),
    );
  }
}
