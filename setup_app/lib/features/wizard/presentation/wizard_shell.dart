import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/widgets/desktop_scaffold.dart';
import '../../config/presentation/config_screen.dart';
import '../../deploy/presentation/deploy_screen.dart';
import '../../ready/presentation/ready_screen.dart';
import '../../target/presentation/target_screen.dart';
import '../../validation/presentation/server_check_screen.dart';
import '../../network/presentation/network_check_screen.dart';
import '../../verify/presentation/verify_screen.dart';
import '../../welcome/presentation/welcome_screen.dart';
import '../domain/wizard_step.dart';
import 'widgets/wizard_step_header.dart';
import 'wizard_controller.dart';

class WizardShell extends ConsumerWidget {
  const WizardShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final wizardState = ref.watch(wizardControllerProvider);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return DesktopScaffold(
      body: Column(
        children: [
          if (wizardState.currentStep != WizardStep.welcome)
            WizardStepHeader(
              currentStep: wizardState.currentStep,
              onBack: wizardState.isBusy || !wizardState.currentStep.canGoBack
                  ? null
                  : wizardNotifier.previousStep,
              onStepTapped: (step) {
                if (!wizardState.isBusy &&
                    step.index < wizardState.currentStep.index) {
                  wizardNotifier.setStep(step);
                }
              },
            ),
          Expanded(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: _buildStepContent(wizardState.currentStep),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStepContent(WizardStep step) {
    switch (step) {
      case WizardStep.welcome:
        return const WelcomeScreen(key: ValueKey('welcome_screen'));
      case WizardStep.target:
        return const TargetScreen(key: ValueKey('target_screen'));
      case WizardStep.systemCheck:
        return const ServerCheckScreen(key: ValueKey('server_check_screen'));
      case WizardStep.networkCheck:
        return const NetworkCheckScreen(key: ValueKey('network_check_screen'));
      case WizardStep.configure:
        return const ConfigScreen(key: ValueKey('config_screen'));
      case WizardStep.install:
        return const DeployScreen(key: ValueKey('deploy_screen'));
      case WizardStep.verify:
        return const VerifyScreen(key: ValueKey('verify_screen'));
      case WizardStep.ready:
        return const ReadyScreen(key: ValueKey('ready_screen'));
    }
  }
}
