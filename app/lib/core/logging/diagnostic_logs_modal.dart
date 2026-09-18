import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import '../widgets/app_button.dart';
import '../widgets/status_badge.dart';
import 'app_logger.dart';

class DiagnosticLogsModal extends ConsumerStatefulWidget {
  const DiagnosticLogsModal({super.key});

  static Future<void> show(BuildContext context) {
    return showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (context) => const DiagnosticLogsModal(),
    );
  }

  @override
  ConsumerState<DiagnosticLogsModal> createState() => _DiagnosticLogsModalState();
}

class _DiagnosticLogsModalState extends ConsumerState<DiagnosticLogsModal> {
  String _filter = '';
  bool _copied = false;

  BadgeVariant _getSeverityBadge(AppLogLevel severity) {
    switch (severity) {
      case AppLogLevel.error:
        return BadgeVariant.error;
      case AppLogLevel.warning:
        return BadgeVariant.warning;
      case AppLogLevel.info:
        return BadgeVariant.info;
      case AppLogLevel.debug:
        return BadgeVariant.neutral;
    }
  }

  @override
  Widget build(BuildContext context) {
    final logger = ref.watch(appLoggerProvider);
    final logs = logger.logs;
    final filteredLogs = _filter.isEmpty
        ? logs
        : logs.where((l) {
            final q = _filter.toLowerCase();
            return l.event.eventName.toLowerCase().contains(q) ||
                (l.message?.toLowerCase().contains(q) ?? false) ||
                (l.metadata?.toString().toLowerCase().contains(q) ?? false);
          }).toList();

    return Dialog(
      backgroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Container(
        width: 780,
        height: 560,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.receipt_long_outlined, size: 22, color: AppColors.slate800),
                    const SizedBox(width: 10),
                    Text('Diagnostic Event Logs', style: AppTextStyles.h2),
                    const SizedBox(width: 12),
                    StatusBadge(
                      label: '${logs.length} / ${logger.maxBuffer} EVENTS',
                      variant: BadgeVariant.neutral,
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Zero-secrets client event stream for pilot debugging and LAN connectivity verification.',
              style: AppTextStyles.bodySmall,
            ),
            const SizedBox(height: 16),

            // Controls Row
            Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: InputDecoration(
                      hintText: 'Filter logs by event, message, or metadata...',
                      hintStyle: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                      prefixIcon: const Icon(Icons.search, size: 18),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: const BorderSide(color: AppColors.slate200),
                      ),
                    ),
                    onChanged: (val) => setState(() => _filter = val),
                  ),
                ),
                const SizedBox(width: 12),
                AppButton(
                  text: _copied ? 'Copied!' : 'Copy All Logs',
                  icon: _copied ? Icons.check : Icons.copy,
                  variant: AppButtonVariant.secondary,
                  onPressed: logs.isEmpty
                      ? null
                      : () async {
                          final jsonText = const JsonEncoder.withIndent('  ').convert(
                            logs.map((l) => l.toJson()).toList(),
                          );
                          await Clipboard.setData(ClipboardData(text: jsonText));
                          setState(() => _copied = true);
                          Future.delayed(const Duration(seconds: 2), () {
                            if (mounted) setState(() => _copied = false);
                          });
                        },
                ),
                const SizedBox(width: 8),
                AppButton(
                  text: 'Clear',
                  icon: Icons.delete_outline,
                  variant: AppButtonVariant.secondary,
                  onPressed: logs.isEmpty
                      ? null
                      : () {
                          logger.clear();
                          setState(() {});
                        },
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Log stream list
            Expanded(
              child: filteredLogs.isEmpty
                  ? Center(
                      child: Text(
                        logs.isEmpty ? 'No diagnostic events logged yet.' : 'No logs match filter.',
                        style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate400),
                      ),
                    )
                  : Container(
                      decoration: BoxDecoration(
                        color: AppColors.slate900,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      padding: const EdgeInsets.all(12),
                      child: ListView.separated(
                        itemCount: filteredLogs.length,
                        separatorBuilder: (context, index) => const Divider(
                          color: AppColors.slate800,
                          height: 12,
                        ),
                        itemBuilder: (context, index) {
                          // Display newest first
                          final log = filteredLogs[filteredLogs.length - 1 - index];
                          final timeStr = log.timestamp.toIso8601String().substring(11, 19);

                          return Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                timeStr,
                                style: AppTextStyles.code.copyWith(
                                  fontSize: 11,
                                  color: AppColors.slate400,
                                ),
                              ),
                              const SizedBox(width: 10),
                              StatusBadge(
                                label: log.severity.name.toUpperCase(),
                                variant: _getSeverityBadge(log.severity),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      log.event.eventName,
                                      style: AppTextStyles.code.copyWith(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.white,
                                      ),
                                    ),
                                    if (log.message != null && log.message!.isNotEmpty)
                                      Padding(
                                        padding: const EdgeInsets.only(top: 2),
                                        child: Text(
                                          log.message!,
                                          style: AppTextStyles.bodySmall.copyWith(
                                            color: AppColors.slate300,
                                          ),
                                        ),
                                      ),
                                    if (log.metadata != null && log.metadata!.isNotEmpty)
                                      Padding(
                                        padding: const EdgeInsets.only(top: 2),
                                        child: Text(
                                          jsonEncode(log.metadata),
                                          style: AppTextStyles.code.copyWith(
                                            fontSize: 11,
                                            color: AppColors.slate400,
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ],
                          );
                        },
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
