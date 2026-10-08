import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/network/api_client.dart';
import '../../../core/widgets/sidebar_scaffold.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../projects/presentation/projects_controller.dart';
import '../../projects/data/project_repository.dart';
import '../../connection/data/local_registry_service.dart';
import '../../../core/storage/storage_service.dart';
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

  ApiClient? _apiClient;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _apiClient = ref.read(apiClientProvider);
        _apiClient?.setActiveProjectId(widget.projectId);
      }
    });
  }

  @override
  void didUpdateWidget(covariant WorkspaceScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.projectId != widget.projectId) {
      _apiClient?.setActiveProjectId(widget.projectId);
    }
  }

  @override
  void dispose() {
    _apiClient?.setActiveProjectId(null);
    super.dispose();
  }

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

  void _handleSelectServer(String targetServerId, List<LocalServer> servers) async {
    final server = servers.firstWhere((s) => s.id == targetServerId);
    
    final storage = ref.read(storageServiceProvider);
    final email = storage.getSavedEmail();
    final password = storage.getSavedPassword();

    if (email == null || password == null) {
      _handleLogOut();
      return;
    }

    final newUrl = 'http://127.0.0.1:${server.apiPort}';
    storage.setServerUrl(newUrl);
    _apiClient?.updateBaseUrl(newUrl);

    if (mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: CircularProgressIndicator()),
      );
    }

    final authController = ref.read(authControllerProvider.notifier);
    bool success = await authController.login(email: email, password: password);
    if (!success) {
      success = await authController.signup(
        name: 'Admin',
        email: email,
        password: password,
      );
    }

    if (mounted) {
      Navigator.of(context, rootNavigator: true).pop(); // hide loading
      if (success) {
        final projectRepo = ref.read(projectRepositoryProvider);
        try {
          final projs = await projectRepo.getProjects();
          if (mounted) {
            if (projs.isNotEmpty) {
              context.go('/projects/${projs.first.id}');
            } else {
              ref.invalidate(projectsProvider);
              context.go('/'); 
            }
          }
        } catch (_) {
          if (mounted) context.go('/');
        }
      } else {
        _handleLogOut();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final userName = authState.user?.name ?? 'Admin';
    final userOrg = 'Unotusk Corp';

    // Watch project context and available projects
    final contextAsync = ref.watch(projectContextProvider(widget.projectId));
    final serversAsync = ref.watch(localServersProvider);
    final conversationsAsync = ref.watch(projectConversationsProvider(widget.projectId));

    final projectName = contextAsync.whenOrNull(data: (ctx) => ctx.repository?.fullName ?? ctx.repository?.name) ??
        'Unotusk Project';
    final projectBranch = contextAsync.whenOrNull(data: (ctx) => ctx.repository?.defaultBranch ?? ctx.activeSnapshot?.branch ?? 'main');

    final serverList = serversAsync.whenOrNull(data: (servers) => servers) ?? [];
    final availableServers = serverList.map((s) => (id: s.id, name: s.name, port: s.apiPort)).toList();

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
      availableServers: availableServers,
      onSelectServer: (id) => _handleSelectServer(id, serverList),
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
