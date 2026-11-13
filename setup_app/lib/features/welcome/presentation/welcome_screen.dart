import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../wizard/presentation/wizard_controller.dart';

class WelcomeScreen extends ConsumerWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = UnoPalette.of(context);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: AppCard(
            borderRadius: BorderRadius.circular(16),
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Brand Serif Header (exact YoungSerif font matching Employee App "Sign in to Unotusk")
                Text(
                  'Unotusk Server',
                  style: UnoTypography.brandSerif(
                    palette: palette,
                    fontSize: 22,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: 6),

                // Subtitle matching Employee App font size & height
                Text(
                  'Deploy Unotusk inside your company infrastructure with complete data residency and multi-agent intelligence.',
                  style: UnoTypography.body(
                    color: palette.textSec,
                    fontSize: 12.5,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 28),

                // Primary Action Button
                AppButton(
                  label: 'Get Started',
                  width: double.infinity,
                  icon: Icons.arrow_forward_rounded,
                  onPressed: () {
                    ref.read(wizardControllerProvider.notifier).nextStep();
                  },
                ),
                const SizedBox(height: 24),

                // Subtle Server status footer matching Employee App bottom indicator
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: palette.accent,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: palette.accent.withValues(alpha: 0.6),
                            blurRadius: 6,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Server: http://localhost:28000',
                      style: UnoTypography.mono(
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
      ),
    );
  }
}
