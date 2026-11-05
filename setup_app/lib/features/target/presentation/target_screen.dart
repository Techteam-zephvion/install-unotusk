import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
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
    final palette = UnoPalette.of(context);
    final targetState = ref.watch(targetControllerProvider);
    final targetNotifier = ref.read(targetControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title & Subtitle
              Text(
                'Where should Unotusk run?',
                style: UnoTypography.brandSerif(
                  palette: palette,
                  fontSize: 21,
                  fontWeight: FontWeight.w400,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Select the environment where you want to deploy Unotusk Server.',
                style: AppTextStyles.bodyMediumOf(context).copyWith(
                  color: palette.textSec,
                  fontSize: 13.5,
                ),
              ),
              const SizedBox(height: 24),

              // Option 1: Local Computer
              _buildTargetOption(
                context: context,
                type: TargetType.local,
                isSelected: targetState.config.type == TargetType.local,
                onTap: () => targetNotifier.setTargetType(TargetType.local),
              ),
              const SizedBox(height: 12),

              // Option 2: Remote Linux Server
              _buildTargetOption(
                context: context,
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
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: palette.error.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: palette.error.withValues(alpha: 0.35)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline_rounded, size: 16, color: palette.error),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          targetState.validationError!,
                          style: AppTextStyles.bodySmallOf(context).copyWith(
                            color: palette.error,
                            fontWeight: FontWeight.w500,
                          ),
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
                    icon: Icons.arrow_forward_rounded,
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
    required BuildContext context,
    required TargetType type,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final palette = UnoPalette.of(context);

    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      backgroundColor: isSelected
          ? palette.accent.withValues(alpha: 0.08)
          : palette.bgSurface,
      border: Border.all(
        color: isSelected ? palette.accent : palette.div,
        width: isSelected ? 1.5 : 1,
      ),
      borderRadius: BorderRadius.circular(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: isSelected
                  ? palette.accent.withValues(alpha: 0.15)
                  : palette.bgElevated,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: isSelected ? palette.accent.withValues(alpha: 0.3) : palette.div,
              ),
            ),
            child: Icon(
              type == TargetType.local ? Icons.computer_rounded : Icons.cloud_outlined,
              size: 20,
              color: isSelected ? palette.accent : palette.textSec,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  type.label,
                  style: AppTextStyles.h3Of(context).copyWith(
                    color: isSelected ? palette.accent : palette.text,
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  type.description,
                  style: AppTextStyles.bodySmallOf(context).copyWith(
                    color: palette.textSec,
                    fontSize: 12.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // Custom Radio Button
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isSelected ? palette.accent : Colors.transparent,
              border: Border.all(
                color: isSelected ? palette.accent : palette.div,
                width: 2,
              ),
            ),
            child: isSelected
                ? const Center(
                    child: SizedBox(
                      width: 8,
                      height: 8,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  )
                : null,
          ),
        ],
      ),
    );
  }
}
