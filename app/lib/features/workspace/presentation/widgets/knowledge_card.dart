import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/project_knowledge.dart';

class KnowledgeCard extends StatelessWidget {
  final ProjectKnowledge item;
  final VoidCallback onEdit;
  final VoidCallback onArchiveOrRestore;
  final void Function(String filePath)? onNavigateToFile;

  const KnowledgeCard({
    super.key,
    required this.item,
    required this.onEdit,
    required this.onArchiveOrRestore,
    this.onNavigateToFile,
  });

  @override
  Widget build(BuildContext context) {
    final isArchived = item.status == 'ARCHIVED';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isArchived ? AppColors.slate200 : AppColors.slate300,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Row: Category Badge, Status, and Actions
          Row(
            children: [
              // Team Curated vs Observed Fact Badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: item.sourceType == 'CUSTOMER'
                      ? AppColors.primaryMuted
                      : AppColors.slate100,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: item.sourceType == 'CUSTOMER'
                        ? AppColors.primary.withOpacity(0.3)
                        : AppColors.slate200,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      item.sourceType == 'CUSTOMER'
                          ? Icons.verified_outlined
                          : Icons.code,
                      size: 11,
                      color: item.sourceType == 'CUSTOMER'
                          ? AppColors.primary
                          : AppColors.slate600,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      item.sourceType == 'CUSTOMER' ? 'TEAM CURATED' : 'OBSERVED FACT',
                      style: AppTextStyles.bodySmall.copyWith(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                        color: item.sourceType == 'CUSTOMER'
                            ? AppColors.primary
                            : AppColors.slate600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _categoryBgColor(item.category),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  _formatCategory(item.category),
                  style: AppTextStyles.bodySmall.copyWith(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: _categoryTextColor(item.category),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (isArchived) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.slate100,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'ARCHIVED',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate500,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Text(
                item.creatorEmail ?? 'System',
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
              ),
              const Spacer(),
              // Edit button
              IconButton(
                icon: const Icon(Icons.edit_outlined, size: 16, color: AppColors.slate600),
                tooltip: 'Edit item',
                splashRadius: 16,
                constraints: const BoxConstraints(),
                padding: const EdgeInsets.all(4),
                onPressed: onEdit,
              ),
              const SizedBox(width: 8),
              // Archive/Restore button
              IconButton(
                icon: Icon(
                  isArchived ? Icons.unarchive_outlined : Icons.archive_outlined,
                  size: 16,
                  color: AppColors.slate600,
                ),
                tooltip: isArchived ? 'Restore' : 'Archive',
                splashRadius: 16,
                constraints: const BoxConstraints(),
                padding: const EdgeInsets.all(4),
                onPressed: onArchiveOrRestore,
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Title
          Text(
            item.title,
            style: AppTextStyles.h2.copyWith(
              fontSize: 15,
              color: isArchived ? AppColors.slate600 : AppColors.slate900,
            ),
          ),
          const SizedBox(height: 6),

          // Content
          Text(
            item.content,
            style: AppTextStyles.bodyMedium.copyWith(
              color: isArchived ? AppColors.slate500 : AppColors.slate700,
            ),
          ),

          // Related file or symbol if present
          if (item.relatedFilePath != null && item.relatedFilePath!.isNotEmpty) ...[
            const SizedBox(height: 12),
            InkWell(
              onTap: () => onNavigateToFile?.call(item.relatedFilePath!),
              borderRadius: BorderRadius.circular(4),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.slate50,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppColors.slate200),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.insert_drive_file_outlined, size: 13, color: AppColors.primary),
                    const SizedBox(width: 6),
                    Text(
                      item.relatedFilePath!,
                      style: AppTextStyles.code.copyWith(
                        fontSize: 11,
                        color: AppColors.primary,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                    if (item.relatedSymbol != null) ...[
                      const SizedBox(width: 6),
                      Text(
                        '• ${item.relatedSymbol}',
                        style: AppTextStyles.code.copyWith(
                          fontSize: 11,
                          color: AppColors.slate600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _formatCategory(String category) {
    return category.replaceAll('_', ' ');
  }

  Color _categoryBgColor(String category) {
    switch (category) {
      case 'ARCHITECTURE_DECISION':
        return AppColors.slate100;
      case 'BUSINESS_RULE':
        return const Color(0xFFF3E8FF); // Purple light
      case 'INTENT':
        return const Color(0xFFE0F2FE); // Sky light
      case 'CONSTRAINT':
        return AppColors.warningBg;
      case 'EXCEPTION':
        return AppColors.errorBg;
      case 'CRITICAL_COMPONENT':
        return const Color(0xFFFCE7F3); // Pink light
      default:
        return AppColors.slate100;
    }
  }

  Color _categoryTextColor(String category) {
    switch (category) {
      case 'ARCHITECTURE_DECISION':
        return AppColors.slate800;
      case 'BUSINESS_RULE':
        return const Color(0xFF7E22CE);
      case 'INTENT':
        return const Color(0xFF0369A1);
      case 'CONSTRAINT':
        return AppColors.warning;
      case 'EXCEPTION':
        return AppColors.error;
      case 'CRITICAL_COMPONENT':
        return const Color(0xFFBE185D);
      default:
        return AppColors.slate700;
    }
  }
}
