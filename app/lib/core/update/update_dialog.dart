import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import '../../core/widgets/app_button.dart';
import '../../core/widgets/status_badge.dart';
import 'update_service.dart';

class UpdateDialog extends ConsumerWidget {
  final AppReleaseInfo releaseInfo;

  const UpdateDialog({super.key, required this.releaseInfo});

  static Future<void> show(BuildContext context, AppReleaseInfo info) {
    return showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) => UpdateDialog(releaseInfo: info),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? AppColors.bgSurface : AppColors.bgSurfaceLight;
    final dividerColor = isDark ? AppColors.divider : AppColors.dividerLight;
    final textColor = isDark ? AppColors.textPrimary : AppColors.textPrimaryLight;
    final mutedColor = isDark ? AppColors.textSecondary : AppColors.textSecondaryLight;

    return Dialog(
      backgroundColor: surfaceColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: dividerColor),
      ),
      child: Container(
        width: 480,
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Header: Icon + Title + Close
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                  ),
                  child: const Icon(
                    Icons.system_update_alt_rounded,
                    size: 20,
                    color: AppColors.primary,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Update Available',
                        style: AppTextStyles.h3.copyWith(color: textColor),
                      ),
                      Text(
                        'A newer version of Unotusk Employee is ready',
                        style: AppTextStyles.bodySmall.copyWith(color: mutedColor),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.close, size: 18, color: mutedColor),
                  onPressed: () => Navigator.of(context).pop(),
                  splashRadius: 16,
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Version Information Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: isDark ? AppColors.bgElevated : AppColors.bgElevatedLight,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: dividerColor),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'New Release',
                        style: AppTextStyles.bodySmall.copyWith(color: mutedColor),
                      ),
                      Row(
                        children: [
                          StatusBadge(
                            label: 'v${releaseInfo.latestVersion}',
                            variant: BadgeVariant.success,
                          ),
                          const SizedBox(width: 6),
                          StatusBadge(
                            label: releaseInfo.codename.toUpperCase(),
                            variant: BadgeVariant.info,
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Currently Installed',
                        style: AppTextStyles.bodySmall.copyWith(color: mutedColor),
                      ),
                      Text(
                        'v${releaseInfo.currentVersion}',
                        style: AppTextStyles.label.copyWith(color: textColor),
                      ),
                    ],
                  ),
                  if (releaseInfo.releaseDate.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Release Date',
                          style: AppTextStyles.bodySmall.copyWith(color: mutedColor),
                        ),
                        Text(
                          releaseInfo.releaseDate,
                          style: AppTextStyles.bodySmall.copyWith(color: mutedColor),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            // In-place upgrade notice
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.info_outline,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Seamless Upgrade: Running the updated package performs a clean in-place update. You do not need to uninstall or reconfigure your account.',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: textColor,
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Action Buttons
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                AppButton(
                  text: 'Remind Me Later',
                  variant: AppButtonVariant.secondary,
                  onPressed: () {
                    ref.read(updateStateProvider.notifier).dismissUpdate();
                    Navigator.of(context).pop();
                  },
                ),
                const SizedBox(width: 12),
                AppButton(
                  text: 'Download & Update',
                  icon: Icons.open_in_new,
                  variant: AppButtonVariant.primary,
                  onPressed: () {
                    final url = releaseInfo.downloadUrl;
                    if (url != null) {
                      UpdateService.launchDownload(url);
                    }
                    Navigator.of(context).pop();
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

