import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';

class NotificationsPanel extends StatelessWidget {
  final UnoPalette palette;
  final List<NotificationItem> notifications;
  final VoidCallback onClearAll;
  final VoidCallback onClose;

  const NotificationsPanel({
    super.key,
    required this.palette,
    required this.notifications,
    required this.onClearAll,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final unreadCount = notifications.where((n) => !n.read).length;

    return Container(
      width: 360,
      constraints: const BoxConstraints(maxHeight: 480),
      decoration: BoxDecoration(
        color: palette.bgSurface,
        border: Border.all(color: palette.div),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.24),
            blurRadius: 48,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(
                      'Notifications',
                      style: UnoTypography.body(
                        color: palette.text,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (unreadCount > 0) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 7, vertical: 1),
                        decoration: BoxDecoration(
                          color: palette.inferred,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          '$unreadCount',
                          style: UnoTypography.mono(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                Row(
                  children: [
                    InkWell(
                      onTap: onClearAll,
                      child: Text(
                        'Mark all read',
                        style: UnoTypography.body(
                          color: palette.textSec,
                          fontSize: 11,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    InkWell(
                      onTap: onClose,
                      child: Icon(LucideIcons.x,
                          size: 14, color: palette.textSec),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Divider(height: 1, thickness: 1, color: palette.div),

          // List
          Flexible(
            child: notifications.isEmpty
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 36),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(LucideIcons.bell,
                            size: 22, color: palette.textSec),
                        const SizedBox(height: 10),
                        Text(
                          'No notifications yet',
                          style: UnoTypography.body(
                            color: palette.textSec,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    itemCount: notifications.length,
                    separatorBuilder: (context, index) =>
                        Divider(height: 1, thickness: 1, color: palette.div),
                    itemBuilder: (context, index) {
                      final n = notifications[index];
                      Color iconColor;
                      IconData iconData;
                      switch (n.type) {
                        case 'success':
                          iconColor = palette.live;
                          iconData = LucideIcons.checkCircle2;
                          break;
                        case 'warning':
                          iconColor = palette.output;
                          iconData = LucideIcons.alertTriangle;
                          break;
                        case 'error':
                          iconColor = palette.inferred;
                          iconData = LucideIcons.alertCircle;
                          break;
                        case 'info':
                        default:
                          iconColor = palette.accent;
                          iconData = LucideIcons.info;
                          break;
                      }

                      return Container(
                        color: n.read
                            ? Colors.transparent
                            : palette.accent.withValues(alpha: 0.04),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(iconData, size: 16, color: iconColor),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        n.title,
                                        style: UnoTypography.body(
                                          color: palette.text,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      Text(
                                        n.time,
                                        style: UnoTypography.mono(
                                          color: palette.textSec,
                                          fontSize: 10,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    n.body,
                                    style: UnoTypography.body(
                                      color: palette.textSec,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
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
