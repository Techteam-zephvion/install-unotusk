import 'package:flutter/material.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';

class NotificationItem {
  final String id;
  final String title;
  final String body;
  final String timestamp;
  final String type; // success, info, warning, error
  bool isRead;

  NotificationItem({
    required this.id,
    required this.title,
    required this.body,
    required this.timestamp,
    required this.type,
    this.isRead = false,
  });
}

class NotificationPanel extends StatefulWidget {
  final VoidCallback onClose;

  const NotificationPanel({
    super.key,
    required this.onClose,
  });

  @override
  State<NotificationPanel> createState() => _NotificationPanelState();
}

class _NotificationPanelState extends State<NotificationPanel> {
  final List<NotificationItem> _notifications = [
    NotificationItem(
      id: 'n1',
      title: 'ADR #7 Indexed',
      body: 'Architecture Decision Record for PostgreSQL pgvector was verified.',
      timestamp: '10m ago',
      type: 'success',
      isRead: false,
    ),
    NotificationItem(
      id: 'n2',
      title: 'License Heartbeat Active',
      body: 'Outbound license telemetry with Platform verified (120s interval).',
      timestamp: '1h ago',
      type: 'info',
      isRead: false,
    ),
    NotificationItem(
      id: 'n3',
      title: 'Spec Contract Generated',
      body: 'BDD rate-limiter scenario ready for export.',
      timestamp: '3h ago',
      type: 'success',
      isRead: true,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 340,
      decoration: BoxDecoration(
        color: AppColors.bgElevated,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.notifications_outlined, size: 16, color: AppColors.textPrimary),
                    const SizedBox(width: 8),
                    Text(
                      'Notifications',
                      style: AppTextStyles.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ],
                ),
                InkWell(
                  onTap: () {
                    setState(() {
                      for (final n in _notifications) {
                        n.isRead = true;
                      }
                    });
                  },
                  child: Text(
                    'Mark all read',
                    style: AppTextStyles.inter(
                      fontSize: 11,
                      color: AppColors.accent,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const Divider(color: AppColors.divider, height: 1),

          // List of items
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _notifications.length,
            separatorBuilder: (context, index) => const Divider(color: AppColors.divider, height: 1),
            itemBuilder: (context, index) {
              final item = _notifications[index];
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                color: item.isRead ? Colors.transparent : AppColors.accent.withValues(alpha: 0.04),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: item.type == 'success' ? AppColors.live : AppColors.info,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              item.title,
                              style: AppTextStyles.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ],
                        ),
                        Text(
                          item.timestamp,
                          style: AppTextStyles.mono(fontSize: 10, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Padding(
                      padding: const EdgeInsets.only(left: 14),
                      child: Text(
                        item.body,
                        style: AppTextStyles.inter(fontSize: 12, color: AppColors.textSecondary),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
