import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../domain/server_config.dart';
import 'config_controller.dart';

class ConfigScreen extends ConsumerStatefulWidget {
  const ConfigScreen({super.key});

  @override
  ConsumerState<ConfigScreen> createState() => _ConfigScreenState();
}

class _ConfigScreenState extends ConsumerState<ConfigScreen> {
  late final TextEditingController _nameController;
  late final TextEditingController _portController;
  late final TextEditingController _emailController;
  late final TextEditingController _passwordController;
  late final TextEditingController _apiKeyController;

  @override
  void initState() {
    super.initState();
    final config = ref.read(configControllerProvider).config;
    _nameController = TextEditingController(text: config.serverName);
    _portController = TextEditingController(text: config.serverPort.toString());
    _emailController = TextEditingController(text: config.adminEmail);
    _passwordController = TextEditingController(text: config.adminPassword);
    _apiKeyController = TextEditingController(text: config.llmApiKey);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _portController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final configState = ref.watch(configControllerProvider);
    final configNotifier = ref.read(configControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Configuration', style: AppTextStyles.h1),
              const SizedBox(height: 6),
              Text(
                'Configure core server parameters and credentials.',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('General Settings', style: AppTextStyles.h3),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: AppTextField(
                            label: 'Server Name',
                            hintText: 'Engineering Unotusk',
                            controller: _nameController,
                            onChanged: configNotifier.updateServerName,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          flex: 1,
                          child: AppTextField(
                            label: 'Port',
                            hintText: '8000',
                            controller: _portController,
                            errorText: configState.portError,
                            keyboardType: TextInputType.number,
                            onChanged: configNotifier.updateServerPort,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Divider(),
                    const SizedBox(height: 16),
                    Text('Initial Admin User', style: AppTextStyles.h3),
                    const SizedBox(height: 12),
                    AppTextField(
                      label: 'Admin Email',
                      hintText: 'admin@company.com',
                      controller: _emailController,
                      errorText: configState.emailError,
                      keyboardType: TextInputType.emailAddress,
                      onChanged: configNotifier.updateAdminEmail,
                    ),
                    const SizedBox(height: 12),
                    AppTextField(
                      label: 'Admin Password',
                      hintText: 'Minimum 8 characters',
                      obscureText: true,
                      controller: _passwordController,
                      errorText: configState.passwordError,
                      onChanged: configNotifier.updateAdminPassword,
                    ),
                    const SizedBox(height: 16),
                    const Divider(),
                    const SizedBox(height: 16),
                    Text('Intelligence & LLM Engine', style: AppTextStyles.h3),
                    const SizedBox(height: 12),
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Text('Provider:', style: AppTextStyles.label),
                        ChoiceChip(
                          label: const Text('Groq (Llama 3.3)'),
                          selected: configState.config.llmProvider == LlmProviderType.groq,
                          onSelected: (selected) {
                            if (selected) {
                              configNotifier.updateLlmProvider(LlmProviderType.groq);
                            }
                          },
                        ),
                        ChoiceChip(
                          label: const Text('Claude 3.5 Sonnet'),
                          selected: configState.config.llmProvider == LlmProviderType.claude,
                          onSelected: (selected) {
                            if (selected) {
                              configNotifier.updateLlmProvider(LlmProviderType.claude);
                            }
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    AppTextField(
                      label: 'API Key',
                      hintText: configState.config.llmProvider.apiKeyHint,
                      obscureText: true,
                      controller: _apiKeyController,
                      errorText: configState.apiKeyError,
                      onChanged: configNotifier.updateLlmApiKey,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  AppButton(
                    label: 'Continue',
                    onPressed: () {
                      if (configNotifier.validateAll()) {
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
}
