import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';

class SettingsModal extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final Function(bool) onThemeChange;
  final VoidCallback onClose;
  final String defaultTab;
  final UserModel user;

  const SettingsModal({
    super.key,
    required this.palette,
    required this.isDark,
    required this.onThemeChange,
    required this.onClose,
    this.defaultTab = 'profile',
    required this.user,
  });

  @override
  State<SettingsModal> createState() => _SettingsModalState();
}

class _SettingsModalState extends State<SettingsModal> {
  late String _activeTab;
  String _selectedReasoningTier = 'warm';
  String _selectedSpecFormat = 'bdd';

  static const List<Map<String, dynamic>> _tabs = [
    {'id': 'profile', 'label': 'Profile', 'icon': LucideIcons.user},
    {'id': 'appearance', 'label': 'Appearance', 'icon': LucideIcons.palette},
    {'id': 'intelligence', 'label': 'Intelligence', 'icon': LucideIcons.sparkles},
  ];

  @override
  void initState() {
    super.initState();
    if (widget.defaultTab == 'general' || widget.defaultTab == 'settings') {
      _activeTab = 'appearance';
    } else if (widget.defaultTab == 'personalization') {
      _activeTab = 'intelligence';
    } else if (_tabs.any((t) => t['id'] == widget.defaultTab)) {
      _activeTab = widget.defaultTab;
    } else {
      _activeTab = 'profile';
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.palette;

    return Material(
      color: Colors.black.withValues(alpha: widget.isDark ? 0.65 : 0.40),
      child: Center(
        child: Container(
          width: 760,
          height: 560,
          margin: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: palette.bgSurface,
            border: Border.all(color: palette.div.withValues(alpha: 0.8)),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: widget.isDark ? 0.55 : 0.22),
                blurRadius: 54,
                offset: const Offset(0, 22),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── Header Bar ──
              Padding(
                padding: const EdgeInsets.fromLTRB(26, 20, 20, 18),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Settings',
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Manage your profile, preferences, and workspace experience',
                          style: UnoTypography.body(
                            color: palette.textSec,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    InkWell(
                      onTap: widget.onClose,
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: palette.bgElevated,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: palette.div.withValues(alpha: 0.7)),
                        ),
                        child: Icon(
                          LucideIcons.x,
                          size: 16,
                          color: palette.textSec,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Divider(height: 1, thickness: 1, color: palette.div.withValues(alpha: 0.6)),

              // ── Split Layout ──
              Expanded(
                child: Row(
                  children: [
                    // Left Tab Sidebar
                    Container(
                      width: 210,
                      decoration: BoxDecoration(
                        color: palette.bgSurface,
                        border: Border(
                          right: BorderSide(color: palette.div.withValues(alpha: 0.6)),
                        ),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                      child: ListView(
                        children: _tabs.map((t) {
                          final active = _activeTab == t['id'];
                          return InkWell(
                            onTap: () => setState(() => _activeTab = t['id']),
                            borderRadius: BorderRadius.circular(10),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              margin: const EdgeInsets.only(bottom: 4),
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 10),
                              decoration: BoxDecoration(
                                color: active
                                    ? palette.accent.withValues(
                                        alpha: widget.isDark ? 0.12 : 0.15)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                border: active
                                    ? Border.all(
                                        color: palette.accent.withValues(alpha: 0.35))
                                    : Border.all(color: Colors.transparent),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    t['icon'] as IconData,
                                    size: 16,
                                    color: active
                                        ? palette.accent
                                        : palette.textSec,
                                  ),
                                  const SizedBox(width: 10),
                                  Text(
                                    t['label'] as String,
                                    style: UnoTypography.body(
                                      color: active
                                          ? palette.text
                                          : palette.textSec,
                                      fontSize: 13,
                                      fontWeight: active
                                          ? FontWeight.w600
                                          : FontWeight.w500,
                                    ),
                                  ),
                                  if (active) ...[
                                    const Spacer(),
                                    Container(
                                      width: 5,
                                      height: 5,
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: palette.accent,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),

                    // Right Content Pane
                    Expanded(
                      child: Container(
                        color: palette.bgSurface,
                        padding: const EdgeInsets.all(28),
                        child: SingleChildScrollView(
                          physics: const BouncingScrollPhysics(),
                          child: _buildTabContent(palette),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabContent(UnoPalette palette) {
    switch (_activeTab) {
      case 'profile':
        return _buildProfileTab(palette);
      case 'appearance':
        return _buildAppearanceTab(palette);
      case 'intelligence':
        return _buildIntelligenceTab(palette);
      default:
        return _buildProfileTab(palette);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 1. Profile Tab: Elegant Executive Monogram & Verified Info
  // ─────────────────────────────────────────────────────────────
  Widget _buildProfileTab(UnoPalette palette) {
    final displayName = widget.user.name.trim().isNotEmpty
        ? widget.user.name.trim()
        : (widget.user.email.isNotEmpty
            ? widget.user.email.split('@').first
            : 'Developer Lead');

    final displayEmail = widget.user.email.isNotEmpty
        ? widget.user.email
        : 'lead@acme.com';

    final displayRole = widget.user.role.isNotEmpty
        ? widget.user.role
        : 'Workspace Administrator';

    final initials = displayName.contains(' ')
        ? displayName
            .split(' ')
            .where((s) => s.isNotEmpty)
            .take(2)
            .map((s) => s[0].toUpperCase())
            .join()
        : (displayName.isNotEmpty ? displayName[0].toUpperCase() : 'DL');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(LucideIcons.userCheck, size: 18, color: palette.accent),
            const SizedBox(width: 8),
            Text(
              'User Profile',
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // ── Hero Profile Monogram Card ──
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: palette.bgElevated,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: palette.div),
            gradient: LinearGradient(
              colors: widget.isDark
                  ? [
                      const Color(0xFF161E32),
                      const Color(0xFF111728),
                    ]
                  : [
                      const Color(0xFFFCF9F4),
                      const Color(0xFFF7F3EA),
                    ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Row(
            children: [
              // Monogram Avatar
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: palette.accent,
                  boxShadow: [
                    BoxShadow(
                      color: palette.accent.withValues(alpha: 0.25),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Center(
                  child: Text(
                    initials,
                    style: TextStyle(
                      color: widget.isDark
                          ? const Color(0xFF0A0F20)
                          : Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          displayName,
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Live Session Beacon
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2.5),
                          decoration: BoxDecoration(
                            color: const Color(0xFF22C55E).withValues(alpha: 0.14),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: const Color(0xFF22C55E)
                                    .withValues(alpha: 0.35)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 5,
                                height: 5,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: Color(0xFF22C55E),
                                ),
                              ),
                              const SizedBox(width: 4),
                              Text(
                                'Active',
                                style: UnoTypography.body(
                                  color: widget.isDark
                                      ? const Color(0xFF4ADE80)
                                      : const Color(0xFF15803D),
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      displayEmail,
                      style: UnoTypography.body(
                        color: palette.textSec,
                        fontSize: 12.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 2.5),
                      decoration: BoxDecoration(
                        color: palette.accent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                            color: palette.accent.withValues(alpha: 0.28)),
                      ),
                      child: Text(
                        displayRole.toUpperCase(),
                        style: UnoTypography.mono(
                          color: palette.accent,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 24),

        // ── Account Details Card ──
        Text(
          'WORKSPACE ACCOUNT DETAILS',
          style: UnoTypography.mono(
            color: palette.textSec,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: palette.bgElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.div),
          ),
          child: Column(
            children: [
              _buildInfoRow('Full Name', displayName,
                  icon: LucideIcons.user, palette: palette),
              Divider(
                  height: 1,
                  thickness: 1,
                  color: palette.div.withValues(alpha: 0.5)),
              _buildInfoRow('Email Address', displayEmail,
                  icon: LucideIcons.mail,
                  palette: palette,
                  badge: 'Verified'),
              Divider(
                  height: 1,
                  thickness: 1,
                  color: palette.div.withValues(alpha: 0.5)),
              _buildInfoRow('Workspace Role', displayRole,
                  icon: LucideIcons.shieldCheck, palette: palette),
              Divider(
                  height: 1,
                  thickness: 1,
                  color: palette.div.withValues(alpha: 0.5)),
              _buildInfoRow('Organization', 'Acme Corporation',
                  icon: LucideIcons.building2, palette: palette),
            ],
          ),
        ),

        const SizedBox(height: 20),

        // ── Security Summary Card ──
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: palette.bgElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.div),
          ),
          child: Row(
            children: [
              Icon(LucideIcons.lock, size: 16, color: palette.accent),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Local Cryptographic Authentication',
                      style: UnoTypography.body(
                        color: palette.text,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Signed via secure local HS256 JWT tokens. Codebase intelligence and credentials remain private on your server.',
                      style: UnoTypography.body(
                        color: palette.textSec,
                        fontSize: 11,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────
  // 2. Appearance Tab: Tactile Theme Mode Switcher
  // ─────────────────────────────────────────────────────────────
  Widget _buildAppearanceTab(UnoPalette palette) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(LucideIcons.palette, size: 18, color: palette.accent),
            const SizedBox(width: 8),
            Text(
              'Appearance & Interface',
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Select your workspace theme mode and visual ambiance',
          style: UnoTypography.body(
            color: palette.textSec,
            fontSize: 12.5,
          ),
        ),
        const SizedBox(height: 20),

        Text(
          'THEME MODE',
          style: UnoTypography.mono(
            color: palette.textSec,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 10),

        Row(
          children: [
            // Dark Mode Card
            Expanded(
              child: InkWell(
                onTap: () => widget.onThemeChange(true),
                borderRadius: BorderRadius.circular(14),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: widget.isDark
                        ? const Color(0xFF161E32)
                        : palette.bgElevated,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: widget.isDark
                          ? palette.accent
                          : palette.div,
                      width: widget.isDark ? 1.8 : 1.0,
                    ),
                    boxShadow: widget.isDark
                        ? [
                            BoxShadow(
                              color: palette.accent.withValues(alpha: 0.15),
                              blurRadius: 16,
                              offset: const Offset(0, 4),
                            ),
                          ]
                        : null,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: const Color(0xFF0A0F20),
                              border: Border.all(
                                  color: palette.accent.withValues(alpha: 0.3)),
                            ),
                            child: Icon(
                              LucideIcons.moon,
                              size: 16,
                              color: palette.accent,
                            ),
                          ),
                          if (widget.isDark)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 7, vertical: 2),
                              decoration: BoxDecoration(
                                color: palette.accent,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                'ACTIVE',
                                style: UnoTypography.mono(
                                  color: const Color(0xFF0A0F20),
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'Warm Dark',
                        style: UnoTypography.body(
                          color: palette.text,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Obsidian Navy (#0A0F20) with Warm Ivory accents. Optimized for low-light focus.',
                        style: UnoTypography.body(
                          color: palette.textSec,
                          fontSize: 11.5,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            const SizedBox(width: 14),

            // Light Mode Card
            Expanded(
              child: InkWell(
                onTap: () => widget.onThemeChange(false),
                borderRadius: BorderRadius.circular(14),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: !widget.isDark
                        ? const Color(0xFFFAF7F2)
                        : palette.bgElevated,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: !widget.isDark
                          ? palette.accent
                          : palette.div,
                      width: !widget.isDark ? 1.8 : 1.0,
                    ),
                    boxShadow: !widget.isDark
                        ? [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.08),
                              blurRadius: 16,
                              offset: const Offset(0, 4),
                            ),
                          ]
                        : null,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: const Color(0xFFEFEAE0),
                              border: Border.all(color: const Color(0xFFDDD5C9)),
                            ),
                            child: const Icon(
                              LucideIcons.sun,
                              size: 16,
                              color: Color(0xFF181816),
                            ),
                          ),
                          if (!widget.isDark)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 7, vertical: 2),
                              decoration: BoxDecoration(
                                color: palette.accent,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                'ACTIVE',
                                style: UnoTypography.mono(
                                  color: Colors.white,
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'Warm Light',
                        style: UnoTypography.body(
                          color: palette.text,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Natural ivory tones with high-contrast typography. Crisp readability for daytime.',
                        style: UnoTypography.body(
                          color: palette.textSec,
                          fontSize: 11.5,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 24),

        // ── Typography System Spec ──
        Text(
          'TYPOGRAPHY SYSTEM',
          style: UnoTypography.mono(
            color: palette.textSec,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: palette.bgElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.div),
          ),
          child: Column(
            children: [
              _buildTypeSpecRow('Editorial Serifs', 'Young Serif & Instrument Serif',
                  'Headings, branding & project hero titles', palette),
              Divider(
                  height: 1,
                  thickness: 1,
                  color: palette.div.withValues(alpha: 0.5)),
              _buildTypeSpecRow('Interface Body', 'Inter',
                  'High-legibility studio UI and dialogue text', palette),
              Divider(
                  height: 1,
                  thickness: 1,
                  color: palette.div.withValues(alpha: 0.5)),
              _buildTypeSpecRow('Technical Mono', 'IBM Plex Mono',
                  'AST symbols, code citations & telemetry', palette),
            ],
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────
  // 3. Intelligence Tab: Real Reasoning Tiers & Specs
  // ─────────────────────────────────────────────────────────────
  Widget _buildIntelligenceTab(UnoPalette palette) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(LucideIcons.sparkles, size: 18, color: palette.accent),
            const SizedBox(width: 8),
            Text(
              'Intelligence & Reasoning',
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Configure AI reasoning depth and architectural specification outputs',
          style: UnoTypography.body(
            color: palette.textSec,
            fontSize: 12.5,
          ),
        ),
        const SizedBox(height: 20),

        Text(
          'DEFAULT REASONING DEPTH',
          style: UnoTypography.mono(
            color: palette.textSec,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 10),

        _buildTierOption(
          id: 'warm',
          title: 'Warm Tier · Multi-Signal AST (Recommended)',
          desc: 'Balanced synthesis combining AST symbol hierarchy, call-graph edges, and code snippets.',
          icon: LucideIcons.flame,
          badgeColor: UnoPalette.queryWarm,
          palette: palette,
        ),
        const SizedBox(height: 8),
        _buildTierOption(
          id: 'cold',
          title: 'Cold Tier · Deep Proof Verification',
          desc: 'Exhaustive multi-hop traversal with deterministic contract and invariant verification.',
          icon: LucideIcons.snowflake,
          badgeColor: UnoPalette.queryCold,
          palette: palette,
        ),
        const SizedBox(height: 8),
        _buildTierOption(
          id: 'hot',
          title: 'Hot Tier · Direct Symbol Retrieval',
          desc: 'Low-latency search targeting exact symbols, interfaces, and function signatures.',
          icon: LucideIcons.zap,
          badgeColor: UnoPalette.queryHot,
          palette: palette,
        ),

        const SizedBox(height: 24),

        Text(
          'SPECIFICATION OUTPUT FORMAT',
          style: UnoTypography.mono(
            color: palette.textSec,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _buildSpecFormatChip('bdd', 'Gherkin BDD Contracts', palette),
            const SizedBox(width: 8),
            _buildSpecFormatChip('adr', 'Markdown ADR Records', palette),
            const SizedBox(width: 8),
            _buildSpecFormatChip('ts', 'TypeScript Interfaces', palette),
          ],
        ),
      ],
    );
  }

  Widget _buildTierOption({
    required String id,
    required String title,
    required String desc,
    required IconData icon,
    required Color badgeColor,
    required UnoPalette palette,
  }) {
    final isSelected = _selectedReasoningTier == id;

    return InkWell(
      onTap: () => setState(() => _selectedReasoningTier = id),
      borderRadius: BorderRadius.circular(12),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSelected
              ? badgeColor.withValues(alpha: widget.isDark ? 0.12 : 0.08)
              : palette.bgElevated,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? badgeColor : palette.div,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: badgeColor.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, size: 16, color: badgeColor),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: UnoTypography.body(
                      color: palette.text,
                      fontSize: 13,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    desc,
                    style: UnoTypography.body(
                      color: palette.textSec,
                      fontSize: 11.5,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Container(
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: isSelected ? badgeColor : palette.textSec,
                  width: 1.8,
                ),
                color: isSelected ? badgeColor : Colors.transparent,
              ),
              child: isSelected
                  ? Icon(Icons.check, size: 11, color: widget.isDark ? Colors.black : Colors.white)
                  : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSpecFormatChip(String id, String label, UnoPalette palette) {
    final isSelected = _selectedSpecFormat == id;

    return InkWell(
      onTap: () => setState(() => _selectedSpecFormat = id),
      borderRadius: BorderRadius.circular(20),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected
              ? palette.accent.withValues(alpha: widget.isDark ? 0.16 : 0.14)
              : palette.bgElevated,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? palette.accent : palette.div,
            width: isSelected ? 1.4 : 1.0,
          ),
        ),
        child: Text(
          label,
          style: UnoTypography.body(
            color: isSelected ? palette.text : palette.textSec,
            fontSize: 12,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(
    String label,
    String value, {
    required IconData icon,
    required UnoPalette palette,
    String? badge,
    bool isMono = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Icon(icon, size: 15, color: palette.textSec),
          const SizedBox(width: 10),
          Text(
            label,
            style: UnoTypography.body(
              color: palette.textSec,
              fontSize: 13,
              fontWeight: FontWeight.w400,
            ),
          ),
          const Spacer(),
          if (badge != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF22C55E).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.check, size: 11, color: Color(0xFF22C55E)),
                  const SizedBox(width: 3),
                  Text(
                    badge,
                    style: UnoTypography.mono(
                      color: const Color(0xFF22C55E),
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
          ],
          Text(
            value,
            style: isMono
                ? UnoTypography.mono(
                    color: palette.text,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                  )
                : UnoTypography.body(
                    color: palette.text,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypeSpecRow(
      String category, String fontName, String usage, UnoPalette palette) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              category,
              style: UnoTypography.body(
                color: palette.textSec,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  fontName,
                  style: UnoTypography.body(
                    color: palette.text,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  usage,
                  style: UnoTypography.body(
                    color: palette.textSec.withValues(alpha: 0.75),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
