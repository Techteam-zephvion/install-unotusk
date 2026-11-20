import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_fonts.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/unotusk_logo.dart';
import '../../wizard/presentation/wizard_controller.dart';

class WelcomeScreen extends ConsumerWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = UnoPalette.of(context);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 540),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Main Elevated Card
              AppCard(
                borderRadius: BorderRadius.circular(20),
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 36),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Brand mark row
                    Row(
                      children: [
                        UnotuskLogo(size: 26, onDark: palette.isDark),
                        const SizedBox(width: 10),
                        Text(
                          'Unotusk',
                          style: AppFonts.youngSerif(
                            color: palette.text,
                            fontSize: 19,
                          ),
                        ),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: palette.live.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: palette.live.withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 6,
                                height: 6,
                                decoration: BoxDecoration(
                                  color: palette.live,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                'Control Plane Ready',
                                style: AppTextStyles.labelOf(context).copyWith(
                                  color: palette.live,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // Editorial Hero Header matching Employee App
                    Text(
                      'Deploy Project Intelligence',
                      style: AppFonts.display(
                        fontSize: 32,
                        color: palette.text,
                        lineHeight: 1.15,
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Subtitle
                    Text(
                      'Deploy isolated Unotusk Data Planes inside your infrastructure with 100% data residency, multi-signal Tree-Sitter AST analysis, and auto-failover LLM grounding.',
                      style: AppFonts.body(
                        color: palette.textSec,
                        fontSize: 13.5,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Feature highlights row
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: palette.bgElevated,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: palette.div),
                      ),
                      child: Column(
                        children: [
                          _buildFeaturePill(
                            context: context,
                            icon: Icons.shield_outlined,
                            title: 'Complete Data Isolation',
                            desc: 'Per-project PostgreSQL + pgvector and Redis instances.',
                          ),
                          const SizedBox(height: 12),
                          _buildFeaturePill(
                            context: context,
                            icon: Icons.alt_route_rounded,
                            title: 'Multi-Key Backup Failover',
                            desc: 'Automatic fallback between Groq, OpenRouter, and Claude.',
                          ),
                          const SizedBox(height: 12),
                          _buildFeaturePill(
                            context: context,
                            icon: Icons.lan_outlined,
                            title: 'Zero-Config LAN Connectivity',
                            desc: 'Auto-detected local IP for seamless multi-client access.',
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 28),

                    // Action buttons
                    Row(
                      children: [
                        Expanded(
                          child: AppButton(
                            label: 'Deploy New Server',
                            icon: Icons.arrow_forward_rounded,
                            onPressed: () {
                              ref.read(wizardControllerProvider.notifier).nextStep();
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        AppButton(
                          label: 'Manage Fleet',
                          variant: AppButtonVariant.secondary,
                          icon: Icons.dns_outlined,
                          onPressed: () {
                            context.go('/manage');
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Server indicator footer
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: palette.accent,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Control Plane: http://127.0.0.1:28000',
                    style: AppFonts.mono(
                      color: palette.textSec,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeaturePill({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String desc,
  }) {
    final palette = UnoPalette.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: palette.accent),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppFonts.body(
                  color: palette.text,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                desc,
                style: AppFonts.body(
                  color: palette.textSec,
                  fontSize: 11.5,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
