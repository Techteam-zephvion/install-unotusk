import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
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
  late final TextEditingController _repoUrlController;
  late final TextEditingController _apiKeyController;

  @override
  void initState() {
    super.initState();
    final config = ref.read(configControllerProvider).config;
    _nameController = TextEditingController(text: config.serverName);
    _portController = TextEditingController(text: config.serverPort.toString());
    _repoUrlController = TextEditingController(text: config.repoUrl);
    _apiKeyController = TextEditingController(text: config.llmApiKey);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _portController.dispose();
    _repoUrlController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);
    final configState = ref.watch(configControllerProvider);
    final configNotifier = ref.read(configControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Configuration',
                style: UnoTypography.brandSerif(
                  palette: palette,
                  fontSize: 21,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Configure core server parameters, code repository, and intelligence providers.',
                style: AppTextStyles.bodyMediumOf(context).copyWith(
                  color: palette.textSec,
                  fontSize: 13.5,
                ),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.tune_rounded, size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Text(
                          'General Settings',
                          style: UnoTypography.brandSerif(palette: palette, fontSize: 15),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
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
                            hintText: '28000',
                            controller: _portController,
                            errorText: configState.portError,
                            keyboardType: TextInputType.number,
                            onChanged: configNotifier.updateServerPort,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Divider(color: palette.div),
                    const SizedBox(height: 18),

                    Row(
                      children: [
                        Icon(Icons.source_rounded, size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Text(
                          'Repository Configuration',
                          style: UnoTypography.brandSerif(palette: palette, fontSize: 15),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    AppTextField(
                      label: 'Target Repository URL',
                      hintText: 'https://github.com/org/repo',
                      controller: _repoUrlController,
                      errorText: configState.repoUrlError,
                      onChanged: configNotifier.updateRepoUrl,
                    ),
                    const SizedBox(height: 20),
                    Divider(color: palette.div),
                    const SizedBox(height: 18),

                    Row(
                      children: [
                        Icon(Icons.auto_awesome_rounded, size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Text(
                          'Intelligence & LLM Engine',
                          style: UnoTypography.brandSerif(palette: palette, fontSize: 15),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Text(
                          'Provider:',
                          style: AppTextStyles.labelOf(context).copyWith(color: palette.textSec),
                        ),
                        _buildProviderChip(
                          label: 'Groq (Llama 3.3)',
                          isSelected: configState.config.llmProvider == LlmProviderType.groq,
                          onTap: () => configNotifier.updateLlmProvider(LlmProviderType.groq),
                        ),
                        _buildProviderChip(
                          label: 'Claude 3.5 Sonnet',
                          isSelected: configState.config.llmProvider == LlmProviderType.claude,
                          onTap: () => configNotifier.updateLlmProvider(LlmProviderType.claude),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
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
                    icon: Icons.arrow_forward_rounded,
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

  Widget _buildProviderChip({
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final palette = UnoPalette.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected ? palette.accent.withValues(alpha: 0.15) : palette.bgElevated,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? palette.accent : palette.div,
          ),
        ),
        child: Text(
          label,
          style: AppTextStyles.labelOf(context).copyWith(
            color: isSelected ? palette.accent : palette.textSec,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}
