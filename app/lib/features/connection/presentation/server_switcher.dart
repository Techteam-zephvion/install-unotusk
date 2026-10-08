import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/storage_service.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../projects/data/project_repository.dart';
import '../../projects/presentation/projects_controller.dart';
import '../data/local_registry_service.dart';

class ServerSwitcherButton extends ConsumerWidget {
  final bool isDark;

  const ServerSwitcherButton({super.key, required this.isDark});

  void _handleSelectServer(BuildContext context, WidgetRef ref, String targetServerId, List<LocalServer> servers) async {
    final server = servers.firstWhere((s) => s.id == targetServerId);
    
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
              context.go('/projects'); 
            }
          }
        } catch (_) {
          if (context.mounted) context.go('/projects');
        }
      } else {
        ref.read(authControllerProvider.notifier).logout();
        context.go('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final serversAsync = ref.watch(localServersProvider);
    final serverList = serversAsync.whenOrNull(data: (servers) => servers) ?? [];
    
    if (serverList.isEmpty) return const SizedBox.shrink();

    final currentUrl = ref.read(storageServiceProvider).getServerUrl();
    final currentUri = Uri.tryParse(currentUrl);
    final currentPort = currentUri?.port ?? 28000;
    
    final currentServer = serverList.where((s) => s.apiPort == currentPort).firstOrNull;
    final displayLabel = currentServer?.name ?? 'Server on $currentPort';

    return PopupMenuButton<String>(
      color: isDark ? AppColors.bgElevated : AppColors.bgElevatedLight,
      offset: const Offset(0, 36),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: isDark ? AppColors.divider : AppColors.dividerLight),
      ),
      onSelected: (id) => _handleSelectServer(context, ref, id, serverList),
      itemBuilder: (context) => serverList.map((p) {
        return PopupMenuItem(
          value: p.id,
          child: Text('${p.name} (Port: ${p.apiPort})', style: AppTextStyles.inter(fontSize: 13)),
        );
      }).toList(),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isDark ? AppColors.bgSurface : Colors.white,
          border: Border.all(color: isDark ? AppColors.divider : AppColors.dividerLight),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.dns_outlined, size: 14, color: AppColors.accent),
            const SizedBox(width: 8),
            Text(
              displayLabel,
              style: AppTextStyles.inter(fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 6),
            Icon(Icons.unfold_more, size: 14, color: isDark ? AppColors.textSecondary : AppColors.textSecondaryLight),
          ],
        ),
      ),
    );
  }
}
