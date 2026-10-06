import re

with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'r') as f:
    content = f.read()

# We need to replace the entire _buildServerCard method
start_marker = "Widget _buildServerCard(BuildContext context, WidgetRef ref, ServerInstance server, ServerManagerController notifier) {"
end_marker = "  Future<void> _startNewServerWizard(BuildContext context, WidgetRef ref) async {"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    exit(1)

new_method = """Widget _buildServerCard(BuildContext context, WidgetRef ref, ServerInstance server, ServerManagerController notifier) {
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

"""

new_content = content[:start_idx] + new_method + content[end_idx:]

with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'w') as f:
    f.write(new_content)
