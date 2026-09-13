import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../wizard/presentation/wizard_controller.dart';

class WelcomeScreen extends ConsumerWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: AppCard(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Center(
                  child: Text(
                    'U',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Unotusk Server',
                style: AppTextStyles.h1.copyWith(fontSize: 22),
              ),
              const SizedBox(height: 8),
              Text(
                'Install Unotusk inside your company infrastructure.',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.slate600,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 32),
              AppButton(
                label: 'Get Started',
                width: double.infinity,
                onPressed: () {
                  ref.read(wizardControllerProvider.notifier).nextStep();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
