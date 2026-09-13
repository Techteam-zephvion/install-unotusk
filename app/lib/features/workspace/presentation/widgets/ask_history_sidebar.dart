import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/grounded_answer.dart';

class AskHistorySidebar extends StatelessWidget {
  final List<ConversationThread> threads;
  final String? activeThreadId;
  final VoidCallback onNewThread;
  final void Function(ConversationThread thread) onSelectThread;

  const AskHistorySidebar({
    super.key,
    required this.threads,
    required this.activeThreadId,
    required this.onNewThread,
    required this.onSelectThread,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.slate200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header + New Query Button
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Text(
                  'Recent Inquiries',
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: FontWeight.w600,
                    color: AppColors.slate800,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline, size: 16, color: AppColors.slate700),
                  tooltip: 'New Investigation',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  onPressed: onNewThread,
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.slate200),

          // Thread List
          Expanded(
            child: threads.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'No previous inquiries.',
                        style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                      ),
                    ),
                  )
                : ListView.builder(
                    itemCount: threads.length,
                    itemBuilder: (context, index) {
                      final thread = threads[index];
                      final isSelected = thread.id == activeThreadId;

                      return InkWell(
                        onTap: () => onSelectThread(thread),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          decoration: BoxDecoration(
                            color: isSelected ? AppColors.slate100 : Colors.transparent,
                            border: const Border(
                              bottom: BorderSide(color: AppColors.slate100),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                thread.title.isNotEmpty ? thread.title : 'Investigation',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: AppTextStyles.bodySmall.copyWith(
                                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                  color: AppColors.slate900,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '${thread.messageCount} messages',
                                style: AppTextStyles.bodySmall.copyWith(
                                  fontSize: 10,
                                  color: AppColors.slate400,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
