enum WizardStep {
  welcome,
  target,
  check,
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
      case WizardStep.check:
        return 'Check Server';
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
    // Cannot go back on welcome, during installation, or when ready
    return this != WizardStep.welcome &&
        this != WizardStep.install &&
        this != WizardStep.verify &&
        this != WizardStep.ready;
  }

  bool get isExecutionStep {
    return this == WizardStep.install || this == WizardStep.verify;
  }
}
