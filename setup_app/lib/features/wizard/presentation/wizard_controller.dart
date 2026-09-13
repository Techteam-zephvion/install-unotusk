import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/wizard_step.dart';

class WizardState {
  final WizardStep currentStep;
  final bool isBusy;
  final bool canProceed;

  const WizardState({
    this.currentStep = WizardStep.welcome,
    this.isBusy = false,
    this.canProceed = true,
  });

  WizardState copyWith({
    WizardStep? currentStep,
    bool? isBusy,
    bool? canProceed,
  }) {
    return WizardState(
      currentStep: currentStep ?? this.currentStep,
      isBusy: isBusy ?? this.isBusy,
      canProceed: canProceed ?? this.canProceed,
    );
  }
}

class WizardController extends StateNotifier<WizardState> {
  WizardController() : super(const WizardState());

  void setStep(WizardStep step) {
    if (state.isBusy && state.currentStep.isExecutionStep) {
      return; // Locked during execution
    }
    state = state.copyWith(currentStep: step);
  }

  void nextStep() {
    final nextIndex = state.currentStep.index + 1;
    if (nextIndex < WizardStep.values.length) {
      setStep(WizardStep.values[nextIndex]);
    }
  }

  void previousStep() {
    if (!state.currentStep.canGoBack) return;
    final prevIndex = state.currentStep.index - 1;
    if (prevIndex >= 0) {
      setStep(WizardStep.values[prevIndex]);
    }
  }

  void setBusy(bool isBusy) {
    state = state.copyWith(isBusy: isBusy);
  }

  void setCanProceed(bool canProceed) {
    state = state.copyWith(canProceed: canProceed);
  }

  void reset() {
    state = const WizardState();
  }
}

final wizardControllerProvider =
    StateNotifierProvider<WizardController, WizardState>((ref) {
  return WizardController();
});
