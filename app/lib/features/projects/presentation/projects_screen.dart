import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/desktop_scaffold.dart';
import '../../../core/widgets/empty_state_view.dart';
import '../../../core/widgets/error_state_view.dart';
import '../../../core/widgets/loading_state_view.dart';
import '../../../core/widgets/status_badge.dart';
import '../../auth/presentation/auth_controller.dart';
import 'create_project_dialog.dart';
import 'projects_controller.dart';
import '../../connection/data/local_registry_service.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/storage_service.dart';
import '../../projects/data/project_repository.dart';

class ProjectsScreen extends ConsumerStatefulWidget {
  const ProjectsScreen({super.key});

  @override
  ConsumerState<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends ConsumerState<ProjectsScreen> {
  final _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _openCreateDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => const CreateProjectDialog(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final serversAsync = ref.watch(localServersProvider);
    final authState = ref.watch(authControllerProvider);

    return DesktopScaffold(
      currentRoute: '/projects',
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Page Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Project Servers', style: AppTextStyles.h1),
                    const SizedBox(height: 4),
                    Text(
                      authState.isAdmin
                          ? 'All unotusk project servers on this machine'
                          : 'Unotusk servers assigned to you',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
                Row(
                  children: [
                    AppButton(
                      text: 'Refresh',
                      icon: Icons.refresh,
                      variant: AppButtonVariant.secondary,
                      onPressed: () => ref.refresh(localServersProvider),
                    ),
                    if (authState.isAdmin) ...[
                      const SizedBox(width: 10),
                      AppButton(
                        text: 'Connect Codebase',
                        icon: Icons.add,
                        variant: AppButtonVariant.primary,
                        onPressed: () => _openCreateDialog(context),
                      ),
                    ],
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Search Bar
            SizedBox(
              width: 320,
              child: AppTextField(
                controller: _searchController,
                hint: 'Filter projects...',
                prefixIcon: const Icon(Icons.search, size: 16),
                onChanged: (val) {
                  setState(() {
                    _searchQuery = val.trim().toLowerCase();
                  });
                },
              ),
            ),
            const SizedBox(height: 16),

            // Project List Area
            Expanded(
              child: serversAsync.when(
                loading: () =>
                    const LoadingStateView(message: 'Loading servers...'),
                error: (err, stack) => ErrorStateView(
                  message: err.toString(),
                  onRetry: () => ref.refresh(localServersProvider),
                ),
                data: (servers) {
                  final filtered = servers.where((s) {
                    if (_searchQuery.isEmpty) return true;
                    return s.name.toLowerCase().contains(_searchQuery);
                  }).toList();

                  if (filtered.isEmpty) {
                    return EmptyStateView(
                      icon: Icons.dns_outlined,
                      title: _searchQuery.isEmpty
                          ? 'No project servers yet'
                          : 'No matching servers',
                      description: _searchQuery.isEmpty
                          ? 'Use the Unotusk Setup Wizard to create and deploy a new project server.'
                          : 'Try changing your filter query.',
                    );
                  }

                  return ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final server = filtered[index];
                      return _ServerItemCard(server: server);
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ServerItemCard extends ConsumerWidget {
  final LocalServer server;

  const _ServerItemCard({required this.server});

  void _handleSelectServer(BuildContext context, WidgetRef ref) async {
    final storage = ref.read(storageServiceProvider);
    final email = storage.getSavedEmail();
    final password = storage.getSavedPassword();

    if (email == null || password == null) {
      ref.read(authControllerProvider.notifier).logout();
      context.go('/login');
      return;
    }

    final newUrl = 'http://127.0.0.1:${server.apiPort}';
    storage.setServerUrl(newUrl);
    ref.read(apiClientProvider).updateBaseUrl(newUrl);

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    final authController = ref.read(authControllerProvider.notifier);
    bool success = await authController.login(email: email, password: password);
    if (!success) {
      success = await authController.signup(
        name: 'Admin',
        email: email,
        password: password,
      );
    }

    if (context.mounted) {
      Navigator.of(context, rootNavigator: true).pop(); // hide loading
      if (success) {
        final projectRepo = ref.read(projectRepositoryProvider);
        try {
          final projs = await projectRepo.getProjects();
          if (context.mounted) {
            if (projs.isNotEmpty) {
              context.go('/projects/${projs.first.id}');
            } else {
              ref.invalidate(projectsProvider);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text(
                    'Auto-provisioning in progress, please wait...',
                  ),
                ),
              );
              // Might need to wait for worker
            }
          }
        } catch (_) {
          // ignore
        }
      } else {
        ref.read(authControllerProvider.notifier).logout();
        context.go('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      onTap: () => _handleSelectServer(context, ref),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.slate100,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppColors.slate200),
            ),
            child: const Icon(
              Icons.dns_outlined,
              size: 18,
              color: AppColors.slate700,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(server.name, style: AppTextStyles.h3),
                    const SizedBox(width: 10),
                    const StatusBadge(
                      label: 'RUNNING',
                      variant: BadgeVariant.success,
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'Port: ${server.apiPort}',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.slate400,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Row(
            children: [
              Text(
                'Connect',
                style: AppTextStyles.label.copyWith(color: AppColors.primary),
              ),
              const SizedBox(width: 4),
              const Icon(
                Icons.arrow_forward,
                size: 14,
                color: AppColors.primary,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
