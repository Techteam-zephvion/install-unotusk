import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

class DesktopScaffold extends StatelessWidget {
  final Widget body;
  final String? title;
  final Widget? headerAction;

  const DesktopScaffold({
    super.key,
    required this.body,
    this.title,
    this.headerAction,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.slate50,
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar
            Container(
              height: 48,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(
                  bottom: BorderSide(color: AppColors.slate200),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Center(
                      child: Text(
                        'U',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    title ?? 'Unotusk Server Setup',
                    style: AppTextStyles.h3,
                  ),
                  const Spacer(),
                  ?headerAction,
                ],
              ),
            ),
            // Main Content Area
            Expanded(child: body),
          ],
        ),
      ),
    );
  }
}
