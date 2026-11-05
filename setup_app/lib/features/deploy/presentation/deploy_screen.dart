import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/error_state_card.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../data/deployment_engine.dart';
import 'deploy_controller.dart';

class DeployScreen extends ConsumerStatefulWidget {
  const DeployScreen({super.key});

  @override
  ConsumerState<DeployScreen> createState() => _DeployScreenState();
}

class _DeployScreenState extends ConsumerState<DeployScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkAutoAdvance();
    });
  }

  void _checkAutoAdvance() {
    final state = ref.read(deployControllerProvider);
    if (state.isSuccess) {
      ref.read(wizardControllerProvider.notifier).nextStep();
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);
    final deployState = ref.watch(deployControllerProvider);
    final deployNotifier = ref.read(deployControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    ref.listen(deployControllerProvider, (prev, next) {
      if (next.isSuccess && (prev == null || !prev.isSuccess)) {
        wizardNotifier.nextStep();
      }
    });

    final stages = [
      DeployStage.preparing,
      DeployStage.configuring,
      DeployStage.startingServices,
      DeployStage.migratingDb,
    ];

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Installing Unotusk',
                style: UnoTypography.brandSerif(
                  palette: palette,
                  fontSize: 21,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Deploying containers, bootstrapping PostgreSQL + pgvector, and configuring infrastructure.',
                style: AppTextStyles.bodyMediumOf(context).copyWith(
                  color: palette.textSec,
                  fontSize: 13.5,
                ),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                child: Column(
                  children: stages.map((stage) {
                    return _buildStageRow(context, stage, deployState.currentStage);
                  }).toList(),
                ),
              ),
              if (deployState.currentStage == DeployStage.failed) ...[
                const SizedBox(height: 16),
                ErrorStateCard(
                  title: 'Installation failed',
                  message: deployState.errorMessage ?? 'An error occurred while launching Docker services.',
                  technicalLogs: deployState.technicalLogs,
                  onRetry: () => deployNotifier.startDeployment(),
                ),
              ],
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (deployState.isSuccess) ...[
                    AppButton(
                      label: 'Continue',
                      icon: Icons.arrow_forward_rounded,
                      onPressed: () => wizardNotifier.nextStep(),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStageRow(BuildContext context, DeployStage stage, DeployStage currentStage) {
    final palette = UnoPalette.of(context);
    final isCompleted = currentStage.index > stage.index || currentStage == DeployStage.completed;
    final isCurrent = currentStage == stage;
    final isPending = currentStage.index < stage.index;

    Widget indicator;
    if (isCompleted) {
      indicator = Icon(Icons.check_circle_rounded, size: 20, color: palette.live);
    } else if (isCurrent) {
      indicator = SizedBox(
        width: 18,
        height: 18,
        child: CircularProgressIndicator(strokeWidth: 2, color: palette.accent),
      );
    } else {
      indicator = Container(
        width: 18,
        height: 18,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: palette.bgElevated,
          border: Border.all(color: palette.div),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          indicator,
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              stage.label,
              style: AppTextStyles.bodyMediumOf(context).copyWith(
                fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w500,
                fontSize: 13.5,
                color: isPending ? palette.textSec : palette.text,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
