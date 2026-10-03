import 'repository_manager_screen.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../data/server_manager_controller.dart';
import '../domain/server_instance.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../../wizard/presentation/wizard_shell.dart';
import '../../config/presentation/config_controller.dart';
import '../../validation/data/environment_validator.dart';

class ServerManagerScreen extends ConsumerWidget {
  const ServerManagerScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(serverManagerProvider);
    final notifier = ref.read(serverManagerProvider.notifier);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 16,
                    runSpacing: 16,
                    children: [
                      Text('Unotusk Server Manager', style: AppTextStyles.h1),
                      AppButton(
                        label: 'Add Server',
                        icon: Icons.add,
                        onPressed: () => _startNewServerWizard(context, ref),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Manage multiple independent UNOTUSK server instances on this machine.',
                    style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600),
                  ),
                  const SizedBox(height: 32),
                  if (state.isLoading)
                    const Expanded(child: Center(child: CircularProgressIndicator()))
                  else if (state.error != null)
                    Expanded(child: Center(child: Text('Error: ${state.error}', style: TextStyle(color: AppColors.error))))
                  else if (state.servers.isEmpty)
                    Expanded(child: _buildEmptyState(context, ref))
                  else
                    Expanded(
                      child: ListView.separated(
                        itemCount: state.servers.length,
                        separatorBuilder: (context, index) => const SizedBox(height: 16),
                        itemBuilder: (context, index) {
                          return _buildServerCard(context, ref, state.servers[index], notifier);
                        },
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.dns_outlined, size: 48, color: AppColors.slate300),
          const SizedBox(height: 16),
          Text('No servers installed yet.', style: AppTextStyles.h3),
          const SizedBox(height: 24),
          AppButton(
            label: 'Install UNOTUSK',
            icon: Icons.download,
            onPressed: () => _startNewServerWizard(context, ref),
          ),
        ],
      ),
    );
  }

  Widget _buildServerCard(BuildContext context, WidgetRef ref, ServerInstance server, ServerManagerController notifier) {
    Color statusColor = AppColors.slate400;
    String statusText = 'Unknown';

    switch (server.lastKnownState) {
      case ServerState.running:
        statusColor = AppColors.success;
        statusText = 'Running';
        break;
      case ServerState.stopped:
        statusColor = AppColors.slate400;
        statusText = 'Stopped';
        break;
      case ServerState.degraded:
        statusColor = AppColors.warning;
        statusText = 'Degraded';
        break;
      case ServerState.failed:
        statusColor = AppColors.error;
        statusText = 'Failed';
        break;
      case ServerState.unknown:
        break;
      case ServerState.starting:
        statusColor = AppColors.primary;
        statusText = 'Starting';
        break;
    }

    return AppCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 12,
                children: [
                  Text(server.name, style: AppTextStyles.h3),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: statusColor.withValues(alpha: 0.2)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: statusColor,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          statusText,
                          style: AppTextStyles.label.copyWith(
                            color: statusColor,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              OutlinedButton.icon(
                onPressed: () => _confirmDelete(context, server, notifier),
                icon: const Icon(Icons.delete_outline, size: 16, color: AppColors.error),
                label: const Text('Delete', style: TextStyle(color: AppColors.error)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.errorBorder),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text('ID: ${server.id}', style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500)),
          Text('Project: ${server.composeProject}', style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500)),
          const SizedBox(height: 8),
          Text(
            server.lanUrl.isNotEmpty ? server.lanUrl : 'No URL available',
            style: AppTextStyles.code.copyWith(color: AppColors.primary, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          if (server.lastKnownState == ServerState.stopped || server.lastKnownState == ServerState.failed)
            AppButton(
              label: 'Start',
              icon: Icons.play_arrow,
              onPressed: () => notifier.startServer(server),
            )
          else if (server.lastKnownState == ServerState.running || server.lastKnownState == ServerState.degraded)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                AppButton(
                  label: 'Copy URL',
                  icon: Icons.copy,
                  onPressed: () => _copyUrl(server, context),
                ),
                AppButton(
                  label: 'Restart',
                  variant: AppButtonVariant.secondary,
                  icon: Icons.refresh,
                  onPressed: () => notifier.restartServer(server),
                ),
                AppButton(
                  label: 'Manage Repos',
                  variant: AppButtonVariant.secondary,
                  icon: Icons.folder,
                  onPressed: () {
                    Navigator.push(context, MaterialPageRoute(
                      builder: (_) => RepositoryManagerScreen(server: server)
                    ));
                  },
                ),
                AppButton(
                  label: 'Stop',
                  variant: AppButtonVariant.destructive,
                  icon: Icons.stop,
                  onPressed: () => notifier.stopServer(server),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Future<void> _startNewServerWizard(BuildContext context, WidgetRef ref) async {
    final nextId = await ref.read(serverRegistryProvider).generateNextServerId();
    final validator = EnvironmentValidator();
    // Auto-allocate a port
    final availablePort = await validator.findAvailablePort('127.0.0.1');
    
    // Configure new server
    ref.read(configControllerProvider.notifier).updateServerName(nextId);
    ref.read(configControllerProvider.notifier).updateServerPort(availablePort.toString());
    
    ref.read(wizardControllerProvider.notifier).reset();
    
    if (!context.mounted) return;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (context) => const WizardShell(),
    ));
  }

  Future<void> _copyUrl(ServerInstance server, BuildContext context) async {
    final url = server.lanUrl;
    if (url.isNotEmpty) {
      // You need `import 'package:flutter/services.dart';` for Clipboard.
      // We assume it's imported, or we will add it.
      await Clipboard.setData(ClipboardData(text: url));
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Copied $url to clipboard')));
      }
    }
  }

  Future<void> _confirmDelete(BuildContext context, ServerInstance server, ServerManagerController notifier) async {
    bool deleteVolumes = false;
    final result = await showDialog<bool>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Delete Server'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Are you sure you want to delete "${server.name}"?'),
                  const SizedBox(height: 16),
                  Text('This will remove the deployment directory and stop the containers.', style: TextStyle(color: AppColors.slate600)),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Checkbox(
                        value: deleteVolumes,
                        onChanged: (val) => setState(() => deleteVolumes = val ?? false),
                      ),
                      const Expanded(
                        child: Text(
                          'Delete persistent data (PostgreSQL, Redis)',
                          style: TextStyle(color: AppColors.error),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(true),
                  style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
                  child: const Text('Delete'),
                ),
              ],
            );
          }
        );
      },
    );

    if (result == true) {
      notifier.deleteServer(server, deleteVolumes: deleteVolumes);
    }
  }
}
