import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import 'update_dialog.dart';
import 'update_service.dart';

class UpdateBanner extends ConsumerWidget {
  const UpdateBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final updateState = ref.watch(updateStateProvider);
    final releaseInfo = updateState.value;

    if (releaseInfo == null || !releaseInfo.hasUpdate) {
      return const SizedBox.shrink();
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bannerBg = isDark ? const Color(0xFF262118) : const Color(0xFFFEF7E6);
    final bannerBorder = isDark ? const Color(0xFF533F1E) : const Color(0xFFE8D39E);
    final bannerText = isDark ? const Color(0xFFF0DFB7) : const Color(0xFF6B4B0A);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: bannerBg,
        border: Border(
          bottom: BorderSide(color: bannerBorder, width: 1),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.new_releases_outlined,
            size: 16,
            color: bannerText,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text.rich(
              TextSpan(
                text: 'New Version Available: ',
                style: AppTextStyles.bodySmall.copyWith(
                  color: bannerText,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
                children: [
                  TextSpan(
                    text: 'Unotusk v${releaseInfo.latestVersion} (${releaseInfo.codename}) is ready to install.',
                    style: AppTextStyles.bodySmall.copyWith(
                      color: bannerText,
                      fontWeight: FontWeight.w400,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 12),
          InkWell(
            onTap: () => UpdateDialog.show(context, releaseInfo),
            borderRadius: BorderRadius.circular(4),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'Update Now',
                style: AppTextStyles.label.copyWith(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: Icon(Icons.close, size: 14, color: bannerText),
            tooltip: 'Dismiss for now',
            splashRadius: 14,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            onPressed: () {
              ref.read(updateStateProvider.notifier).dismissUpdate();
            },
          ),
        ],
      ),
    );
  }
}

