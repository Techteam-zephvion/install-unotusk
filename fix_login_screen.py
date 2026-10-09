import re

with open('app/lib/features/auth/presentation/login_screen.dart', 'r') as f:
    content = f.read()

# Add imports
imports = """import '../../connection/data/local_registry_service.dart';
import '../../../core/storage/storage_service.dart';
import '../../../core/network/api_client.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/widgets/loading_state_view.dart';
import '../../../core/widgets/error_state_view.dart';
import '../../../core/widgets/empty_state_view.dart';
"""
content = content.replace("import 'auth_controller.dart';", "import 'auth_controller.dart';\n" + imports)

# Update enum
content = content.replace("enum _AuthScreen { entry, checking, existingOrg, newOrg, oidcConsent, oidcTokenExchange, authenticating, denied }",
                          "enum _AuthScreen { entry, checking, existingOrg, newOrg, serverList, oidcConsent, oidcTokenExchange, authenticating, denied }")

# Update onCustomIssuer to navigate to serverList
content = content.replace("onCustomIssuer: () => setState(() => _screen = _AuthScreen.newOrg),",
                          "onCustomIssuer: () => setState(() => _screen = _AuthScreen.serverList),")

# Inject _ServerListCard into _AuthScreen switch
server_list_case = "      case _AuthScreen.serverList: return _ServerListCard(key: key, onBack: () => setState(() => _screen = _AuthScreen.entry));\n"
content = content.replace("case _AuthScreen.oidcConsent:", server_list_case + "      case _AuthScreen.oidcConsent:")

# Append _ServerListCard widget
server_list_card = """

class _ServerListCard extends ConsumerWidget {
  final VoidCallback onBack;
  const _ServerListCard({super.key, required this.onBack});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final serversAsync = ref.watch(localServersProvider);
    
    return _AuthCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Available Workspaces', style: AppTextStyles.authHeading),
          const SizedBox(height: 6),
          Text('Select a project server to connect to.', style: AppTextStyles.body.copyWith(color: AppColors.textSecondary, height: 1.5)),
          const SizedBox(height: 20),
          
          SizedBox(
            height: 300,
            child: serversAsync.when(
              loading: () => const LoadingStateView(message: 'Loading servers...'),
              error: (err, stack) => ErrorStateView(
                message: err.toString(),
                onRetry: () => ref.refresh(localServersProvider),
              ),
              data: (servers) {
                if (servers.isEmpty) {
                  return const EmptyStateView(
                    icon: Icons.dns_outlined,
                    title: 'No servers found',
                    description: 'Use the Unotusk Setup Wizard to create a new project server.',
                  );
                }
                
                return ListView.separated(
                  itemCount: servers.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final server = servers[index];
                    return InkWell(
                      onTap: () {
                        final newUrl = 'http://127.0.0.1:${server.apiPort}';
                        ref.read(storageServiceProvider).setServerUrl(newUrl);
                        ref.read(apiClientProvider).updateBaseUrl(newUrl);
                        onBack();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Switched to ${server.name} on port ${server.apiPort}')),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.bgSurface,
                          border: Border.all(color: AppColors.divider),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 32,
                              height: 32,
                              decoration: BoxDecoration(
                                color: AppColors.slate100,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: AppColors.slate200),
                              ),
                              child: const Icon(Icons.dns_outlined, size: 16, color: AppColors.slate700),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Text(server.name, style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600)),
                                      const SizedBox(width: 8),
                                      const StatusBadge(label: 'RUNNING', variant: BadgeVariant.success),
                                    ],
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Port: ${server.apiPort}',
                                    style: AppTextStyles.caption.copyWith(color: AppColors.slate400),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          
          const SizedBox(height: 20),
          _OidcButton(label: 'Back', enabled: true, filled: false, onPressed: onBack),
        ],
      ),
    );
  }
}
"""
content += server_list_card

with open('app/lib/features/auth/presentation/login_screen.dart', 'w') as f:
    f.write(content)

