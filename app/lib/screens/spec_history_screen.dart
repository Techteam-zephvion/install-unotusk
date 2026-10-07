import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../dialogs/spec_chat_drawer.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/badges.dart';

class SpecHistoryScreen extends StatefulWidget {
  final UnoPalette palette;

  const SpecHistoryScreen({super.key, required this.palette});

  @override
  State<SpecHistoryScreen> createState() => _SpecHistoryScreenState();
}

class _SpecHistoryScreenState extends State<SpecHistoryScreen> {
  String _search = '';
  DateTime? _selectedDate;
  SpecHistoryItem? _activeSpecDrawer;
  List<SpecHistoryItem> _specHistory = [];

  @override
  void initState() {
    super.initState();
    _loadSpecs();
  }

  void _loadSpecs() async {
    final list = await ApiService.fetchSpecHistory();
    if (mounted) {
      setState(() => _specHistory = list);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _specHistory.where((s) {
      final matchesSearch =
          s.query.toLowerCase().contains(_search.toLowerCase());
      if (!matchesSearch) return false;
      if (_selectedDate != null) {
        final year = _selectedDate!.year.toString();
        final month = _selectedDate!.month.toString().padLeft(2, '0');
        final day = _selectedDate!.day.toString().padLeft(2, '0');
        final iso = '$year-$month-$day';
        return s.isoDate == iso;
      }
      return true;
    }).toList();

    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 36),
          child: Center(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 860),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header
                  Text(
                    'SPEC HISTORY',
                    style: UnoTypography.mono(
                      color: widget.palette.textSec,
                      fontSize: 10,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Project Intelligence Record',
                    style: UnoTypography.brandSerif(
                      palette: widget.palette,
                      fontSize: 26,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${_specHistory.length} live architecture findings & reports indexed',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Search and Filter Bar
                  Row(
                    children: [
                      // Search input
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            color: widget.palette.bgElevated,
                            border: Border.all(color: widget.palette.div),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              Icon(LucideIcons.search,
                                  size: 13, color: widget.palette.textSec),
                              const SizedBox(width: 8),
                              Expanded(
                                child: TextField(
                                  onChanged: (val) =>
                                      setState(() => _search = val),
                                  style: UnoTypography.body(
                                      color: widget.palette.text, fontSize: 13),
                                  decoration: InputDecoration(
                                    hintText: 'Search specs…',
                                    hintStyle: UnoTypography.body(
                                        color: widget.palette.textSec,
                                        fontSize: 13),
                                    border: InputBorder.none,
                                    isDense: true,
                                    contentPadding:
                                        const EdgeInsets.symmetric(vertical: 10),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),

                      // Date Picker Button
                      OutlinedButton.icon(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: _selectedDate ?? DateTime.now(),
                            firstDate: DateTime(2020, 1, 1),
                            lastDate: DateTime(2030, 12, 31),
                            builder: (context, child) {
                              return Theme(
                                data: ThemeData(
                                  colorScheme: ColorScheme.dark(
                                    primary: widget.palette.accent,
                                    surface: widget.palette.bgSurface,
                                  ),
                                ),
                                child: child!,
                              );
                            },
                          );
                          if (picked != null) {
                            setState(() => _selectedDate = picked);
                          }
                        },
                        icon: Icon(LucideIcons.calendar,
                            size: 13,
                            color: _selectedDate != null
                                ? widget.palette.accent
                                : widget.palette.textSec),
                        label: Text(
                          _selectedDate != null
                              ? '${_selectedDate!.month}/${_selectedDate!.day}'
                              : 'Date',
                          style: UnoTypography.body(
                            color: _selectedDate != null
                                ? widget.palette.accent
                                : widget.palette.textSec,
                            fontSize: 12,
                          ),
                        ),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(
                            color: _selectedDate != null
                                ? widget.palette.accent
                                : widget.palette.div,
                          ),
                          backgroundColor: _selectedDate != null
                                ? widget.palette.accent.withValues(alpha: 0.12)
                              : Colors.transparent,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                      if (_selectedDate != null) ...[
                        const SizedBox(width: 6),
                        IconButton(
                          icon: Icon(LucideIcons.x,
                              size: 14, color: widget.palette.textSec),
                          onPressed: () => setState(() => _selectedDate = null),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 20),

                  // Similar Spec Notice Card
                  if (_specHistory.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: widget.palette.accent.withValues(alpha: 0.10),
                        border: Border.all(
                            color: widget.palette.accent.withValues(alpha: 0.3)),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(LucideIcons.trendingUp,
                              size: 14, color: widget.palette.accent),
                          const SizedBox(width: 12),
                          Expanded(
                            child: RichText(
                              text: TextSpan(
                                style: UnoTypography.body(
                                    color: widget.palette.textSec, fontSize: 12),
                                children: [
                                  TextSpan(
                                    text: 'Active Finding Highlight',
                                    style: TextStyle(
                                      color: widget.palette.accent,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  TextSpan(
                                    text:
                                        ' — ${_specHistory.first.query} [${_specHistory.first.category?.toUpperCase() ?? 'FINDING'}] (${_specHistory.first.severity ?? 'active'}).',
                                  ),
                                ],
                              ),
                            ),
                          ),
                          TextButton(
                            onPressed: () {
                              if (_specHistory.isNotEmpty) {
                                setState(() => _activeSpecDrawer = _specHistory.first);
                              }
                            },
                            child: Text(
                              'VIEW →',
                              style: UnoTypography.mono(
                                color: widget.palette.accent,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.6,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 20),

                  // Specs List
                  if (filtered.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 48),
                      child: Column(
                        children: [
                          Icon(LucideIcons.fileText,
                              size: 28, color: widget.palette.textSec),
                          const SizedBox(height: 10),
                          Text(
                            'No matching specs',
                            style: UnoTypography.body(
                              color: widget.palette.textSec,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Try adjusting your search or date filter to find past specifications.',
                            style: UnoTypography.body(
                              color: widget.palette.textSec,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    ...filtered.map((s) => Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 18, vertical: 14),
                          decoration: BoxDecoration(
                            color: widget.palette.bgSurface,
                            border: Border.all(color: widget.palette.div),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        QueryTierBadge(tier: s.queryType),
                                        const SizedBox(width: 8),
                                        ConfidenceBadge(tier: s.confidence),
                                        if (s.hasBDD) ...[
                                          const SizedBox(width: 8),
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                                horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              border: Border.all(
                                                color: widget.palette.inferred
                                                    .withValues(alpha: 0.44),
                                              ),
                                              borderRadius:
                                                  BorderRadius.circular(4),
                                            ),
                                            child: Text(
                                              'BDD',
                                              style: UnoTypography.mono(
                                                color: widget.palette.inferred,
                                                fontSize: 9,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      s.query,
                                      style: UnoTypography.body(
                                        color: widget.palette.text,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    Row(
                                      children: [
                                        Text(
                                          '${s.timestamp} · ${s.ago}',
                                          style: UnoTypography.mono(
                                            color: widget.palette.textSec,
                                            fontSize: 10,
                                          ),
                                        ),
                                        const SizedBox(width: 12),
                                        Text(
                                          'score ${s.score.toStringAsFixed(2)}',
                                          style: UnoTypography.mono(
                                            color: widget.palette.textSec,
                                            fontSize: 10,
                                          ),
                                        ),
                                        if (s.fprDelta != null) ...[
                                          const SizedBox(width: 12),
                                          Text(
                                            'FPR +${s.fprDelta!.toStringAsFixed(2)}',
                                            style: UnoTypography.mono(
                                              color: widget.palette.live,
                                              fontSize: 10,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 12),
                              OutlinedButton(
                                onPressed: () {
                                  setState(() => _activeSpecDrawer = s);
                                },
                                style: OutlinedButton.styleFrom(
                                  side: BorderSide(color: widget.palette.div),
                                  shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(6)),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 14, vertical: 6),
                                ),
                                child: Text(
                                  'View chat →',
                                  style: UnoTypography.body(
                                    color: widget.palette.textSec,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )),
                ],
              ),
            ),
          ),
        ),

        // Sliding Drawer on Right
        if (_activeSpecDrawer != null)
          Positioned(
            top: 0,
            bottom: 0,
            right: 0,
            child: SpecChatDrawer(
              spec: _activeSpecDrawer!,
              palette: widget.palette,
              onClose: () => setState(() => _activeSpecDrawer = null),
            ),
          ),
      ],
    );
  }
}
