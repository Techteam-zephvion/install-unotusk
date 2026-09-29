import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';
import '../widgets/badges.dart';

class SpecChatDrawer extends StatelessWidget {
  final SpecHistoryItem spec;
  final UnoPalette palette;
  final VoidCallback onClose;

  const SpecChatDrawer({
    super.key,
    required this.spec,
    required this.palette,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 520,
      decoration: BoxDecoration(
        color: palette.bgSurface,
        border: Border(left: BorderSide(color: palette.div)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 36,
            offset: const Offset(-8, 0),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: palette.bgSurface,
              border: Border(bottom: BorderSide(color: palette.div)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        QueryTierBadge(tier: spec.queryType),
                        const SizedBox(width: 6),
                        ConfidenceBadge(tier: spec.confidence),
                        if (spec.severity != null) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: (spec.severity == 'CRITICAL' || spec.severity == 'HIGH')
                                  ? const Color(0xFFD4725A).withValues(alpha: 0.15)
                                  : palette.live.withValues(alpha: 0.15),
                              border: Border.all(
                                color: (spec.severity == 'CRITICAL' || spec.severity == 'HIGH')
                                    ? const Color(0xFFD4725A).withValues(alpha: 0.44)
                                    : palette.live.withValues(alpha: 0.44),
                              ),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              spec.severity!,
                              style: UnoTypography.mono(
                                color: (spec.severity == 'CRITICAL' || spec.severity == 'HIGH')
                                    ? const Color(0xFFD4725A)
                                    : palette.live,
                                fontSize: 9,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    IconButton(
                      icon: Icon(LucideIcons.x,
                          size: 16, color: palette.textSec),
                      onPressed: onClose,
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  spec.query,
                  style: UnoTypography.body(
                    color: palette.text,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text(
                      '${spec.timestamp} · ${spec.ago}',
                      style: UnoTypography.mono(
                        color: palette.textSec,
                        fontSize: 11,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      'Score ${(spec.score * 100).toStringAsFixed(1)}',
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

          // Details List
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Description
                if (spec.description != null && spec.description!.isNotEmpty) ...[
                  Text(
                    'FINDING DESCRIPTION',
                    style: UnoTypography.mono(
                      color: palette.textSec,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: palette.bgSurface,
                      border: Border.all(color: palette.div),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      spec.description!,
                      style: UnoTypography.body(color: palette.text, fontSize: 13),
                    ),
                  ),
                  const SizedBox(height: 18),
                ],

                // Why It Matters
                if (spec.whyItMatters != null && spec.whyItMatters!.isNotEmpty) ...[
                  Text(
                    'WHY IT MATTERS',
                    style: UnoTypography.mono(
                      color: palette.accent,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: palette.accent.withValues(alpha: 0.08),
                      border: Border.all(color: palette.accent.withValues(alpha: 0.25)),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      spec.whyItMatters!,
                      style: UnoTypography.body(color: palette.text, fontSize: 13),
                    ),
                  ),
                  const SizedBox(height: 18),
                ],

                // Recommendation
                if (spec.recommendation != null && spec.recommendation!.isNotEmpty) ...[
                  Text(
                    'RECOMMENDED ARCHITECTURAL ACTION',
                    style: UnoTypography.mono(
                      color: const Color(0xFF6EC8B8),
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6EC8B8).withValues(alpha: 0.08),
                      border: Border.all(color: const Color(0xFF6EC8B8).withValues(alpha: 0.25)),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      spec.recommendation!,
                      style: UnoTypography.body(color: palette.text, fontSize: 13),
                    ),
                  ),
                  const SizedBox(height: 18),
                ],

                // Evidence Snippets
                if (spec.evidence.isNotEmpty) ...[
                  Text(
                    'GROUNDED CODE EVIDENCE (${spec.evidence.length})',
                    style: UnoTypography.mono(
                      color: palette.textSec,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...spec.evidence.map((ev) {
                    return Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: palette.bgSurface,
                        border: Border.all(color: palette.div),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(LucideIcons.fileCode, size: 13, color: palette.accent),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  ev.file,
                                  style: UnoTypography.mono(
                                    color: palette.accent,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              if (ev.lines != null)
                                Text(
                                  'L${ev.lines}',
                                  style: UnoTypography.mono(
                                    color: palette.textSec,
                                    fontSize: 10,
                                  ),
                                ),
                            ],
                          ),
                          if (ev.snippet != null && ev.snippet!.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: palette.bgElevated,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                ev.snippet!,
                                style: UnoTypography.mono(
                                  color: palette.textSec,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    );
                  }),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
