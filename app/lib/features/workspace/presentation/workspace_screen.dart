import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/widgets/sidebar_scaffold.dart';
import '../../auth/presentation/auth_controller.dart';
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

  void _handleNewQuery() {
    setState(() {
      _activeTabIndex = 0;
      _askTabKey = UniqueKey();
    });
  }

  void _handleLogOut() async {
    await ref.read(authControllerProvider.notifier).logout();
    if (mounted) {
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final userName = authState.user?.name ?? 'Naren D';
    final userOrg = 'Unotusk Corp';

    return SidebarScaffold(
      activeIndex: _activeTabIndex,
      onIndexChanged: (idx) => setState(() => _activeTabIndex = idx),
      onNewQuery: _handleNewQuery,
      userName: userName,
      userOrg: userOrg,
      onLogOut: _handleLogOut,
      child: IndexedStack(
        index: _activeTabIndex,
        children: [
          AskTab(key: _askTabKey, projectId: widget.projectId),
          SpecHistoryTab(projectId: widget.projectId),
          OntologyTab(projectId: widget.projectId),
          IngestionFeedTab(projectId: widget.projectId),
        ],
      ),
    );
  }
}
