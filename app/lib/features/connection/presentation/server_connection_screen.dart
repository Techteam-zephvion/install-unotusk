import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/logging/diagnostic_logs_modal.dart';
import '../domain/connection_state.dart';
import 'connection_controller.dart';

class ServerConnectionScreen extends ConsumerStatefulWidget {
  const ServerConnectionScreen({super.key});

  @override
  ConsumerState<ServerConnectionScreen> createState() => _ServerConnectionScreenState();
}

class _ServerConnectionScreenState extends ConsumerState<ServerConnectionScreen> {
  late final TextEditingController _urlController;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    final currentUrl = ref.read(connectionControllerProvider).serverUrl;
    _urlController = TextEditingController(text: currentUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _handleConnect() async {
    if (_formKey.currentState?.validate() ?? false) {
      final success = await ref
          .read(connectionControllerProvider.notifier)
          .saveAndConnect(_urlController.text);
      if (success && mounted) {
        // Connected successfully
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final connectionState = ref.watch(connectionControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.slate50,
      body: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          padding: const EdgeInsets.all(24),
          child: AppCard(
            padding: const EdgeInsets.all(32),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // App Title
                  Row(
                    children: [
                      Container(
                        width: 28,
                        height: 28,
                        decoration: BoxDecoration(
                          color: AppColors.slate900,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Center(
                          child: Text(
                            'U',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text('Unotusk Server', style: AppTextStyles.h2),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Connect the employee application to your company\'s Unotusk Server instance.',
                    style: AppTextStyles.bodySmall,
                  ),
                  const SizedBox(height: 24),

                  // Server Address Input
                  AppTextField(
                    controller: _urlController,
                    label: 'Server address',
                    hint: 'http://localhost:8000',
                    keyboardType: TextInputType.url,
                    prefixIcon: const Icon(Icons.dns_outlined, size: 16),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Server address is required';
                      }
                      if (!value.startsWith('http://') && !value.startsWith('https://')) {
                        return 'Must start with http:// or https://';
                      }
                      return null;
                    },
                    onEditingComplete: _handleConnect,
                  ),
                  const SizedBox(height: 20),

                  // Connection status feedback
                  if (connectionState.status == ConnectionStatus.connected) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.successBg,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppColors.successBorder),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_outline, color: AppColors.success, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Connected to server${connectionState.serverVersion != null ? ' (v${connectionState.serverVersion})' : ''}',
                              style: AppTextStyles.bodySmall.copyWith(
                                color: AppColors.success,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    AppButton(
                      text: 'Continue to Sign In',
                      onPressed: () => context.go('/login'),
                      isFullWidth: true,
                    ),
                  ] else ...[
                    if (connectionState.errorMessage != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.errorBg,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppColors.errorBorder),
                        ),
                        child: Text(
                          connectionState.errorMessage!,
                          style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    AppButton(
                      text: 'Connect',
                      isLoading: connectionState.isChecking,
                      onPressed: _handleConnect,
                      isFullWidth: true,
                    ),
                  ],
                  const SizedBox(height: 12),
                  Center(
                    child: TextButton.icon(
                      icon: const Icon(Icons.receipt_long_outlined, size: 16),
                      label: const Text('View Connection Logs', style: TextStyle(fontSize: 12)),
                      onPressed: () => DiagnosticLogsModal.show(context),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
