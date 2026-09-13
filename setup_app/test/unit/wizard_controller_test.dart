import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/wizard/domain/wizard_step.dart';
import 'package:setup_app/features/wizard/presentation/wizard_controller.dart';

void main() {
  group('WizardController Tests', () {
    test('Initial state is welcome step with canProceed true', () {
      final controller = WizardController();
      expect(controller.state.currentStep, WizardStep.welcome);
      expect(controller.state.isBusy, false);
      expect(controller.state.canProceed, true);
    });

    test('nextStep advances linear step flow', () {
      final controller = WizardController();
      controller.nextStep();
      expect(controller.state.currentStep, WizardStep.target);

      controller.nextStep();
      expect(controller.state.currentStep, WizardStep.check);

      controller.nextStep();
      expect(controller.state.currentStep, WizardStep.configure);
    });

    test('previousStep goes back when permitted', () {
      final controller = WizardController();
      controller.setStep(WizardStep.target);
      expect(controller.state.currentStep.canGoBack, true);

      controller.previousStep();
      expect(controller.state.currentStep, WizardStep.welcome);
    });

    test('previousStep is blocked on execution steps', () {
      final controller = WizardController();
      controller.setStep(WizardStep.install);
      expect(controller.state.currentStep.canGoBack, false);

      controller.previousStep();
      expect(controller.state.currentStep, WizardStep.install);
    });

    test('setBusy locks step changes during execution', () {
      final controller = WizardController();
      controller.setStep(WizardStep.install);
      controller.setBusy(true);

      controller.setStep(WizardStep.welcome);
      expect(controller.state.currentStep, WizardStep.install);
    });
  });
}
