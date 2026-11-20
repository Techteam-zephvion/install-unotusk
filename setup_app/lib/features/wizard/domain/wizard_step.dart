enum WizardStep {
  welcome,
  target,
  systemCheck,
  networkCheck,
  configure,
  install,
  verify,
  ready;

  String get label {
    switch (this) {
      case WizardStep.welcome:
        return 'Welcome';
      case WizardStep.target:
        return 'Target';
      case WizardStep.systemCheck:
        return 'System Check';
      case WizardStep.networkCheck:
        return 'Network Check';
      case WizardStep.configure:
        return 'Configure';
      case WizardStep.install:
        return 'Install';
      case WizardStep.verify:
        return 'Verify';
      case WizardStep.ready:
        return 'Ready';
    }
  }

  bool get canGoBack {
    // Can go back on all steps except welcome and during active installation
    return this != WizardStep.welcome && this != WizardStep.install;
  }

  bool get isExecutionStep {
    return this == WizardStep.install || this == WizardStep.verify;
  }
}
