import '../../ready/data/app_launcher.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/desktop_scaffold.dart';
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
    final palette = UnoPalette.of(context);
    final state = ref.watch(serverManagerProvider);
    final notifier = ref.read(serverManagerProvider.notifier);

    return DesktopScaffold(
      title: 'Unotusk Server Manager',
      body: Column(
        children: [
          // Rectangular box extended till the window borders
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
            child: AppCard(
              borderRadius: BorderRadius.circular(16),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Text(
                      'Manage independent UNOTUSK server instances, projects, and LAN endpoints.',
                      style: AppTextStyles.bodyMediumOf(context).copyWith(
                        color: palette.textSec,
                        fontSize: 13.5,
                      ),
                    ),
                  ),
                  const SizedBox(width: 20),
                  AppButton(
                    label: 'Add Server',
                    icon: Icons.add_rounded,
                    onPressed: () => _startNewServerWizard(context, ref),
                  ),
                ],
              ),
            ),
          ),

          // Main Content Area below the full-width control bar
          Expanded(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 860),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                  child: state.isLoading
                      ? Center(
                          child: CircularProgressIndicator(color: palette.accent),
                        )
                      : state.error != null
                          ? Center(
                              child: Text(
                                'Error: ${state.error}',
                                style: TextStyle(color: palette.error),
                              ),
                            )
                          : state.servers.isEmpty
                              ? _buildEmptyState(context, ref)
                              : ListView.separated(
                                  itemCount: state.servers.length,
                                  separatorBuilder: (context, index) =>
                                      const SizedBox(height: 16),
                                  itemBuilder: (context, index) {
                                    return _buildServerCard(
                                      context,
                                      ref,
                                      state.servers[index],
                                      notifier,
                                    );
                                  },
                                ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) {
    final palette = UnoPalette.of(context);

    return Center(
      child: AppCard(
        borderRadius: BorderRadius.circular(20),
        padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 48),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: palette.bgElevated,
                shape: BoxShape.circle,
                border: Border.all(color: palette.div),
              ),
              child: Icon(Icons.dns_outlined, size: 28, color: palette.textSec),
            ),
            const SizedBox(height: 18),
            Text(
              'No servers installed yet',
              style: AppTextStyles.h2Of(context).copyWith(fontSize: 18),
            ),
            const SizedBox(height: 8),
            Text(
              'Launch a new local Docker or remote SSH Unotusk Server instance with one click.',
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyMediumOf(context).copyWith(color: palette.textSec),
            ),
            const SizedBox(height: 24),
            AppButton(
              label: 'Install UNOTUSK',
              icon: Icons.download_rounded,
              onPressed: () => _startNewServerWizard(context, ref),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServerCard(
    BuildContext context,
    WidgetRef ref,
    ServerInstance server,
    ServerManagerController notifier,
  ) {
    final palette = UnoPalette.of(context);
    Color statusColor = palette.textSec;
    String statusText = 'Unknown';

    switch (server.lastKnownState) {
      case ServerState.running:
        statusColor = palette.live;
        statusText = 'Running';
        break;
      case ServerState.stopped:
        statusColor = palette.textSec;
        statusText = 'Stopped';
        break;
      case ServerState.degraded:
        statusColor = palette.warn;
        statusText = 'Degraded';
        break;
      case ServerState.failed:
        statusColor = palette.error;
        statusText = 'Failed';
        break;
      case ServerState.unknown:
        break;
      case ServerState.starting:
        statusColor = palette.accent;
        statusText = 'Starting';
        break;
    }

    return AppCard(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    server.name,
                    style: UnoTypography.brandSerif(palette: palette, fontSize: 16),
                  ),
                  const SizedBox(width: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: statusColor.withValues(alpha: 0.3)),
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
                          style: AppTextStyles.labelOf(context).copyWith(
                            color: statusColor,
                            fontSize: 10.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              OutlinedButton.icon(
                onPressed: () => _confirmDelete(context, server, notifier),
                icon: Icon(Icons.delete_outline_rounded, size: 16, color: palette.error),
                label: Text('Delete', style: TextStyle(color: palette.error)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: palette.error.withValues(alpha: 0.35)),
                  backgroundColor: palette.error.withValues(alpha: 0.05),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'ID: ${server.id}  ·  Project: ${server.composeProject}',
            style: AppTextStyles.bodySmallOf(context).copyWith(color: palette.textSec),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: palette.bgElevated,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: palette.div),
            ),
            child: Text(
              server.lanUrl.isNotEmpty ? server.lanUrl : 'No URL available',
              style: UnoTypography.mono(
                color: palette.accent,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (server.lastKnownState == ServerState.stopped || server.lastKnownState == ServerState.failed)
            AppButton(
              label: 'Start',
              icon: Icons.play_arrow_rounded,
              onPressed: () => notifier.startServer(server),
            )
          else if (server.lastKnownState == ServerState.running || server.lastKnownState == ServerState.degraded)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                AppButton(
                  label: 'Projects & Ports',
                  icon: Icons.hub_outlined,
                  onPressed: () => _openProjectsModal(server, context),
                ),
                AppButton(
                  label: 'Copy URL',
                  variant: AppButtonVariant.secondary,
                  icon: Icons.copy_rounded,
                  onPressed: () => _copyUrl(server, context),
                ),
                AppButton(
                  label: 'Open Client',
                  variant: AppButtonVariant.secondary,
                  icon: Icons.launch_rounded,
                  onPressed: () => _openClient(server, context),
                ),
                AppButton(
                  label: 'Restart',
                  variant: AppButtonVariant.secondary,
                  icon: Icons.refresh_rounded,
                  onPressed: () => notifier.restartServer(server),
                ),
                AppButton(
                  label: 'Stop',
                  variant: AppButtonVariant.destructive,
                  icon: Icons.stop_rounded,
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
    final availablePort = await validator.findAvailablePort('127.0.0.1');

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
      await Clipboard.setData(ClipboardData(text: url));
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Copied $url to clipboard')),
        );
      }
    }
  }

  Future<void> _openProjectsModal(ServerInstance server, BuildContext context) async {
    final palette = UnoPalette.of(context);

    showDialog(
      context: context,
      builder: (ctx) {
        return Dialog(
          backgroundColor: palette.bgSurface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: palette.div),
          ),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720, maxHeight: 600),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Server: ${server.name}', style: AppTextStyles.h2Of(ctx)),
                        IconButton(
                          icon: Icon(Icons.close_rounded, color: palette.textSec),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Manage data plane project container instances attached to this server.',
                      style: AppTextStyles.bodyMediumOf(ctx).copyWith(color: palette.textSec),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _openClient(ServerInstance server, BuildContext context) async {
    final palette = UnoPalette.of(context);
    final launched = await AppLauncher().launchEmployeeApp(serverUrl: server.lanUrl);
    if (!launched && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Employee Client not found in local build. Connect manually using ${server.lanUrl}'),
          backgroundColor: palette.bgElevated,
        ),
      );
    }
  }

  Future<void> _confirmDelete(
    BuildContext context,
    ServerInstance server,
    ServerManagerController notifier,
  ) async {
    final palette = UnoPalette.of(context);
    bool deleteVolumes = false;

    final result = await showDialog<bool>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              backgroundColor: palette.bgSurface,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: palette.div),
              ),
              title: Text('Delete Server', style: AppTextStyles.h2Of(context)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Are you sure you want to delete "${server.name}"?',
                    style: AppTextStyles.bodyMediumOf(context),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'This will remove the deployment directory and stop Docker containers.',
                    style: AppTextStyles.bodySmallOf(context).copyWith(color: palette.textSec),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Checkbox(
                        value: deleteVolumes,
                        activeColor: palette.error,
                        onChanged: (val) => setState(() => deleteVolumes = val ?? false),
                      ),
                      Expanded(
                        child: Text(
                          'Delete persistent data (PostgreSQL, Redis)',
                          style: TextStyle(color: palette.error, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: Text('Cancel', style: TextStyle(color: palette.textSec)),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: palette.error,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: const Text('Delete', style: TextStyle(color: Colors.white)),
                ),
              ],
            );
          },
        );
      },
    );

    if (result == true) {
      notifier.deleteServer(server, deleteVolumes: deleteVolumes);
    }
  }
}
