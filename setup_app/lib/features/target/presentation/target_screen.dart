import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../domain/target_config.dart';
import 'target_controller.dart';
import 'widgets/remote_ssh_form.dart';

class TargetScreen extends ConsumerWidget {
  const TargetScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final targetState = ref.watch(targetControllerProvider);
    final targetNotifier = ref.read(targetControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Where should Unotusk run?', style: AppTextStyles.h1),
              const SizedBox(height: 6),
              Text(
                'Select the environment where you want to deploy Unotusk Server.',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600),
              ),
              const SizedBox(height: 24),
              _buildTargetOption(
                type: TargetType.local,
                isSelected: targetState.config.type == TargetType.local,
                onTap: () => targetNotifier.setTargetType(TargetType.local),
              ),
              const SizedBox(height: 12),
              _buildTargetOption(
                type: TargetType.remote,
                isSelected: targetState.config.type == TargetType.remote,
                onTap: () => targetNotifier.setTargetType(TargetType.remote),
              ),
              if (targetState.config.type == TargetType.remote) ...[
                const SizedBox(height: 16),
                RemoteSshForm(
                  config: targetState.config,
                  onChanged: (updated) {
                    targetNotifier.updateRemoteConfig(
                      host: updated.host,
                      port: updated.port,
                      username: updated.username,
                      privateKeyPath: updated.privateKeyPath,
                      password: updated.password,
                    );
                  },
                ),
              ],
              if (targetState.validationError != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.errorBg,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.errorBorder),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, size: 16, color: AppColors.error),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          targetState.validationError!,
                          style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  AppButton(
                    label: 'Continue',
                    onPressed: () {
                      if (targetNotifier.validate()) {
                        wizardNotifier.nextStep();
                      }
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTargetOption({
    required TargetType type,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return AppCard(
      onTap: onTap,
      backgroundColor: isSelected ? AppColors.primaryMuted.withValues(alpha: 0.2) : Colors.white,
      border: Border.all(
        color: isSelected ? AppColors.primary : AppColors.slate200,
        width: isSelected ? 1.5 : 1,
      ),
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            type == TargetType.local ? Icons.computer : Icons.cloud_outlined,
            size: 24,
            color: isSelected ? AppColors.primary : AppColors.slate600,
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  type.label,
                  style: AppTextStyles.h3.copyWith(
                    color: isSelected ? AppColors.primary : AppColors.slate900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  type.description,
                  style: AppTextStyles.bodySmall,
                ),
              ],
            ),
          ),
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: isSelected ? AppColors.primary : AppColors.slate400,
                width: isSelected ? 6 : 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
