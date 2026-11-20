import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_fonts.dart';
import '../../../core/theme/uno_palette.dart';
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
  late final TextEditingController _backupApiKeyController;

  bool _obscurePrimary = true;
  bool _obscureBackup = true;

  @override
  void initState() {
    super.initState();
    final config = ref.read(configControllerProvider).config;
    _nameController = TextEditingController(text: config.serverName);
    _portController = TextEditingController(text: config.serverPort.toString());
    _repoUrlController = TextEditingController(text: config.repoUrl);
    _apiKeyController = TextEditingController(text: config.llmApiKey);
    _backupApiKeyController = TextEditingController(text: config.backupLlmApiKey);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _portController.dispose();
    _repoUrlController.dispose();
    _apiKeyController.dispose();
    _backupApiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);
    final configState = ref.watch(configControllerProvider);
    final configNotifier = ref.read(configControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);
    final currentConfig = configState.config;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Text(
                'Instance & Intelligence Setup',
                style: AppFonts.display(
                  fontSize: 28,
                  color: palette.text,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Configure your project data plane port, target Git repository, and primary/backup LLM inference keys.',
                style: AppFonts.body(
                  color: palette.textSec,
                  fontSize: 13.5,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 24),

              // SECTION 1: Instance Identity & Network
              AppCard(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.tune_rounded, size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Text(
                          'Instance & Network Port',
                          style: AppFonts.youngSerif(color: palette.text, fontSize: 16),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 3,
                          child: AppTextField(
                            label: 'Server / Project Name',
                            hintText: 'e.g. Swastha Yoga',
                            controller: _nameController,
                            onChanged: configNotifier.updateServerName,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          flex: 2,
                          child: AppTextField(
                            label: 'Data Plane Port',
                            hintText: '28150',
                            controller: _portController,
                            errorText: configState.portError,
                            keyboardType: TextInputType.number,
                            onChanged: configNotifier.updateServerPort,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Each project runs as an isolated data plane on its own dedicated port (e.g. 28100-28200).',
                      style: AppFonts.body(color: palette.textSec, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // SECTION 2: Repository Configuration
              AppCard(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.source_rounded, size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Text(
                          'Codebase Source',
                          style: AppFonts.youngSerif(color: palette.text, fontSize: 16),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    AppTextField(
                      label: 'Target Git Repository URL',
                      hintText: 'https://github.com/organization/repository.git',
                      controller: _repoUrlController,
                      errorText: configState.repoUrlError,
                      onChanged: configNotifier.updateRepoUrl,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Tree-Sitter parsers will index functions, classes, imports, and call graphs for this repository.',
                      style: AppFonts.body(color: palette.textSec, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // SECTION 3: Multi-Key LLM Providers & Automatic Failover
              AppCard(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.auto_awesome_rounded, size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Text(
                          'Primary Intelligence Provider',
                          style: AppFonts.youngSerif(color: palette.text, fontSize: 16),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Primary Provider Selector Chips
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _buildProviderChip(
                          label: 'Groq (openai/gpt-oss-120b)',
                          isSelected: currentConfig.llmProvider == LlmProviderType.groq,
                          onTap: () => configNotifier.updateLlmProvider(LlmProviderType.groq),
                        ),
                        _buildProviderChip(
                          label: 'OpenRouter (Multi-model)',
                          isSelected: currentConfig.llmProvider == LlmProviderType.openrouter,
                          onTap: () => configNotifier.updateLlmProvider(LlmProviderType.openrouter),
                        ),
                        _buildProviderChip(
                          label: 'Claude 3.5 Sonnet',
                          isSelected: currentConfig.llmProvider == LlmProviderType.claude,
                          onTap: () => configNotifier.updateLlmProvider(LlmProviderType.claude),
                        ),
                        _buildProviderChip(
                          label: 'Offline Synth',
                          isSelected: currentConfig.llmProvider == LlmProviderType.offline,
                          onTap: () => configNotifier.updateLlmProvider(LlmProviderType.offline),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    if (currentConfig.llmProvider != LlmProviderType.offline) ...[
                      AppTextField(
                        label: 'Primary API Key',
                        hintText: currentConfig.llmProvider.apiKeyHint,
                        obscureText: _obscurePrimary,
                        controller: _apiKeyController,
                        errorText: configState.apiKeyError,
                        onChanged: configNotifier.updateLlmApiKey,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePrimary ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                            size: 18,
                            color: palette.textSec,
                          ),
                          onPressed: () => setState(() => _obscurePrimary = !_obscurePrimary),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    Divider(color: palette.div),
                    const SizedBox(height: 16),

                    // BACKUP FAILOVER SECTION (Multi-Key Support)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.alt_route_rounded, size: 16, color: palette.accent),
                            const SizedBox(width: 8),
                            Text(
                              'Automatic Backup Failover',
                              style: AppFonts.youngSerif(color: palette.text, fontSize: 15),
                            ),
                          ],
                        ),
                        Switch.adaptive(
                          value: currentConfig.enableBackupLlm,
                          activeThumbColor: palette.accent,
                          activeTrackColor: palette.accent.withValues(alpha: 0.3),
                          onChanged: configNotifier.toggleBackupLlm,
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'If the primary provider encounters rate limits (HTTP 429) or timeouts, Unotusk automatically fails over to this secondary key.',
                      style: AppFonts.body(color: palette.textSec, fontSize: 12),
                    ),

                    if (currentConfig.enableBackupLlm) ...[
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _buildProviderChip(
                            label: 'OpenRouter (Backup)',
                            isSelected: currentConfig.backupLlmProvider == LlmProviderType.openrouter,
                            onTap: () => configNotifier.updateBackupLlmProvider(LlmProviderType.openrouter),
                          ),
                          _buildProviderChip(
                            label: 'Groq (Backup)',
                            isSelected: currentConfig.backupLlmProvider == LlmProviderType.groq,
                            onTap: () => configNotifier.updateBackupLlmProvider(LlmProviderType.groq),
                          ),
                          _buildProviderChip(
                            label: 'Claude (Backup)',
                            isSelected: currentConfig.backupLlmProvider == LlmProviderType.claude,
                            onTap: () => configNotifier.updateBackupLlmProvider(LlmProviderType.claude),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      AppTextField(
                        label: 'Backup API Key',
                        hintText: currentConfig.backupLlmProvider.apiKeyHint,
                        obscureText: _obscureBackup,
                        controller: _backupApiKeyController,
                        errorText: configState.backupApiKeyError,
                        onChanged: configNotifier.updateBackupLlmApiKey,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureBackup ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                            size: 18,
                            color: palette.textSec,
                          ),
                          onPressed: () => setState(() => _obscureBackup = !_obscureBackup),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 32),

              // Action Buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  AppButton(
                    label: 'Back',
                    variant: AppButtonVariant.secondary,
                    icon: Icons.arrow_back_rounded,
                    onPressed: () => wizardNotifier.previousStep(),
                  ),
                  AppButton(
                    label: 'Continue to Deployment',
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
          style: AppFonts.body(
            color: isSelected ? palette.accent : palette.textSec,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}
