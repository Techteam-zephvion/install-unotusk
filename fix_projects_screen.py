import re

with open('app/lib/features/projects/presentation/projects_screen.dart', 'r') as f:
    content = f.read()

# Add new imports
new_imports = """import '../../connection/data/local_registry_service.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/storage_service.dart';
import '../../projects/data/project_repository.dart';"""

content = content.replace("import 'projects_controller.dart';", "import 'projects_controller.dart';\n" + new_imports)

# Replace projectsProvider with localServersProvider
content = content.replace("final projectsAsync = ref.watch(projectsProvider);", "final serversAsync = ref.watch(localServersProvider);")
content = content.replace("ref.refresh(projectsProvider)", "ref.refresh(localServersProvider)")
content = content.replace("loading: () => const LoadingStateView(message: 'Loading projects...')", "loading: () => const LoadingStateView(message: 'Loading servers...')")

# Change data handling
data_handling = """                data: (servers) {
                  final filtered = servers.where((s) {
                    if (_searchQuery.isEmpty) return true;
                    return s.name.toLowerCase().contains(_searchQuery);
                  }).toList();

                  if (filtered.isEmpty) {
                    return EmptyStateView(
                      icon: Icons.dns_outlined,
                      title: _searchQuery.isEmpty ? 'No project servers yet' : 'No matching servers',
                      description: _searchQuery.isEmpty
                          ? 'Use the Unotusk Setup Wizard to create and deploy a new project server.'
                          : 'Try changing your filter query.',
                    );
                  }

                  return ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (context, index) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final server = filtered[index];
                      return _ServerItemCard(server: server);
                    },
                  );
                },"""

# We need to find the data: block and replace it
data_regex = re.compile(r"data: \(projects\) \{.*?\},\n              \),", re.DOTALL)
content = data_regex.sub(data_handling + "\n              ),", content)

# Change header text
content = content.replace("'All software projects across your organization workspace'", "'All unotusk project servers on this machine'")
content = content.replace("'Software projects assigned to you in this workspace'", "'Unotusk servers assigned to you'")
content = content.replace("Text('Projects', style: AppTextStyles.h1)", "Text('Project Servers', style: AppTextStyles.h1)")


# Add _ServerItemCard
server_item_card = """
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
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Auto-provisioning in progress, please wait...')));
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
            child: const Icon(Icons.dns_outlined, size: 18, color: AppColors.slate700),
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
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Row(
            children: [
              Text('Connect', style: AppTextStyles.label.copyWith(color: AppColors.primary)),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_forward, size: 14, color: AppColors.primary),
            ],
          ),
        ],
      ),
    );
  }
}
"""

# Replace _ProjectItemCard with _ServerItemCard
project_item_card_regex = re.compile(r"class _ProjectItemCard extends ConsumerWidget \{.*?\}\n\}", re.DOTALL)
content = project_item_card_regex.sub(server_item_card, content)


with open('app/lib/features/projects/presentation/projects_screen.dart', 'w') as f:
    f.write(content)
